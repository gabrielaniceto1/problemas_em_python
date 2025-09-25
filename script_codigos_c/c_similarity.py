#!/usr/bin/env python3
import os, re, math, argparse, itertools, csv, datetime
from collections import Counter, defaultdict

C_EXTS = {".c"}  # restringindo a .c conforme seu padrão
DEFAULT_K = 5

# --------- Pré-processamento ---------
def strip_comments_and_strings(code: str) -> str:
    str_re = r"""
        ("([^"\\]|\\.)*") |       # string "..."
        ('([^'\\]|\\.)*')         # char '...'
    """
    code = re.sub(str_re, lambda m: " " * len(m.group(0)), code, flags=re.VERBOSE | re.DOTALL)
    code = re.sub(r"/\*.*?\*/", lambda m: " " * len(m.group(0)), code, flags=re.DOTALL)
    code = re.sub(r"//[^\n]*", "", code)
    return code

TOKEN_RE = re.compile(
    r"""
    ([A-Za-z_][A-Za-z_0-9]*)         # identificadores/palavras-chave
    | (0x[0-9A-Fa-f]+)               # hex
    | (\d+\.\d*|\.\d+|\d+)           # números
    | (==|!=|<=|>=|->|\+\+|--|&&|\|\||<<|>>|::)
    | ([{}()\[\];,.:?~!%^&*+\-/|<>=])
    """,
    re.VERBOSE,
)

def tokenize(code: str):
    return [t for t in (m.group(0) for m in TOKEN_RE.finditer(code)) if t and not t.isspace()]

C_KEYWORDS = {
    'auto','break','case','char','const','continue','default','do','double','else','enum','extern',
    'float','for','goto','if','inline','int','long','register','restrict','return','short','signed',
    'sizeof','static','struct','switch','typedef','union','unsigned','void','volatile','while',
    '_Bool','_Complex','_Imaginary'
}

def normalize_identifiers(tokens):
    id_map = {}
    out = []
    next_id = 1
    for t in tokens:
        if re.match(r"[A-Za-z_][A-Za-z_0-9]*$", t) and t not in C_KEYWORDS:
            if t not in id_map:
                id_map[t] = f"ID{next_id}"
                next_id += 1
            out.append(id_map[t])
        else:
            out.append(t)
    return out

# --------- Similaridades ---------
def shingles(tokens, k=DEFAULT_K):
    if len(tokens) < k:
        return set()
    return {" ".join(tokens[i:i+k]) for i in range(len(tokens) - k + 1)}

def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0

def cosine_counter(ca: Counter, cb: Counter) -> float:
    if not ca and not cb:
        return 1.0
    keys = set(ca) | set(cb)
    dot = sum(ca[k] * cb[k] for k in keys)
    na = math.sqrt(sum(v*v for v in ca.values()))
    nb = math.sqrt(sum(v*v for v in cb.values()))
    return dot / (na * nb) if na and nb else 0.0

# --------- Nome → (questão, sigla) ---------
# aceita nomes tipo: q1_joao.c, q02_maria.c, Q10_ABC.c
QNAME_RE = re.compile(r"^[qQ](\d+)_([A-Za-z0-9_-]+)\.c$")

def parse_qsigla(path):
    base = os.path.basename(path)
    m = QNAME_RE.match(base)
    if not m:
        return None
    qnum = int(m.group(1))
    sigla = m.group(2)
    return qnum, sigla

# --------- Leitura de arquivos ---------
def gather_files(root):
    paths = []
    if os.path.isfile(root):
        if os.path.splitext(root)[1].lower() in C_EXTS and parse_qsigla(root):
            paths.append(root)
    else:
        for dirpath, _, files in os.walk(root):
            for name in files:
                if os.path.splitext(name)[1].lower() in C_EXTS:
                    full = os.path.join(dirpath, name)
                    if parse_qsigla(full):
                        paths.append(full)
    return sorted(paths)

