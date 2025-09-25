#!/usr/bin/env python3
import os, re, math, argparse, itertools, csv, datetime
from collections import Counter, defaultdict

# -------- Config --------
C_EXTS = {".c"}
DEFAULT_K = 5
WEIGHTS = {  # pesos do score composto
    "jaccard": 0.40,
    "control": 0.20,
    "idents":  0.15,
    "loops":   0.15,
    "calls":   0.10,
}

# -------- Util --------
def html_escape(s:str)->str:
    return (s.replace("&","&amp;").replace("<","&lt;")
             .replace(">","&gt;").replace('"',"&quot;").replace("'","&#39;"))

def percentage(x: float) -> str:
    return f"{x*100:.1f}%"

# -------- Pré-processamento --------
def strip_comments_and_strings(code: str) -> str:
    str_re = r"""("([^"\\]|\\.)*")|('([^'\\]|\\.)*')"""
    code = re.sub(str_re, lambda m: " " * len(m.group(0)), code, flags=re.DOTALL)
    code = re.sub(r"/\*.*?\*/", lambda m: " " * len(m.group(0)), code, flags=re.DOTALL)
    code = re.sub(r"//[^\n]*", "", code)
    return code

TOKEN_RE = re.compile(
    r"""
    ([A-Za-z_][A-Za-z_0-9]*)
    | (0x[0-9A-Fa-f]+)
    | (\d+\.\d*|\.\d+|\d+)
    | (==|!=|<=|>=|->|\+\+|--|&&|\|\||<<|>>|::)
    | ([{}()\[\];,.:?~!%^&*+\-/|<>=])
    """, re.VERBOSE,
)

def tokenize(code: str):
    return [m.group(0) for m in TOKEN_RE.finditer(code)]

C_KEYWORDS = {
    'auto','break','case','char','const','continue','default','do','double','else','enum','extern',
    'float','for','goto','if','inline','int','long','register','restrict','return','short','signed',
    'sizeof','static','struct','switch','typedef','union','unsigned','void','volatile','while',
    '_Bool','_Complex','_Imaginary'
}

def normalize_identifiers(tokens):
    id_map, out, next_id = {}, [], 1
    for t in tokens:
        if re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", t) and t not in C_KEYWORDS:
            if t not in id_map:
                id_map[t] = f"ID{next_id}"; next_id += 1
            out.append(id_map[t])
        else:
            out.append(t)
    return out

# -------- Similaridades base --------
def shingles(tokens, k=DEFAULT_K):
    if len(tokens) < k: return set()
    return {" ".join(tokens[i:i+k]) for i in range(len(tokens) - k + 1)}

def jaccard_set(a:set, b:set) -> float:
    if not a and not b: return 1.0
    u = len(a|b)
    return len(a&b)/u if u else 0.0

# -------- Levenshtein para sequência de rótulos --------
def levenshtein(a, b):
    # dist. de edição clássica
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
    # similaridade = 1 - dist/len_max
    if not a and not b: return 1.0
    d = levenshtein(a, b)
    return 1.0 - d / max(len(a), len(b), 1)

