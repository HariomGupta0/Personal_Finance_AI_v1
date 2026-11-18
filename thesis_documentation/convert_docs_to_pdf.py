"""
Academic Markdown to PDF Converter using Native Edge Engine.
Converts all files from thesis_documentation/ to thesis_documentation_pdf/
"""
import os
import re
import subprocess
import shutil

SOURCE_DIR = r"C:\Users\gupta\Documents\HARIOM\Personal_Finance_AI_FYP\thesis_documentation"
TARGET_DIR = r"C:\Users\gupta\Documents\HARIOM\Personal_Finance_AI_FYP\thesis_documentation_pdf"
EDGE_EXE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

ACADEMIC_CSS = """
@page {
    size: A4;
    margin: 20mm 15mm 20mm 15mm;
    @bottom-center {
        content: counter(page);
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 9pt;
        color: #64748b;
    }
}
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.6;
    color: #1e293b;
    background-color: #ffffff;
    margin: 0;
    padding: 0;
}
h1, h2, h3, h4, h5, h6 {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    color: #0f172a;
    font-weight: 700;
    line-height: 1.3;
    margin-top: 1.4em;
    margin-bottom: 0.5em;
    page-break-after: avoid;
}
h1 {
    font-size: 20pt;
    color: #0f172a;
    border-bottom: 2px solid #2563eb;
    padding-bottom: 6px;
    margin-top: 0.8em;
}
h2 {
    font-size: 15pt;
    color: #1e293b;
    border-bottom: 1px solid #cbd5e1;
    padding-bottom: 4px;
}
h3 {
    font-size: 12.5pt;
    color: #2563eb;
}
h4 {
    font-size: 11pt;
    color: #475569;
}
p {
    margin-top: 0;
    margin-bottom: 0.8em;
    text-align: justify;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin: 1.2em 0;
    font-size: 9pt;
    page-break-inside: avoid;
}
th, td {
    padding: 7px 10px;
    border: 1px solid #cbd5e1;
    text-align: left;
    vertical-align: top;
}
th {
    background-color: #1e293b;
    color: #ffffff;
    font-weight: 600;
}
tr:nth-child(even) {
    background-color: #f8fafc;
}
code {
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 9pt;
    background-color: #f1f5f9;
    padding: 2px 5px;
    border-radius: 4px;
    color: #0f172a;
    border: 1px solid #e2e8f0;
}
pre {
    background-color: #0f172a;
    color: #f8fafc;
    padding: 12px 14px;
    border-radius: 6px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 8.5pt;
    line-height: 1.45;
    overflow-x: auto;
    page-break-inside: avoid;
    margin: 1em 0;
}
pre code {
    background: transparent;
    border: none;
    padding: 0;
    color: #f8fafc;
}
blockquote {
    margin: 1em 0;
    padding: 8px 16px;
    background-color: #eff6ff;
    border-left: 4px solid #2563eb;
    color: #1e40af;
    font-style: italic;
}
ul, ol {
    margin-top: 0;
    margin-bottom: 0.8em;
    padding-left: 22px;
}
li {
    margin-bottom: 0.3em;
}
hr {
    border: none;
    border-top: 1px solid #e2e8f0;
    margin: 1.5em 0;
}
.badge {
    display: inline-block;
    padding: 2px 6px;
    font-size: 8pt;
    font-weight: 600;
    border-radius: 4px;
    background-color: #dbeafe;
    color: #1e40af;
}
"""

