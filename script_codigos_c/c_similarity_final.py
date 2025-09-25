#!/usr/bin/env python3
import os, re, math, argparse, itertools, csv, datetime, pickle, fnmatch, hashlib, statistics
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor

C_EXTS = {".c"}             # só .c (ajuste se quiser .h)
DEFAULT_K = 5
CACHE_FILE = ".features_cache.pkl"

QNAME_RE = re.compile(r"^[qQ](\d+)[ _-]([A-Za-z0-9_-]+)\.c$")  # aceita q1_abc.c, q01-abc.c, q1 abc.c
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

def cosine(ca: Counter, cb: Counter)->float:
    if not ca and not cb: return 1.0
    keys = set(ca) | set(cb)
    dot = sum(ca[k]*cb[k] for k in keys)
    na = math.sqrt(sum(v*v for v in ca.values()))
    nb = math.sqrt(sum(v*v for v in cb.values()))
    return dot/(na*nb) if na and nb else 0.0

def gather_files(root, ignore_globs):
    paths = []
    if os.path.isfile(root):
        if os.path.splitext(root)[1].lower() in C_EXTS and parse_qsigla(root):
            if not any(fnmatch.fnmatch(os.path.basename(root), g) for g in ignore_globs):
                paths.append(root)
    else:
        for dp, _, files in os.walk(root):
            for nm in files:
                full = os.path.join(dp, nm)
                if os.path.splitext(nm)[1].lower() in C_EXTS and parse_qsigla(full):
                    if not any(fnmatch.fnmatch(nm, g) for g in ignore_globs):
                        paths.append(full)
    return sorted(paths)

def file_sigla_key(p): return parse_qsigla(p)[1].lower()

