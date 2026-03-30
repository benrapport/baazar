#!/usr/bin/env python3
"""Generate a styled PDF from GAME_RESULTS.md using markdown2 + weasyprint."""

import markdown2
import weasyprint
from pathlib import Path

HERE = Path(__file__).resolve().parent
MD_FILE = HERE / "GAME_RESULTS.md"
PDF_FILE = HERE / "GAME_RESULTS.pdf"

CSS = """
@page {
    size: letter;
    margin: 0.75in 0.85in;
    @bottom-center { content: counter(page); font-size: 9pt; color: #999; }
}
body {
    font-family: -apple-system, "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.5;
    color: #1a1a1a;
}
h1 {
    font-size: 22pt;
    border-bottom: 3px solid #2563eb;
    padding-bottom: 8px;
    margin-bottom: 16px;
    color: #111;
}
h2 {
    font-size: 15pt;
    color: #2563eb;
    margin-top: 28px;
    border-bottom: 1px solid #ddd;
    padding-bottom: 4px;
}
h3 {
    font-size: 12pt;
    color: #374151;
    margin-top: 20px;
}
table {
    border-collapse: collapse;
    width: 100%;
    margin: 12px 0;
    font-size: 9.5pt;
}
th {
    background: #2563eb;
    color: white;
    padding: 6px 8px;
    text-align: left;
    font-weight: 600;
}
td {
    padding: 5px 8px;
    border-bottom: 1px solid #e5e7eb;
}
tr:nth-child(even) td {
    background: #f8fafc;
}
strong {
    color: #111;
}
ul, ol {
    padding-left: 24px;
}
li {
    margin-bottom: 4px;
}
code {
    background: #f1f5f9;
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 10pt;
}
p {
    margin: 8px 0;
}
"""

html_body = markdown2.markdown(
    MD_FILE.read_text(),
    extras=["tables", "fenced-code-blocks", "header-ids"],
)

full_html = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<style>{CSS}</style>
</head><body>{html_body}</body></html>"""

weasyprint.HTML(string=full_html).write_pdf(str(PDF_FILE))
print(f"PDF written to {PDF_FILE}")