# -------- Extrações "pente-fino" --------
def extract_identifiers(tokens):
    # nomes originais (sem normalizar)
    return {t for t in tokens if re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", t) and t not in C_KEYWORDS}

def extract_function_calls(tokens):
    calls = set()
    for i in range(len(tokens)-1):
        if re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", tokens[i]) and tokens[i] not in C_KEYWORDS:
            if tokens[i+1] == '(':
                calls.add(tokens[i])
    return calls

def control_stream(tokens):
    # reduz tokens a um fluxo de controle
    stream = []
    map_ctrl = {
        'if':'IF','else':'ELSE','for':'FOR','while':'WHILE','do':'DO',
        'switch':'SWITCH','case':'CASE','default':'DEFAULT','return':'RETURN','break':'BREAK','continue':'CONTINUE'
    }
    for t in tokens:
        tt = t.lower()
        if tt in map_ctrl:
            stream.append(map_ctrl[tt])
        elif t in {'{','}'}:
            stream.append('BRACE'+t)
        elif t == ';':
            stream.append('SEMI')
        # (poderíamos adicionar mais categorias aqui se quiser)
    # comprime repetições consecutivas para estabilidade
    comp = []
    for s in stream:
        if not comp or comp[-1] != s:
            comp.append(s)
    return comp

# --- Extração robusta das assinaturas de FOR/WHILE a partir do código "limpo" ---
def find_matching_paren(s, start_idx):
    # s[start_idx] deve ser '(' ; retorna índice da ')'
    depth = 0
    for i in range(start_idx, len(s)):
        if s[i] == '(':
            depth += 1
        elif s[i] == ')':
            depth -= 1
            if depth == 0:
                return i
    return -1

def normalize_for_header(header):
    # header: "init ; cond ; incr"
    parts = [p.strip() for p in header.split(';')]
    while len(parts) < 3: parts.append('')
    init, cond, incr = parts[0], parts[1], parts[2]

    def norm_init(s):
        s = re.sub(r"\s+", "", s)
        if not s: return "NONE"
        if re.match(r"(?:unsigned|signed|short|long|int|char|float|double|bool|_Bool|size_t|[^=]+)\w*\*?\w*=", s):
            return "DECL_ASSIGN"
        if re.match(r"[A-Za-z_]\w*=", s): return "ASSIGN"
        return "OTHER"

    def norm_cond(s):
        s = re.sub(r"\s+", "", s)
        if not s: return "NONE"
        s = re.sub(r"[A-Za-z_]\w*", "ID", s)
        s = re.sub(r"\d+(\.\d+)?", "NUM", s)
        s = re.sub(r"0x[0-9A-Fa-f]+", "HEX", s)
        # reduz operadores
        s = s.replace(">=","≥").replace("<=","≤").replace("==","=").replace("!=","≠")
        s = s.replace(">",">").replace("<","<")
        # bucket básico
        if "ID<NUM" in s or "ID≤NUM" in s: return "ID<NUM"
        if "ID>NUM" in s or "ID≥NUM" in s: return "ID>NUM"
        if "ID=ID" in s or "ID=NUM" in s: return "ASSIGN_IN_COND"
        if "ID==ID" in s or "ID=ID" in s: return "EQ"
        return "COND"

    def norm_incr(s):
        s = re.sub(r"\s+", "", s)
        if not s: return "NONE"
        if re.match(r"[A-Za-z_]\w*\+\+|--", s): return "INCDEC"
        if re.match(r"[A-Za-z_]\w*\+=\d+|-=\\d+", s): return "PLUSMINUS_EQ"
        if re.match(r"[A-Za-z_]\w*=[A-Za-z_]\w*\+\\d+|-\\d+", s): return "ASSIGN_ARITH"
        return "OTHER"

    return f"FOR[{norm_init(init)};{norm_cond(cond)};{norm_incr(incr)}]"

def normalize_while_cond(cond):
    s = re.sub(r"\s+", "", cond)
    s = re.sub(r"[A-Za-z_]\w*", "ID", s)
    s = re.sub(r"\d+(\.\d+)?", "NUM", s)
    s = re.sub(r"0x[0-9A-Fa-f]+", "HEX", s)
    if any(op in s for op in ("ID<NUM","ID≤NUM","ID>NUM","ID≥NUM")): return "CMP_NUM"
    if "ID" in s and "NUM" not in s: return "COND_ID"
    return "COND"
    
def extract_loop_signatures(code_clean: str):
    sigs = set()
    i = 0
    n = len(code_clean)
    while i < n:
        # procura 'for' e 'while' como palavras isoladas
        m_for = re.compile(r'\bfor\b').search(code_clean, i)
        m_while = re.compile(r'\bwhile\b').search(code_clean, i)
        m = None
        kind = None
        if m_for and (not m_while or m_for.start() < m_while.start()):
            m, kind = m_for, 'FOR'
        elif m_while:
            m, kind = m_while, 'WHILE'
        else:
            break
        i = m.end()
        # próximo não-espaço deve ser '('
        j = i
        while j < n and code_clean[j].isspace(): j += 1
        if j >= n or code_clean[j] != '(':
            continue
        k = find_matching_paren(code_clean, j)
        if k == -1:
            continue
        inside = code_clean[j+1:k]
        if kind == 'FOR':
            sigs.add(normalize_for_header(inside))
        else:
            sigs.add(f"WHILE[{normalize_while_cond(inside)}]")
        i = k + 1
    return sigs

# -------- Nome → (questão, sigla) --------
QNAME_RE = re.compile(r"^[qQ](\d+)_([A-Za-z0-9_-]+)\.c$")

def parse_qsigla(path):
    base = os.path.basename(path)
    m = QNAME_RE.match(base)
    if not m: return None
    return int(m.group(1)), m.group(2)

# -------- Leitura e features --------
def gather_files(root):
    paths = []
    if os.path.isfile(root):
        if os.path.splitext(root)[1].lower() in C_EXTS and parse_qsigla(root):
            paths.append(root)
    else:
        for dp, _, files in os.walk(root):
            for nm in files:
                if os.path.splitext(nm)[1].lower() in C_EXTS:
                    full = os.path.join(dp, nm)
                    if parse_qsigla(full):
                        paths.append(full)
    return sorted(paths)

def read_code(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def build_features(paths, k=DEFAULT_K, normalize=True):
    feats, meta, groups = {}, {}, defaultdict(list)
    for p in paths:
        meta[p] = parse_qsigla(p)  # (qnum, sigla)
        if not meta[p]: continue
        qnum, _ = meta[p]
        code = read_code(p)
        code_clean = strip_comments_and_strings(code)
        tok_raw = tokenize(code_clean)              # tokens pós-limpeza (p/ nomes, chamadas, controle)
        tok_norm = normalize_identifiers(tok_raw) if normalize else tok_raw
        feats[p] = {
            "tok_norm": tok_norm,
            "shingles": shingles(tok_norm, k=k),
            "idents": extract_identifiers(tok_raw),
            "calls": extract_function_calls(tok_raw),
            "control": control_stream(tok_raw),
            "loopsigs": extract_loop_signatures(code_clean),
        }
        groups[qnum].append(p)
    return feats, meta, groups

# -------- Comparações por questão --------
def compare_pair(fa, fb, feats):
    A, B = feats[fa], feats[fb]
    j = jaccard_set(A["shingles"], B["shingles"])
    ctrl = sim_edit(A["control"], B["control"])
    idj = jaccard_set(A["idents"], B["idents"])
    loops = jaccard_set(A["loopsigs"], B["loopsigs"])
    calls = jaccard_set(A["calls"], B["calls"])
    score = (WEIGHTS["jaccard"]*j + WEIGHTS["control"]*ctrl + WEIGHTS["idents"]*idj +
             WEIGHTS["loops"]*loops + WEIGHTS["calls"]*calls)
    breakdown = {"jaccard": j, "control": ctrl, "idents": idj, "loops": loops, "calls": calls}
    return score, breakdown

def pairwise_fine(groups, feats, meta):
    result_by_q = {}
    for qnum, plist in groups.items():
        pairs = []
        for a, b in itertools.combinations(plist, 2):
            if meta[a][1] == meta[b][1]:  # mesma sigla? ignora
                continue
            score, br = compare_pair(a, b, feats)
            pairs.append((a, b, score, br))
        result_by_q[qnum] = pairs
    return result_by_q

def best_match_per_file(q_paths, pairs):
    best = {p: (None, -1.0, None) for p in q_paths}
    for a, b, s, br in pairs:
        if s > best[a][1]: best[a] = (b, s, br)
        if s > best[b][1]: best[b] = (a, s, br)
    return best

# -------- HTML --------
def generate_html(output_path, root_label, groups, pairs_by_q, feats):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html = f"""<!doctype html>
<html lang="pt-br"><head><meta charset="utf-8">
<title>Similaridade C — Pente Fino — {html_escape(root_label)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root{{--bg:#0b1020;--card:#121a33;--muted:#93a4c3;--text:#e8efff;--ok:#7ad97a;--warn:#ffd36e;}}
*{{box-sizing:border-box}}body{{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:var(--bg);color:var(--text)}}
header{{padding:24px;border-bottom:1px solid #213055;background:linear-gradient(180deg,#0f1630,transparent)}}
h1{{margin:0 0 6px}}.sub{{color:var(--muted);font-size:14px}}
main{{padding:24px;max-width:1200px;margin:0 auto}}.card{{background:#121a33;border:1px solid #1f2b4b;border-radius:16px;padding:16px;margin-bottom:20px}}
table{{width:100%;border-collapse:collapse;font-size:14px}}th,td{{padding:10px 12px;border-bottom:1px solid #1f2b4b;text-align:left}}
th{{color:var(--muted)}}tr:hover td{{background:rgba(255,255,255,.03)}}.pct{{font-variant-numeric:tabular-nums;font-weight:600}}
.good{{color:var(--ok)}}.mid{{color:var(--warn)}}.low{{color:var(--muted)}}
.kv{{display:flex;flex-wrap:wrap;gap:10px;margin-top:6px}}.kv span{{border:1px solid #2a3c6e;border-radius:999px;padding:2px 8px;color:#c9d6f3;font-size:12px}}
.footer{{color:var(--muted);font-size:12px;padding:24px;text-align:center}}
</style></head><body>
<header><h1>Relatório de Similaridade — Pente Fino</h1>
<div class="sub">Conjunto: {html_escape(root_label)} · Gerado em {html_escape(ts)}</div></header><main>
"""
    for qnum in sorted(groups.keys()):
        q_paths = sorted(groups[qnum], key=lambda p: os.path.basename(p))
        pairs = pairs_by_q.get(qnum, [])
        best = best_match_per_file(q_paths, pairs)
        rows = []
        for p in q_paths:
            mate, s, br = best[p]
            rows.append((os.path.basename(p), os.path.basename(mate) if mate else "—", s, br))
        rows.sort(key=lambda x: (x[2] if x[2] is not None else -1), reverse=True)

        html += f"""<section class="card">
<h2 style="margin:6px 0 12px">Questão Q{qnum:02d}</h2>
<table><thead><tr>
<th>Arquivo</th><th>Melhor Par</th><th>Score Composto</th>
<th>Jaccard</th><th>Fluxo Controle</th><th>Ids</th><th>Laços</th><th>Chamadas</th>
</tr></thead><tbody>
"""
        for fname, mate, s, br in rows:
            if s is None: s=0.0; br={"jaccard":0,"control":0,"idents":0,"loops":0,"calls":0}
            cls = "good" if s>=0.7 else ("mid" if s>=0.4 else "low")
            html += f"<tr><td>{html_escape(fname)}</td><td>{html_escape(mate)}</td>"
            html += f"<td class='pct {cls}'>{percentage(s)}</td>"
            html += f"<td class='pct'>{percentage(br['jaccard'])}</td>"
            html += f"<td class='pct'>{percentage(br['control'])}</td>"
            html += f"<td class='pct'>{percentage(br['idents'])}</td>"
            html += f"<td class='pct'>{percentage(br['loops'])}</td>"
            html += f"<td class='pct'>{percentage(br['calls'])}</td></tr>\n"
        html += "</tbody></table>\n"

        # Opcional: listar assinaturas de laços por arquivo (útil p/ auditoria rápida)
        html += "<div class='kv'>"
        for p in q_paths:
            ls = sorted(feats[p]["loopsigs"])
            if ls:
                html += f"<span>Q{qnum:02d}/{html_escape(os.path.basename(p))}: {html_escape(', '.join(ls))}</span>"
        html += "</div></section>\n"

    html += f"""</main>
<div class="footer">
<p>Score composto = {WEIGHTS['jaccard']:.2f}·Jaccard(k-shingles) + {WEIGHTS['control']:.2f}·FluxoControle + {WEIGHTS['idents']:.2f}·Ids + {WEIGHTS['loops']:.2f}·Laços + {WEIGHTS['calls']:.2f}·Chamadas.</p>
<p>Comparações apenas entre arquivos no padrão <code>qN_SIGLA.c</code> dentro da mesma questão.</p>
</div></body></html>"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

# -------- CSV --------
def save_csv(pairs_by_q, out_csv):
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(
            ["question","file_a","file_b","score","jaccard","control","idents","loops","calls"])
        for qnum, pairs in sorted(pairs_by_q.items()):
            for a,b,s,br in sorted(pairs, key=lambda x: x[2], reverse=True):
                w.writerow([qnum, os.path.basename(a), os.path.basename(b), f"{s:.6f}",
                            f"{br['jaccard']:.6f}", f"{br['control']:.6f}", f"{br['idents']:.6f}",
                            f"{br['loops']:.6f}", f"{br['calls']:.6f}"])

# -------- CLI --------
def parse_args():
    ap = argparse.ArgumentParser(
        description="Pente-fino de similaridade C por questão (qN_SIGLA.c): fluxo de controle, assinaturas de laços, ids e chamadas."
    )
    ap.add_argument("path", help="Pasta/arquivo (usa apenas qN_SIGLA.c)")
    ap.add_argument("--k", type=int, default=DEFAULT_K, help=f"Tamanho do shingle (padrão {DEFAULT_K})")
    ap.add_argument("--no-normalize", action="store_true", help="Não normalizar identificadores para os shingles")
    ap.add_argument("--html", type=str, help="Salvar relatório HTML (ex.: fine.html)")
    ap.add_argument("--csv", type=str, help="Salvar CSV detalhado dos pares")
    return ap.parse_args()

def main():
    args = parse_args()
    paths = gather_files(args.path)
    if len(paths) < 2:
        print("⚠️  Preciso de ≥2 arquivos .c no padrão qN_SIGLA.c"); return

    feats, meta, groups = build_features(paths, k=args.k, normalize=not args.no_normalize)
    groups = {q:plist for q,plist in groups.items() if len(plist) >= 2}
    if not groups:
        print("⚠️  Nenhuma questão com 2+ arquivos válidos."); return

    pairs_by_q = pairwise_fine(groups, feats, meta)

    # Console: top 5 por questão
    for qnum, pairs in sorted(pairs_by_q.items()):
        print(f"\n== Q{qnum:02d}: TOP pares (score composto) ==")
        for a,b,s,br in sorted(pairs, key=lambda x: x[2], reverse=True)[:5]:
            print(f"{os.path.basename(a)} ↔ {os.path.basename(b)} | score={s:.3f} "
                  f"(J={br['jaccard']:.2f}, Ctl={br['control']:.2f}, Id={br['idents']:.2f}, "
                  f"Lc={br['loops']:.2f}, Call={br['calls']:.2f})")

    if args.csv:
        save_csv(pairs_by_q, args.csv)
        print(f"\n💾 CSV salvo em: {args.csv}")

    if args.html:
        root_label = os.path.basename(os.path.abspath(args.path)) if os.path.isdir(args.path) \
                     else os.path.basename(os.path.dirname(os.path.abspath(args.path)))
        generate_html(args.html, root_label, groups, pairs_by_q, feats)
        print(f"🌐 HTML salvo em: {args.html}")

if __name__ == "__main__":
    main()