def read_text(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def sha1(path):
    with open(path,"rb") as f: return hashlib.sha1(f.read()).hexdigest()

def _extract_one(args):
    path, k, do_norm, min_tokens = args
    try:
        code = read_text(path)
        clean = strip_comments_and_strings(code)
        toks = tokenize(clean)
        if len(toks) < min_tokens:
            return path, {"too_short": True}
        tnorm = normalize_identifiers(toks) if do_norm else toks
        return path, {
            "too_short": False,
            "tokens": tnorm,
            "shingles": shingles(tnorm, k),
            "tf": Counter(tnorm),
            "hash": sha1(path),
        }
    except Exception as e:
        return path, {"error": str(e)}

def load_cache(cache_path):
    if os.path.exists(cache_path):
        try:
            with open(cache_path,"rb") as f: return pickle.load(f)
        except Exception:
            return {}
    return {}

def save_cache(cache_path, data):
    try:
        with open(cache_path,"wb") as f: pickle.dump(data, f)
    except Exception:
        pass

def feature_key(path):
    st = os.stat(path)
    return (path, st.st_mtime_ns, st.st_size)

def build_features(paths, k, do_norm, min_tokens, jobs):
    cache = load_cache(CACHE_FILE)
    out = {}
    todo = []
    for p in paths:
        key = feature_key(p)
        if key in cache:
            out[p] = cache[key]
        else:
            todo.append((p, k, do_norm, min_tokens))
    if todo:
        with ProcessPoolExecutor(max_workers=jobs or None) as ex:
            for p, feat in ex.map(_extract_one, todo):
                key = feature_key(p)
                out[p] = feat
                cache[key] = feat
        save_cache(CACHE_FILE, cache)
    return out

def baseline_stats(values):
    if len(values) < 2: return (None, None)
    mean = statistics.fmean(values)
    sd = statistics.pstdev(values)
    return mean, sd if sd>0 else (mean, 0.0)

def status_from_scores(j, ctl, idv, loops, calls, th_j, th_ctl, th_id, th_loops, th_calls, policy, weighted_score=None, weighted_th=0.7):
    flags = []
    if j is not None and j >= th_j: flags.append(True)
    if ctl is not None and ctl >= th_ctl: flags.append(True)
    if idv is not None and idv >= th_id: flags.append(True)
    if loops is not None and loops >= th_loops: flags.append(True)
    if calls is not None and calls >= th_calls: flags.append(True)
    if policy == "any":
        sus = any(flags)
    elif policy == "all":
        sus = all([j is None or j>=th_j,
                   ctl is None or ctl>=th_ctl,
                   idv is None or idv>=th_id,
                   loops is None or loops>=th_loops,
                   calls is None or calls>=th_calls])
    else:  # weighted
        sus = (weighted_score or 0.0) >= weighted_th
    return "SUSPEITO" if sus else ("REVISAR" if (j or 0.0) >= (th_j*0.85) else "OK")

def read_roster(path):
    if not path: return {}
    m = {}
    with open(path,"r",encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        # precisa ter 'sigla' e 'nome'
        for row in rdr:
            sig = (row.get("sigla") or "").strip()
            nome = (row.get("nome") or "").strip()
            if sig and nome:
                m[sig.lower()] = {"nome": nome, "matricula": (row.get("matricula") or "").strip()}
    return m

def write_json_per_student(outdir, qnum, rows):
    import json
    d = os.path.join(outdir, f"Q{qnum:02d}_per_student")
    os.makedirs(d, exist_ok=True)
    for r in rows:
        sigla = r["sigla"]
        with open(os.path.join(d, f"{sigla}.json"),"w",encoding="utf-8") as f:
            json.dump(r, f, ensure_ascii=False, indent=2)

def generate_html(output_path, root_label, groups, best_by_q, roster, q_baseline):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    def esc(s): 
        return (s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")
    def pct(x): return f"{x*100:.1f}%" if x is not None else "—"
    html = f"""<!doctype html><html lang="pt-br"><head><meta charset="utf-8">
<title>Similaridade C — {esc(root_label)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root{{--bg:#0b1020;--card:#121a33;--muted:#93a4c3;--text:#e8efff;--ok:#7ad97a;--warn:#ffd36e;--bad:#ff7a7a}}
*{{box-sizing:border-box}}body{{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:var(--bg);color:var(--text)}}
header{{padding:24px;border-bottom:1px solid #213055;background:linear-gradient(180deg,#0f1630,transparent)}}
h1{{margin:0 0 6px}}.sub{{color:var(--muted);font-size:14px}}
main{{padding:24px;max-width:1200px;margin:0 auto}}.card{{background:#121a33;border:1px solid #1f2b4b;border-radius:16px;padding:16px;margin-bottom:20px}}
table{{width:100%;border-collapse:collapse;font-size:14px}}th,td{{padding:10px 12px;border-bottom:1px solid #1f2b4b;text-align:left}}
th{{color:var(--muted)}}tr:hover td{{background:rgba(255,255,255,.03)}}.pct{{font-variant-numeric:tabular-nums;font-weight:600}}
.good{{color:var(--ok)}}.mid{{color:var(--warn)}}.bad{{color:var(--bad)}}.pill{{border:1px solid #2a3c6e;border-radius:999px;padding:2px 8px;color:#c9d6f3;font-size:12px}}
.small{{color:var(--muted);font-size:12px}}
</style></head><body>
<header><h1>Relatório de Similaridade</h1>
<div class="sub">Conjunto: {esc(root_label)} · Gerado em {esc(ts)}</div></header><main>
"""
    for qnum in sorted(groups.keys()):
        rows = best_by_q[qnum]  # lista de dicts prontos
        mean, sd = q_baseline.get(qnum, (None, None))
        html += f"""<section class="card"><h2>Questão Q{qnum:02d}</h2>"""
        if mean is not None:
            html += f"""<div class="small">Baseline Jaccard: média={mean:.3f}; DP={sd:.3f}</div>"""
        html += """<table><thead><tr>
<th>Sigla</th><th>Nome</th><th>Arquivo</th><th>Melhor Par</th><th>Jaccard</th><th>Cosseno</th><th>z(Jaccard)</th><th>Status</th>
</tr></thead><tbody>"""
        for r in rows:
            cls = "bad" if r["status"]=="SUSPEITO" else ("mid" if r["status"]=="REVISAR" else "good")
            html += f"<tr><td>{esc(r['sigla'])}</td><td>{esc(r.get('nome') or '')}</td><td>{esc(r['file'])}</td><td>{esc(r['best_with'])}</td>"
            html += f"<td class='pct'>{pct(r['jaccard'])}</td><td class='pct'>{pct(r['cosine'])}</td>"
            ztxt = f"{r['zscore']:.2f}" if r['zscore'] is not None else "—"
            html += f"<td>{ztxt}</td><td class='{cls}'>{r['status']}</td></tr>\n"
        html += "</tbody></table></section>\n"
    html += f"""</main>
<footer style="text-align:center;padding:24px;color:#93a4c3">
<span class="pill">Jaccard = k-shingles (estrutura)</span>
<span class="pill">Cosseno = frequência de tokens (vocabulário)</span>
</footer></body></html>"""
    with open(output_path,"w",encoding="utf-8") as f: f.write(html)

def main():
    ap = argparse.ArgumentParser(description="Similaridade de C por questão (qN_SIGLA.c) com cache, multiprocess, roster e baseline.")
    ap.add_argument("path", help="Pasta/arquivo (usa apenas qN_SIGLA.c)")
    ap.add_argument("--k", type=int, default=DEFAULT_K)
    ap.add_argument("--no-normalize", action="store_true")
    ap.add_argument("--html", type=str, help="Relatório HTML")
    ap.add_argument("--csv", type=str, help="Consolidado CSV por aluno")
    ap.add_argument("--jsondir", type=str, help="Diretório para JSONs por aluno")
    ap.add_argument("--roster", type=str, help="CSV com colunas: sigla,nome[,matricula]")
    ap.add_argument("--ignore", type=str, default="", help="Padrões glob separados por vírgula, ex: main.c,utils*.c")
    ap.add_argument("--min-tokens", type=int, default=10)
    ap.add_argument("--jobs", type=int, default=0, help="Processos em paralelo (0=auto)")
    # limiares e política
    ap.add_argument("--th-j", type=float, default=0.70)
    ap.add_argument("--policy", choices=["any","all","weighted"], default="any")
    args = ap.parse_args()

    ignore_globs = [g.strip() for g in args.ignore.split(",") if g.strip()]
    paths = gather_files(args.path, ignore_globs)
    if len(paths) < 2:
        print("⚠️ Preciso de ≥2 arquivos válidos."); return

    roster = read_roster(args.roster)
    feats = build_features(paths, args.k, not args.no_normalize, args.min_tokens, args.jobs)

    # agrupar por questão e ordenar por sigla
    groups = defaultdict(list)
    for p in paths: groups[parse_qsigla(p)[0]].append(p)
    for q in list(groups.keys()):
        groups[q].sort(key=file_sigla_key)
        # descartar grupos com menos de 2 utilizáveis
        if len(groups[q])<2: groups.pop(q, None)

    # pares por questão + baseline
    best_by_q = {}
    q_baseline = {}
    all_rows_for_csv = []

    for qnum, plist in sorted(groups.items()):
        pairs = []
        # calcula todos os pares (sem repetição)
        for a, b in itertools.combinations(plist, 2):
            fa, fb = feats[a], feats[b]
            if fa.get("error") or fb.get("error") or fa.get("too_short") or fb.get("too_short"):
                continue
            j = jaccard(fa["shingles"], fb["shingles"])
            c = cosine(fa["tf"], fb["tf"])
            pairs.append((a,b,j,c))

        # baseline por questão (média/DP do Jaccard)
        jvals = [x[2] for x in pairs]
        mean, sd = baseline_stats(jvals)
        q_baseline[qnum] = (mean, sd)

        # melhor par por arquivo
        idx = {p: {"mate":None,"j":-1.0,"c":-1.0} for p in plist}
        for a,b,j,c in pairs:
            if j > idx[a]["j"]: idx[a] = {"mate":b,"j":j,"c":c}
            if j > idx[b]["j"]: idx[b] = {"mate":a,"j":j,"c":c}

        # linhas ordenadas por sigla
        rows=[]
        for p in plist:
            sigla = parse_qsigla(p)[1]
            mate = idx[p]["mate"]
            j = idx[p]["j"] if idx[p]["j"]>=0 else None
            c = idx[p]["c"] if idx[p]["c"]>=0 else None
            z = ((j - mean)/sd) if (j is not None and mean is not None and sd not in (None,0.0)) else None
            nome = roster.get(sigla.lower(),{}).get("nome")
            status = status_from_scores(j, None, None, None, None, args.th_j, 1,1,1,1, args.policy,
                                        weighted_score=j, weighted_th=args.th_j)
            row = {
                "question": qnum,
                "sigla": sigla,
                "nome": nome,
                "file": os.path.basename(p),
                "best_with": os.path.basename(mate) if mate else "—",
                "jaccard": j, "cosine": c, "zscore": z, "status": status
            }
            rows.append(row); all_rows_for_csv.append(row)
        best_by_q[qnum] = rows

    # HTML
    if args.html:
        root_label = os.path.basename(os.path.abspath(args.path)) if os.path.isdir(args.path) \
                     else os.path.basename(os.path.dirname(os.path.abspath(args.path)))
        generate_html(args.html, root_label, groups, best_by_q, roster, q_baseline)
        print(f"🌐 HTML salvo em: {args.html}")

    # CSV consolidado
    if args.csv:
        with open(args.csv,"w",newline="",encoding="utf-8") as f:
            w=csv.writer(f); w.writerow(["question","sigla","nome","file","best_with","jaccard","cosine","zscore","status"])
            for r in all_rows_for_csv:
                w.writerow([r["question"], r["sigla"], r.get("nome") or "", r["file"], r["best_with"],
                            f"{(r['jaccard'] or 0):.6f}" if r["jaccard"] is not None else "",
                            f"{(r['cosine'] or 0):.6f}" if r["cosine"] is not None else "",
                            f"{r['zscore']:.3f}" if r["zscore"] is not None else "", r["status"]])
        print(f"💾 CSV salvo em: {args.csv}")

    # JSON por aluno
    if args.jsondir:
        os.makedirs(args.jsondir, exist_ok=True)
        for qnum, rows in best_by_q.items():
            write_json_per_student(args.jsondir, qnum, rows)
        print(f"📦 JSONs salvos em: {args.jsondir}")

if __name__ == "__main__":
    main()
