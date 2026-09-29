"""Build the bilingual PDF guides from the Markdown chapters in docs/en and docs/es.

EN: Markdown → HTML (with Mermaid diagrams rendered by mermaid.js) → PDF via a headless browser.
ES: Markdown → HTML (con los diagramas Mermaid dibujados por mermaid.js) → PDF con un navegador sin ventana.

Run / Ejecutar:
    python scripts/build_pdf.py            # both languages → docs/pdf/
    python scripts/build_pdf.py --lang es

Needs: `pip install markdown playwright` and either Microsoft Edge / Google Chrome installed
       or `playwright install chromium`. Internet is needed once to load mermaid.js from a CDN.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from datetime import date
from pathlib import Path

import markdown
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
OUT = DOCS / "pdf"

META = {
    "en": {"file": "GoldMLFlow_Guide_EN.pdf", "title": "MLOps for Dummies",
           "subtitle": "Predicting whether gold goes UP or DOWN in the next hour — the whole MLOps flow, step by step",
           "toc": "Contents", "by": "Educational project · Not financial advice",
           "stack": "MetaTrader 5 → DVC → MLflow → FastAPI → Docker → GitHub Actions → Streamlit",
           "repo": "Code"},
    "es": {"file": "GoldMLFlow_Guia_ES.pdf", "title": "MLOps para Dummies",
           "subtitle": "Predecir si el oro SUBE o BAJA en la próxima hora — todo el flujo MLOps, paso a paso",
           "toc": "Contenido", "by": "Proyecto educativo · No es asesoría financiera",
           "stack": "MetaTrader 5 → DVC → MLflow → FastAPI → Docker → GitHub Actions → Streamlit",
           "repo": "Código"},
}

CSS = """
@page { size: A4; margin: 16mm 14mm 18mm 14mm; }
* { box-sizing: border-box; }
body { font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; color: #1f2933; font-size: 10.5pt; line-height: 1.5; }
h1 { color: #7a5c00; border-bottom: 4px solid #D4A017; padding-bottom: 6px; font-size: 22pt; margin-top: 0; }
h2 { color: #1f2933; border-left: 6px solid #D4A017; padding-left: 10px; margin-top: 22px; font-size: 15pt; }
h3 { color: #334e68; font-size: 12.5pt; }
.chapter { page-break-before: always; }
table { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 9.5pt; page-break-inside: avoid; }
th { background: #fff3c4; color: #5c4400; text-align: left; }
th, td { border: 1px solid #e0d7b8; padding: 5px 8px; vertical-align: top; }
tr:nth-child(even) td { background: #fffdf5; }
code { background: #f4f1e8; padding: 1px 4px; border-radius: 4px; font-family: Consolas, 'Courier New', monospace; font-size: 9pt; }
pre { background: #1f2933; color: #f0f4f8; padding: 10px 12px; border-radius: 8px; font-size: 8.6pt; line-height: 1.35;
      white-space: pre-wrap; word-break: break-word; page-break-inside: avoid; }
pre code { background: none; color: inherit; padding: 0; }
blockquote { border-left: 5px solid #D4A017; background: #fffaf0; margin: 10px 0; padding: 6px 12px; color: #52606d; }
img { max-width: 100%; border-radius: 6px; border: 1px solid #e4e7eb; page-break-inside: avoid; }
td img { max-height: 230px; }
pre.mermaid { background: #ffffff; color: #1f2933; text-align: center; border: 1px dashed #e0d7b8; }
.cover { height: 250mm; display: flex; flex-direction: column; justify-content: center; text-align: center; }
.cover .medal { font-size: 70pt; }
.cover h1 { border: none; font-size: 34pt; margin: 6px 0; }
.cover .brand { font-size: 18pt; color: #D4A017; font-weight: 700; letter-spacing: 2px; }
.cover .sub { font-size: 13pt; color: #52606d; margin: 8px 30px 18px; }
.cover .stack { font-size: 10pt; background: #1f2933; color: #fff3c4; padding: 8px; border-radius: 8px; margin: 0 20px; }
.cover img { margin: 18px auto; width: 88%; }
.cover .foot { color: #7b8794; font-size: 9pt; }
.toc ul { font-size: 12pt; line-height: 2; list-style: none; padding-left: 10px; }
h1, h2, h3 { page-break-after: avoid; break-after: avoid; }
pre.mermaid svg { width: 100% !important; max-width: 100% !important; height: auto; max-height: 215mm; }
.toc a { color: #1f2933; text-decoration: none; }
a { color: #0b69a3; text-decoration: none; }
"""

NAV_LINE = re.compile(r"^(>\s*🌐.*|⬅️.*|➡️.*|\[🏠.*)$")
MERMAID = re.compile(r"```mermaid\n(.*?)```", re.S)


def portrait(src: str) -> str:
    """A4 is tall and narrow: big left-to-right diagrams become top-to-bottom so they stay readable."""
    if src.lstrip().startswith("flowchart LR") and src.count("-->") + src.count("-.") > 7:
        return src.replace("flowchart LR", "flowchart TB", 1)
    return src


def chapter_html(md_text: str, idx: int) -> tuple[str, str]:
    lines = [ln for ln in md_text.splitlines() if not NAV_LINE.match(ln.strip())]
    text = "\n".join(lines)
    title = next((ln[2:] for ln in lines if ln.startswith("# ")), f"Chapter {idx}")
    text = MERMAID.sub(lambda m: f'\n<pre class="mermaid">\n{html.escape(portrait(m.group(1)))}</pre>\n', text)
    body = markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists", "md_in_html"])
    return title, f'<section class="chapter" id="ch{idx}">{body}</section>'


def build(lang: str) -> Path:
    m = META[lang]
    chapters = sorted((DOCS / lang).glob("[0-9][0-9]-*.md"))
    parts, toc = [], []
    for i, path in enumerate(chapters):
        title, body = chapter_html(path.read_text(encoding="utf-8"), i)
        parts.append(body)
        toc.append(f'<li><a href="#ch{i}">{html.escape(title)}</a></li>')

    doc = f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8">
<base href="{(DOCS / lang).as_uri()}/"><title>GoldMLFlow — {m['title']}</title><style>{CSS}</style></head><body>
<div class="cover">
  <div class="medal">🥇</div><div class="brand">GOLDMLFLOW</div>
  <h1>{m['title']}</h1><div class="sub">{m['subtitle']}</div>
  <div class="stack">{m['stack']}</div>
  <img src="../images/dashboard_prediction.png">
  <div class="foot">{m['repo']}: github.com/MirandaCR/GoldMLFlow · {date.today():%Y-%m-%d}<br>{m['by']}</div>
</div>
<section class="chapter toc"><h1>📚 {m['toc']}</h1><ul>{''.join(toc)}</ul></section>
{''.join(parts)}
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<script>
  mermaid.initialize({{ startOnLoad: false, theme: 'neutral', flowchart: {{ htmlLabels: true }} }});
  mermaid.run({{ querySelector: 'pre.mermaid' }}).then(() => document.body.dataset.ready = '1')
    .catch(e => {{ console.error(e); document.body.dataset.ready = 'error'; }});
</script></body></html>"""

    OUT.mkdir(parents=True, exist_ok=True)
    html_path = OUT / f"_build_{lang}.html"
    html_path.write_text(doc, encoding="utf-8")
    pdf_path = OUT / m["file"]

    with sync_playwright() as p:
        browser = None
        for channel in ("msedge", "chrome", None):
            try:
                browser = p.chromium.launch(channel=channel) if channel else p.chromium.launch()
                break
            except Exception:
                continue
        if browser is None:
            raise RuntimeError("No browser found: install Edge/Chrome or run `playwright install chromium`")
        page = browser.new_page()
        page.goto(html_path.as_uri(), wait_until="networkidle")
        page.wait_for_function("document.body.dataset.ready", timeout=60000)
        state = page.evaluate("document.body.dataset.ready")
        page.pdf(path=str(pdf_path), format="A4", print_background=True, display_header_footer=True,
                 header_template="<span></span>",
                 footer_template='<div style="font-size:8px;width:100%;text-align:center;color:#7b8794">'
                                 f'GoldMLFlow · {m["title"]} · <span class="pageNumber"></span>/<span class="totalPages"></span></div>',
                 margin={"top": "14mm", "bottom": "16mm", "left": "12mm", "right": "12mm"})
        browser.close()
    html_path.unlink()
    print(f"✅ {pdf_path.relative_to(ROOT)}  (mermaid: {state})")
    return pdf_path


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", choices=["en", "es", "all"], default="all")
    args = parser.parse_args()
    for lang in (["en", "es"] if args.lang == "all" else [args.lang]):
        build(lang)


if __name__ == "__main__":
    main()
