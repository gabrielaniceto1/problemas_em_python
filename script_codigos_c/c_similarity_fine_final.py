#!/usr/bin/env python3
import os, re, math, argparse, itertools, csv, datetime, pickle, fnmatch, hashlib, statistics, json
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor

C_EXTS = {".c"}
DEFAULT_K = 5
CACHE_FILE = ".features_fine_cache.pkl"

# pesos do score composto (podem ser alterados via CLI)
DEFAULT_WEIGHTS = {"jaccard":0.40, "control":0.20, "idents":0.15, "loops":0.15, "calls":0.10}

QNAME_RE = re.compile(r"^[qQ](\d+)[ _-]([A-Za-z0-9_-]+)\.c$")
TOKEN_RE = re.compile(r"""
    ([A-Za-z_][A-Za-z_0-9]*) | (0x[0-9A-Fa-f]+) | (\d+\.\d*|\.\d+|\d+) |
    (==|!=|<=|>=|->|\+\+|--|&&|\|\||<<|>>|::) | ([{}()\[\];,.:?~!%^&*+\-/|<>=])
""", re.VERBOSE)
C_KEYWORDS = {
    'auto','break','case','char','const','continue','default','do','double','else','enum','extern',
    'float','for','goto','if','inline','int','long','register','restrict','return','short','signed',
    'sizeof','static','struct','switch','typedef','union','unsigned','void','volatile','while',
    '_Bool','_Complex','_Imaginary'
}

def parse_qsigla(path):
    m = QNAME_RE.match(os.path.basename(path))
    if not m: return None
    return int(m.group(1)), m.group(2)

def strip_comments_and_strings(code: str) -> str:
    code = re.sub(r'("([^"\\]|\\.)*")|(\'([^\'\\]|\\.)*\')', lambda m: " " * len(m.group(0)), code, flags=re.DOTALL)
    code = re.sub(r"/\*.*?\*/", lambda m: " " * len(m.group(0)), code, flags=re.DOTALL)
    code = re.sub(r"//[^\n]*", "", code)
    return code

def tokenize(code: str):
    return [m.group(0) for m in TOKEN_RE.finditer(code)]

def normalize_identifiers(tokens):
    id_map, out, nxt = {}, [], 1
    for t in tokens:
        if re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", t) and t not in C_KEYWORDS:
            if t not in id_map: id_map[t] = f"ID{nxt}"; nxt += 1
            out.append(id_map[t])
        else:
            out.append(t)
    return out

def shingles(tokens, k=DEFAULT_K):
    if len(tokens) < k: return set()
    return {" ".join(tokens[i:i+k]) for i in range(len(tokens) - k + 1)}

def jaccard(a:set, b:set)->float:
    if not a and not b: return 1.0
    u = len(a|b)
    return len(a&b)/u if u else 0.0

def levenshtein(a, b):
    n, m = len(a), len(b)
    if n==0: return m
    if m==0: return n
    dp = list(range(m+1))
    for i in range(1, n+1):
        prev, dp[0] = dp[0], i
        for j in range(1, m+1):
            ins = dp[j-1] + 1
            dele = dp[j] + 1
            sub = prev + (0 if a[i-1]==b[j-1] else 1)
            prev, dp[j] = dp[j], min(ins, dele, sub)
    return dp[m]

def sim_edit(a, b):
    if not a and not b: return 1.0
    d = levenshtein(a, b)
    return 1.0 - d / max(len(a), len(b), 1)