def md_to_html(md_text, title="Academic Thesis Document"):
    """Lightweight, robust Markdown to Academic HTML converter."""
    lines = md_text.splitlines()
    html_lines = []
    in_code_block = False
    code_lang = ""
    code_buffer = []
    in_table = False
    table_lines = []
    in_list = False
    list_type = None

    def flush_table():
        nonlocal in_table, table_lines, html_lines
        if not table_lines:
            in_table = False
            return
        
        headers = []
        rows = []
        is_first = True
        for row in table_lines:
            row_str = row.strip()
            if not row_str.startswith("|") or not row_str.endswith("|"):
                continue
            cells = [c.strip() for c in row_str[1:-1].split("|")]
            # Check if separator row
            if all(re.match(r"^:?-+:?$", c) for c in cells if c):
                continue
            if is_first:
                headers = cells
                is_first = False
            else:
                rows.append(cells)
        
        t_html = ["<table>"]
        if headers:
            t_html.append("  <thead><tr>")
            for h in headers:
                t_html.append(f"    <th>{inline_format(h)}</th>")
            t_html.append("  </tr></thead>")
        if rows:
            t_html.append("  <tbody>")
            for r in rows:
                t_html.append("    <tr>")
                for c in r:
                    t_html.append(f"      <td>{inline_format(c)}</td>")
                t_html.append("    </tr>")
            t_html.append("  </tbody>")
        t_html.append("</table>")
        html_lines.append("\n".join(t_html))
        table_lines = []
        in_table = False

    def inline_format(text):
        # Escape HTML entities (except intentional tags)
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        # Inline code
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
        # Bold + Italic
        text = re.sub(r"\*\*\*([^*]+)\*\*\*", r"<strong><em>\1</em></strong>", text)
        # Bold
        text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
        # Italic
        text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
        # Links
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
        # Math tags
        text = re.sub(r"\$([^\$]+)\$", r'<code class="math">\1</code>', text)
        return text

    for line in lines:
        stripped = line.strip()

        # Code block handling
        if stripped.startswith("```"):
            if in_code_block:
                code_content = "\n".join(code_buffer)
                code_content = code_content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                html_lines.append(f"<pre><code>{code_content}</code></pre>")
                code_buffer = []
                in_code_block = False
            else:
                if in_table:
                    flush_table()
                in_code_block = True
                code_lang = stripped[3:].strip()
            continue

        if in_code_block:
            code_buffer.append(line)
            continue

        # Table handling
        if stripped.startswith("|") and stripped.endswith("|"):
            in_table = True
            table_lines.append(stripped)
            continue
        elif in_table:
            flush_table()

        # Blank line
        if not stripped:
            if in_list:
                html_lines.append(f"</{list_type}>")
                in_list = False
                list_type = None
            continue

        # Headings
        if stripped.startswith("#"):
            if in_list:
                html_lines.append(f"</{list_type}>")
                in_list = False
            m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
            if m:
                level = len(m.group(1))
                h_text = inline_format(m.group(2))
                html_lines.append(f"<h{level}>{h_text}</h{level}>")
                continue

        # Horizontal Rule
        if re.match(r"^(\-{3,}|\*{3,}|_{3,})$", stripped):
            if in_list:
                html_lines.append(f"</{list_type}>")
                in_list = False
            html_lines.append("<hr />")
            continue

        # Blockquote
        if stripped.startswith(">"):
            if in_list:
                html_lines.append(f"</{list_type}>")
                in_list = False
            bq_text = inline_format(stripped[1:].strip())
            html_lines.append(f"<blockquote>{bq_text}</blockquote>")
            continue

        # Unordered list
        if stripped.startswith(("- ", "* ")):
            if not in_list or list_type != "ul":
                if in_list:
                    html_lines.append(f"</{list_type}>")
                html_lines.append("<ul>")
                in_list = True
                list_type = "ul"
            li_text = inline_format(stripped[2:].strip())
            html_lines.append(f"  <li>{li_text}</li>")
            continue

        # Ordered list
        m_ol = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if m_ol:
            if not in_list or list_type != "ol":
                if in_list:
                    html_lines.append(f"</{list_type}>")
                html_lines.append("<ol>")
                in_list = True
                list_type = "ol"
            li_text = inline_format(m_ol.group(2).strip())
            html_lines.append(f"  <li>{li_text}</li>")
            continue

        # Standard Paragraph
        if in_list:
            html_lines.append(f"</{list_type}>")
            in_list = False
            list_type = None

        p_text = inline_format(stripped)
        html_lines.append(f"<p>{p_text}</p>")

    if in_table:
        flush_table()
    if in_list:
        html_lines.append(f"</{list_type}>")

    body_html = "\n".join(html_lines)
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
{ACADEMIC_CSS}
</style>
</head>
<body>
{body_html}
</body>
</html>
"""
    return full_html


def process_all_files():
    print(f"Starting conversion from {SOURCE_DIR} to {TARGET_DIR}...")
    os.makedirs(TARGET_DIR, exist_ok=True)

    # 1. Copy SVG diagram folder
    src_diagrams = os.path.join(SOURCE_DIR, "diagrams")
    tgt_diagrams = os.path.join(TARGET_DIR, "diagrams")
    if os.path.exists(src_diagrams):
        if os.path.exists(tgt_diagrams):
            shutil.rmtree(tgt_diagrams)
        shutil.copytree(src_diagrams, tgt_diagrams)
        print("Diagrams folder mirrored successfully.")

    # 2. Find all markdown files
    md_files = []
    for root, dirs, files in os.walk(SOURCE_DIR):
        for f in files:
            if f.endswith(".md"):
                md_files.append(os.path.join(root, f))

    print(f"Found {len(md_files)} markdown files to convert.")

    for md_path in md_files:
        rel_path = os.path.relpath(md_path, SOURCE_DIR)
        rel_pdf = os.path.splitext(rel_path)[0] + ".pdf"
        tgt_pdf_path = os.path.join(TARGET_DIR, rel_pdf)
        os.makedirs(os.path.dirname(tgt_pdf_path), exist_ok=True)

        # Temporary HTML path
        temp_html_path = os.path.join(TARGET_DIR, os.path.splitext(rel_path)[0] + "_temp.html")
        os.makedirs(os.path.dirname(temp_html_path), exist_ok=True)

        try:
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()

            doc_title = os.path.splitext(os.path.basename(md_path))[0].replace("_", " ").title()
            html_content = md_to_html(content, title=doc_title)

            with open(temp_html_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            # Invoke Edge headless print-to-pdf
            cmd = [
                EDGE_EXE,
                "--headless",
                "--disable-gpu",
                "--no-pdf-header-footer",
                f"--print-to-pdf={tgt_pdf_path}",
                temp_html_path
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Remove temp html
            if os.path.exists(temp_html_path):
                os.remove(temp_html_path)

            file_size = os.path.getsize(tgt_pdf_path)
            print(f"Generated: {rel_pdf} ({file_size / 1024:.1f} KB)")
        except Exception as e:
            print(f"Error converting {rel_path}: {e}")

    print("\nAll Markdown files successfully converted to PDF!")

if __name__ == "__main__":
    process_all_files()