# --------- Pipeline ---------
def read_code(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def prepare_tokens(path, normalize=True):
    code = read_code(path)
    code = strip_comments_and_strings(code)
    toks = tokenize(code)
    return normalize_identifiers(toks) if normalize else toks

def build_features(paths, k=DEFAULT_K, normalize=True):
    feats = {}
    tf = {}
    meta = {}
    groups = defaultdict(list)  # questão -> [paths]
    for p in paths:
        meta[p] = parse_qsigla(p)  # (qnum, sigla)
        if not meta[p]:
            continue
        qnum, _ = meta[p]
        toks = prepare_tokens(p, normalize=normalize)
        feats[p] = {"tokens": toks, "shingles": shingles(toks, k=k)}
        tf[p] = Counter(toks)
        groups[qnum].append(p)
    return feats, tf, meta, groups

def pairwise_scores_grouped(groups, feats, tf, meta):
    """
    Retorna:
      pairs_by_q[qnum] = [(a,b,j,c), ...]  (apenas combinações dentro da mesma questão, sem repetição)
    """
    pairs_by_q = {}
    for qnum, plist in groups.items():
        local_pairs = []
        # combinações sem repetição já evita comparar A×B e B×A
        for a, b in itertools.combinations(plist, 2):
            # se por acaso houver mesma sigla duplicada, ignora comparar consigo mesmo
            if meta[a][1] == meta[b][1]:
                continue
            j = jaccard(feats[a]["shingles"], feats[b]["shingles"])
            c = cosine_counter(tf[a], tf[b])
            local_pairs.append((a, b, j, c))
        pairs_by_q[qnum] = local_pairs
    return pairs_by_q

# --------- HTML helpers ---------
def html_escape(s: str) -> str:
    return (s.replace("&","&amp;").replace("<","&lt;")
             .replace(">","&gt;").replace('"',"&quot;").replace("'","&#39;"))

def percentage(x: float) -> str:
    return f"{x*100:.1f}%"

def best_match_per_file_in_question(q_paths, pairs):
    """
    Para uma questão específica:
      retorna dict: file -> (best_other, best_j, best_c)
    """
    best = {p: (None, -1.0, -1.0) for p in q_paths}
    for a, b, j, c in pairs:
        if j > best[a][1]:
            best[a] = (b, j, c)
        if j > best[b][1]:
            best[b] = (a, j, c)
    return best

def generate_html(output_path, root_label, groups, pairs_by_q, k, normalize, meta):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    qnums_sorted = sorted(groups.keys())

    def cls_for(j):
        return "good" if j >= 0.7 else ("mid" if j >= 0.4 else "low")

    html = f"""<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Similaridade C — {html_escape(root_label)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root {{
    --bg:#0b1020; --card:#121a33; --muted:#93a4c3; --text:#e8efff; --accent:#8ab4ff; --ok:#7ad97a; --warn:#ffd36e;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; background: var(--bg); color: var(--text); }}
  header {{ padding: 24px; border-bottom: 1px solid #213055; background: linear-gradient(180deg,#0f1630,transparent); }}
  h1 {{ margin: 0 0 6px; font-weight: 700; letter-spacing: .3px; }}
  .sub {{ color: var(--muted); font-size: 14px; }}
  main {{ padding: 24px; max-width: 1100px; margin: 0 auto; }}
  .card {{ background: var(--card); border: 1px solid #1f2b4b; border-radius: 16px; padding: 16px; margin-bottom: 20px; }}
  .qtitle {{ margin: 6px 0 12px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  th, td {{ padding: 10px 12px; border-bottom: 1px solid #1f2b4b; text-align: left; }}
  th {{ color: var(--muted); font-weight: 600; }}
  tr:hover td {{ background: rgba(255,255,255,0.03); }}
  .pct {{ font-variant-numeric: tabular-nums; font-weight: 600; }}
  .good {{ color: var(--ok); }}
  .mid {{ color: var(--warn); }}
  .low {{ color: var(--muted); }}
  footer {{ color: var(--muted); font-size: 12px; padding: 24px; text-align:center; }}
  .pill {{ display:inline-block; padding: 2px 8px; border-radius: 999px; border:1px solid #2a3c6e; color: var(--muted); font-size: 12px; }}
</style>
</head>
<body>
<header>
  <h1>Relatório de Similaridade — {html_escape(root_label)}</h1>
  <div class="sub">Gerado em {html_escape(ts)} · k-shingles = {k} · Normalização de identificadores = {"sim" if normalize else "não"}</div>
</header>
<main>
"""

    for qnum in qnums_sorted:
        q_paths = sorted(groups[qnum], key=lambda p: os.path.basename(p))
        pairs = pairs_by_q.get(qnum, [])
        best = best_match_per_file_in_question(q_paths, pairs)

        # monta linhas só com o MELHOR par por arquivo
        rows = []
        for p in q_paths:
            mate, j, c = best[p]
            mate_name = os.path.basename(mate) if mate else "—"
            rows.append((os.path.basename(p), mate_name, j, c))
        rows.sort(key=lambda x: x[2], reverse=True)

        html += f"""  <section class="card">
    <h2 class="qtitle">Questão Q{qnum:02d}</h2>
    <table>
      <thead>
        <tr>
          <th>Arquivo</th>
          <th>Maior Similaridade com</th>
          <th>Similaridade (Jaccard)</th>
          <th>Similaridade (Cosseno)</th>
        </tr>
      </thead>
      <tbody>
"""
        for fname, mate_name, j, c in rows:
            cls = cls_for(j if j is not None else 0.0)
            jtxt = percentage(j) if j >= 0 else "—"
            ctxt = percentage(c) if c >= 0 else "—"
            html += f"""        <tr>
          <td>{html_escape(fname)}</td>
          <td>{html_escape(mate_name)}</td>
          <td class="pct {cls}">{jtxt}</td>
          <td class="pct">{ctxt}</td>
        </tr>
"""
        html += """      </tbody>
    </table>
  </section>
"""

    html += f"""</main>
<footer>
  <span class="pill">Pasta: {html_escape(root_label)}</span>
  <div style="margin-top:10px">Somente arquivos com padrão <code>qN_SIGLA.c</code> foram considerados. Comparações ocorrem apenas dentro da mesma questão, sem repetições; exibimos somente o melhor par por arquivo (Jaccard).</div>
</footer>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

# --------- CSV (opcional): salva só pares dentro de cada questão ---------
def save_csv_grouped(pairs_by_q, out_csv):
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["question", "file_a", "file_b", "jaccard_k_shingles", "cosine_tokens"])
        for qnum, pairs in sorted(pairs_by_q.items()):
            for a,b,j,c in pairs:
                w.writerow([qnum, os.path.basename(a), os.path.basename(b), f"{j:.6f}", f"{c:.6f}"])

# --------- CLI ---------
def parse_args():
    ap = argparse.ArgumentParser(
        description="Similaridade de códigos C por questão (qN_SIGLA.c): compara apenas dentro da mesma questão e mostra o melhor par por arquivo em HTML."
    )
    ap.add_argument("path", help="Pasta (ou arquivo .c) a analisar; usa apenas nomes no padrão qN_SIGLA.c")
    ap.add_argument("--k", type=int, default=DEFAULT_K, help=f"Tamanho do shingle (padrão {DEFAULT_K})")
    ap.add_argument("--no-normalize", action="store_true", help="Não normalizar identificadores")
    ap.add_argument("--html", type=str, help="Salvar relatório em HTML (ex.: report.html)")
    ap.add_argument("--csv", type=str, help="Salvar CSV dos pares (por questão)")
    return ap.parse_args()

def main():
    args = parse_args()
    paths = gather_files(args.path)
    if len(paths) < 2:
        print("⚠️  Preciso de pelo menos 2 arquivos .c no padrão qN_SIGLA.c")
        for p in paths:
            print("Encontrado:", p)
        return

    normalize = not args.no_normalize
    feats, tf, meta, groups = build_features(paths, k=args.k, normalize=normalize)

    # remove questões com menos de 2 arquivos
    groups = {q:plist for q,plist in groups.items() if len(plist) >= 2}
    if not groups:
        print("⚠️  Nenhuma questão possui 2+ arquivos válidos para comparar.")
        return

    pairs_by_q = pairwise_scores_grouped(groups, feats, tf, meta)

    # Console: resumo por questão (top 5 pares por Jaccard)
    for qnum, pairs in sorted(pairs_by_q.items()):
        print(f"\n== Q{qnum:02d}: top pares por Jaccard ==")
        for a,b,j,c in sorted(pairs, key=lambda x: x[2], reverse=True)[:5]:
            print(f"{os.path.basename(a)} ↔ {os.path.basename(b)} | Jaccard={j:.3f} | Cosseno={c:.3f}")

    # CSV opcional (pares por questão)
    if args.csv:
        save_csv_grouped(pairs_by_q, args.csv)
        print(f"\n💾 CSV salvo em: {args.csv}")

    # HTML opcional (somente melhor par por arquivo, por questão)
    if args.html:
        if os.path.isdir(args.path):
            root_label = os.path.basename(os.path.abspath(args.path)) or args.path
        else:
            root_label = os.path.basename(os.path.dirname(os.path.abspath(args.path))) or "arquivos"
        generate_html(args.html, root_label, groups, pairs_by_q, args.k, normalize, meta)
        print(f"🌐 HTML salvo em: {args.html}")

if __name__ == "__main__":
    main()