def extract_identifiers(tokens):
    return {t for t in tokens if re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", t) and t not in C_KEYWORDS}

def extract_function_calls(tokens):
    calls=set()
    for i in range(len(tokens)-1):
        if re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", tokens[i]) and tokens[i] not in C_KEYWORDS and tokens[i+1]=='(':
            calls.add(tokens[i])
    return calls

def control_stream(tokens):
    stream=[]
    map_ctrl={'if':'IF','else':'ELSE','for':'FOR','while':'WHILE','do':'DO','switch':'SWITCH','case':'CASE','default':'DEFAULT',
              'return':'RETURN','break':'BREAK','continue':'CONTINUE'}
    for t in tokens:
        tt=t.lower()
        if tt in map_ctrl: stream.append(map_ctrl[tt])
        elif t in {'{','}'}: stream.append('BRACE'+t)
        elif t==';': stream.append('SEMI')
    comp=[]
    for s in stream:
        if not comp or comp[-1]!=s: comp.append(s)
    return comp

def find_matching_paren(s, start_idx):
    depth=0
    for i,ch in enumerate(s[start_idx:], start_idx):
        if ch=='(':
            depth+=1
        elif ch==')':
            depth-=1
            if depth==0: return i
    return -1

def normalize_for_header(header):
    parts=[p.strip() for p in header.split(';')]
    while len(parts)<3: parts.append('')
    init,cond,incr = parts[0],parts[1],parts[2]
    def norm_init(s):
        s=re.sub(r"\s+","",s)
        if not s: return "NONE"
        if re.match(r".*=", s): return "ASSIGN_OR_DECL"
        return "OTHER"
    def norm_cond(s):
        s=re.sub(r"\s+","",s); s=re.sub(r"[A-Za-z_]\w*","ID",s); s=re.sub(r"\d+(\.\d+)?","NUM",s)
        if "ID<NUM" in s or "ID<=NUM" in s: return "ID<NUM"
        if "ID>NUM" in s or "ID>=NUM" in s: return "ID>NUM"
        if "ID==ID" in s or "ID==NUM" in s: return "EQ"
        return "COND"
    def norm_incr(s):
        s=re.sub(r"\s+","",s)
        if not s: return "NONE"
        if re.search(r"\+\+|--", s): return "INCDEC"
        if re.search(r"\+=|-=|=ID[+\-]NUM", s): return "ARITH"
        return "OTHER"
    return f"FOR[{norm_init(init)};{norm_cond(cond)};{norm_incr(incr)}]"
def normalize_while_cond(cond):
    s=re.sub(r"\s+","",cond); s=re.sub(r"[A-Za-z_]\w*","ID",s); s=re.sub(r"\d+(\.\d+)?","NUM",s)
    if "ID<NUM" in s or "ID>NUM" in s: return "CMP_NUM"
    if "ID" in s and "NUM" not in s: return "COND_ID"
    return "COND"
def extract_loop_signatures(code_clean: str):
    sigs=set(); i=0; n=len(code_clean)
    while i<n:
        mf=re.compile(r'\bfor\b').search(code_clean,i)
        mw=re.compile(r'\bwhile\b').search(code_clean,i)
        m=kind=None
        if mf and (not mw or mf.start()<mw.start()): m,kind=mf,'FOR'
        elif mw: m,kind=mw,'WHILE'
        else: break
        i=m.end(); j=i
        while j<n and code_clean[j].isspace(): j+=1
        if j>=n or code_clean[j] != '(': continue
        k=find_matching_paren(code_clean,j)
        if k==-1: continue
        inside=code_clean[j+1:k]
        sigs.add(normalize_for_header(inside) if kind=='FOR' else f"WHILE[{normalize_while_cond(inside)}]")
        i=k+1
    return sigs

def cosine(ca: Counter, cb: Counter)->float:
    keys=set(ca)|set(cb)
    dot=sum(ca[k]*cb[k] for k in keys)
    na=math.sqrt(sum(v*v for v in ca.values()))
    nb=math.sqrt(sum(v*v for v in cb.values()))
    return dot/(na*nb) if na and nb else 0.0

def sha1(path):
    with open(path,"rb") as f: return hashlib.sha1(f.read()).hexdigest()

def gather_files(root, ignore_globs):
    paths=[]
    if os.path.isfile(root):
        if os.path.splitext(root)[1].lower() in C_EXTS and parse_qsigla(root):
            if not any(fnmatch.fnmatch(os.path.basename(root), g) for g in ignore_globs):
                paths.append(root)
    else:
        for dp,_,files in os.walk(root):
            for nm in files:
                full=os.path.join(dp,nm)
                if os.path.splitext(nm)[1].lower() in C_EXTS and parse_qsigla(full):
                    if not any(fnmatch.fnmatch(nm, g) for g in ignore_globs):
                        paths.append(full)
    return sorted(paths)
def file_sigla_key(p): return parse_qsigla(p)[1].lower()

def read_text(path):
    with open(path,"r",encoding="utf-8",errors="ignore") as f: return f.read()

def _extract_one(args):
    path, k, do_norm, min_tokens = args
    try:
        code = read_text(path)
        clean = strip_comments_and_strings(code)
        tok_raw = tokenize(clean)
        if len(tok_raw) < min_tokens:
            return path, {"too_short": True}
        tok_norm = normalize_identifiers(tok_raw) if do_norm else tok_raw
        feat = {
            "too_short": False,
            "hash": sha1(path),
            "tok_norm": tok_norm,
            "shingles": shingles(tok_norm, k),
            "tf": Counter(tok_norm),
            "idents": extract_identifiers(tok_raw),
            "calls": extract_function_calls(tok_raw),
            "control": control_stream(tok_raw),
            "loopsigs": extract_loop_signatures(clean),
        }
        return path, feat
    except Exception as e:
        return path, {"error": str(e)}

def feature_key(path):
    st=os.stat(path)
    return (path, st.st_mtime_ns, st.st_size)

def load_cache(cache_path):
    if os.path.exists(cache_path):
        try:
            with open(cache_path,"rb") as f: return pickle.load(f)
        except Exception: return {}
    return {}
def save_cache(cache_path, data):
    try:
        with open(cache_path,"wb") as f: pickle.dump(data,f)
    except Exception: pass

def build_features(paths, k, do_norm, min_tokens, jobs):
    cache = load_cache(CACHE_FILE)
    out={}
    todo=[]
    for p in paths:
        key=feature_key(p)
        if key in cache:
            out[p]=cache[key]
        else:
            todo.append((p,k,do_norm,min_tokens))
    if todo:
        with ProcessPoolExecutor(max_workers=jobs or None) as ex:
            for p,feat in ex.map(_extract_one, todo):
                key=feature_key(p)
                out[p]=feat
                cache[key]=feat
        save_cache(CACHE_FILE, cache)
    return out

def compare_pair(fa, fb, weights):
    j = jaccard(fa["shingles"], fb["shingles"])
    ctrl = sim_edit(fa["control"], fb["control"])
    idj = jaccard(fa["idents"], fb["idents"])
    loops = jaccard(fa["loopsigs"], fb["loopsigs"])
    calls = jaccard(fa["calls"], fb["calls"])
    score = (weights["jaccard"]*j + weights["control"]*ctrl + weights["idents"]*idj +
             weights["loops"]*loops + weights["calls"]*calls)
    breakdown = {"jaccard": j, "control": ctrl, "idents": idj, "loops": loops, "calls": calls}
    return score, breakdown

def baseline_stats(values):
    if len(values) < 2: return (None, None)
    mean = statistics.fmean(values); sd = statistics.pstdev(values)
    return mean, sd if sd>0 else (mean, 0.0)

def status_from_policy(score, br, th, policy):
    if policy=="weighted":
        return "SUSPEITO" if score >= th else ("REVISAR" if score >= th*0.85 else "OK")
    elif policy=="any":
        flags=[br["jaccard"]>=th, br["control"]>=th, br["idents"]>=th, br["loops"]>=th, br["calls"]>=th]
        sus=any(flags)
    else:  # all
        sus=all([br["jaccard"]>=th, br["control"]>=th, br["idents"]>=th, br["loops"]>=th, br["calls"]>=th])
    return "SUSPEITO" if sus else "OK"

def generate_html(output_path, root_label, groups, rows_by_q, mean_sd_by_q, weights):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    def esc(s):
        return (s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")
    def pct(x): return f"{x*100:.1f}%"
    html = f"""<!doctype html><html lang="pt-br"><head><meta charset="utf-8">
<title>Pente Fino — {esc(root_label)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root{{--bg:#0b1020;--card:#121a33;--muted:#93a4c3;--text:#e8efff;--ok:#7ad97a;--warn:#ffd36e;--bad:#ff7a7a}}
*{{box-sizing:border-box}}body{{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:var(--bg);color:var(--text)}}
header{{padding:24px;border-bottom:1px solid #213055;background:linear-gradient(180deg,#0f1630,transparent)}}
h1{{margin:0 0 6px}}.sub{{color:var(--muted);font-size:14px}}
main{{padding:24px;max-width:1280px;margin:0 auto}}.card{{background:#121a33;border:1px solid #1f2b4b;border-radius:16px;padding:16px;margin-bottom:20px}}
table{{width:100%;border-collapse:collapse;font-size:14px}}th,td{{padding:10px 12px;border-bottom:1px solid #1f2b4b;text-align:left}}
th{{color:var(--muted)}}tr:hover td{{background:rgba(255,255,255,.03)}}.pct{{font-variant-numeric:tabular-nums;font-weight:600}}
.good{{color:var(--ok)}}.mid{{color:var(--warn)}}.bad{{color:var(--bad)}}.pill{{border:1px solid #2a3c6e;border-radius:999px;padding:2px 8px;color:#c9d6f3;font-size:12px}}
.small{{color:var(--muted);font-size:12px}}
</style></head><body>
<header><h1>Relatório de Similaridade — Pente Fino</h1>
<div class="sub">Conjunto: {esc(root_label)} · Gerado em {esc(ts)} · Pesos: {json.dumps(weights)}</div></header><main>
"""
    for qnum in sorted(groups.keys()):
        rows = rows_by_q[qnum]
        mean, sd = mean_sd_by_q.get(qnum, (None,None))
        html += f"<section class='card'><h2>Questão Q{qnum:02d}</h2>"
        if mean is not None:
            html += f"<div class='small'>Baseline (score composto) — média={mean:.3f}; DP={sd:.3f}</div>"
        html += """<table><thead><tr>
<th>Sigla</th><th>Nome</th><th>Arquivo</th><th>Melhor Par</th>
<th>Score</th><th>Jaccard</th><th>Fluxo</th><th>Ids</th><th>Laços</th><th>Chamadas</th><th>Status</th>
</tr></thead><tbody>"""
        for r in rows:
            cls = "bad" if r["status"]=="SUSPEITO" else ("mid" if r["status"]=="REVISAR" else "good")
            html += f"<tr><td>{esc(r['sigla'])}</td><td>{esc(r.get('nome') or '')}</td><td>{esc(r['file'])}</td><td>{esc(r['best_with'])}</td>"
            html += f"<td class='pct'>{pct(r['score'])}</td><td class='pct'>{pct(r['br']['jaccard'])}</td><td class='pct'>{pct(r['br']['control'])}</td>"
            html += f"<td class='pct'>{pct(r['br']['idents'])}</td><td class='pct'>{pct(r['br']['loops'])}</td><td class='pct'>{pct(r['br']['calls'])}</td>"
            html += f"<td class='{cls}'>{r['status']}</td></tr>\n"
        html += "</tbody></table></section>\n"
    html += """</main><footer style="text-align:center;padding:24px;color:#93a4c3">
<span class="pill">Jaccard: k-shingles</span> <span class="pill">Fluxo: edição(IF/ELSE/FOR/WHILE…)</span>
<span class="pill">Ids: nomes iguais</span> <span class="pill">Laços: cabeçalhos normalizados</span> <span class="pill">Chamadas: funções</span>
</footer></body></html>"""
    with open(output_path,"w",encoding="utf-8") as f: f.write(html)

def read_roster(path):
    if not path: return {}
    m={}
    with open(path,"r",encoding="utf-8") as f:
        rdr=csv.DictReader(f)
        for row in rdr:
            sig=(row.get("sigla") or "").strip()
            nome=(row.get("nome") or "").strip()
            if sig and nome: m[sig.lower()]={"nome":nome,"matricula":(row.get("matricula") or "").strip()}
    return m

def main():
    ap = argparse.ArgumentParser(description="Pente-fino de similaridade C por questão com cache, multiprocess, roster e baseline.")
    ap.add_argument("path")
    ap.add_argument("--k", type=int, default=DEFAULT_K)
    ap.add_argument("--no-normalize", action="store_true")
    ap.add_argument("--html", type=str)
    ap.add_argument("--csv", type=str)
    ap.add_argument("--jsondir", type=str)
    ap.add_argument("--roster", type=str)
    ap.add_argument("--ignore", type=str, default="")
    ap.add_argument("--min-tokens", type=int, default=10)
    ap.add_argument("--jobs", type=int, default=0)
    # pesos & política
    ap.add_argument("--w-j", type=float, default=DEFAULT_WEIGHTS["jaccard"])
    ap.add_argument("--w-ctl", type=float, default=DEFAULT_WEIGHTS["control"])
    ap.add_argument("--w-id", type=float, default=DEFAULT_WEIGHTS["idents"])
    ap.add_argument("--w-loops", type=float, default=DEFAULT_WEIGHTS["loops"])
    ap.add_argument("--w-calls", type=float, default=DEFAULT_WEIGHTS["calls"])
    ap.add_argument("--th", type=float, default=0.70, help="limiar p/ política (any/all/weighted)")
    ap.add_argument("--policy", choices=["any","all","weighted"], default="weighted")
    args = ap.parse_args()

    weights={"jaccard":args.w_j,"control":args.w_ctl,"idents":args.w_id,"loops":args.w_loops,"calls":args.w_calls}
    ignore_globs=[g.strip() for g in args.ignore.split(",") if g.strip()]
    paths=gather_files(args.path, ignore_globs)
    if len(paths)<2: print("⚠️ Preciso de ≥2 arquivos válidos."); return

    roster=read_roster(args.roster)
    feats = build_features(paths, args.k, not args.no_normalize, args.min_tokens, args.jobs)

    groups=defaultdict(list)
    for p in paths: groups[parse_qsigla(p)[0]].append(p)
    for q in list(groups.keys()):
        groups[q].sort(key=file_sigla_key)
        if len(groups[q])<2: groups.pop(q,None)

    rows_by_q={}
    mean_sd_by_q={}
    all_rows=[]

    for qnum, plist in sorted(groups.items()):
        # computa pares
        pairs=[]
        for a,b in itertools.combinations(plist,2):
            fa,fb=feats[a],feats[b]
            if fa.get("error") or fb.get("error") or fa.get("too_short") or fb.get("too_short"): continue
            score, br = compare_pair(fa, fb, weights)
            pairs.append((a,b,score,br))
        # baseline
        scores=[x[2] for x in pairs]
        mean, sd = baseline_stats(scores)
        mean_sd_by_q[qnum]=(mean,sd)

        # melhor par por aluno
        best={p:(None,-1.0,None) for p in plist}
        for a,b,s,br in pairs:
            if s>best[a][1]: best[a]=(b,s,br)
            if s>best[b][1]: best[b]=(a,s,br)

        # linhas
        rows=[]
        for p in plist:
            sig=parse_qsigla(p)[1]; mate,score,br=best[p]
            if br is None: br={"jaccard":0,"control":0,"idents":0,"loops":0,"calls":0}; score=0.0
            status = status_from_policy(score, br, args.th, args.policy)
            row={"question":qnum,"sigla":sig,"nome":roster.get(sig.lower(),{}).get("nome"),
                 "file":os.path.basename(p),"best_with":os.path.basename(mate) if mate else "—",
                 "score":score,"br":br,"status":status}
            rows.append(row); all_rows.append(row)
        rows_by_q[qnum]=rows

    # HTML
    if args.html:
        root_label = os.path.basename(os.path.abspath(args.path)) if os.path.isdir(args.path) \
                     else os.path.basename(os.path.dirname(os.path.abspath(args.path)))
        generate_html(args.html, root_label, groups, rows_by_q, mean_sd_by_q, weights)
        print(f"🌐 HTML salvo em: {args.html}")

    # CSV
    if args.csv:
        with open(args.csv,"w",newline="",encoding="utf-8") as f:
            w=csv.writer(f); w.writerow(["question","sigla","nome","file","best_with","score","jaccard","control","idents","loops","calls","status"])
            for r in all_rows:
                w.writerow([r["question"], r["sigla"], r.get("nome") or "", r["file"], r["best_with"],
                            f"{r['score']:.6f}", f"{r['br']['jaccard']:.6f}", f"{r['br']['control']:.6f}",
                            f"{r['br']['idents']:.6f}", f"{r['br']['loops']:.6f}", f"{r['br']['calls']:.6f}", r["status"]])
        print(f"💾 CSV salvo em: {args.csv}")

    # JSON por aluno
    if args.jsondir:
        os.makedirs(args.jsondir, exist_ok=True)
        for qnum, rows in rows_by_q.items():
            d=os.path.join(args.jsondir, f"Q{qnum:02d}_per_student"); os.makedirs(d, exist_ok=True)
            for r in rows:
                with open(os.path.join(d, f"{r['sigla']}.json"),"w",encoding="utf-8") as f:
                    json.dump(r, f, ensure_ascii=False, indent=2)
        print(f"📦 JSONs salvos em: {args.jsondir}")

if __name__ == "__main__":
    main()
