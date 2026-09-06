# -*- coding: utf-8 -*-
"""
build_langchain_word.py —— 把 _content_NN_*.md 源码排版成一份 Word 学习笔记。
生成 LangChain智能体开发实战_学习笔记.docx
用法：python build_langchain_word.py
依赖：python-docx（已装 1.2.0）
"""
import re
import glob
import os
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTENT_GLOB = os.path.join(BASE_DIR, "_content_*.md")
OUTPUT_DOCX = os.path.join(BASE_DIR, "LangChain智能体开发实战_学习笔记.docx")

# 等宽字体（Windows 常见 monospace）
MONO_FONT = "Consolas"


def set_cell_shading(cell, color_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color_hex)
    tcPr.append(shd)


def add_code_block(doc, lines):
    """每个代码行一段，Consolas 等宽，浅灰底纹，紧凑间距。"""
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(2)
    pf.space_after = Pt(2)
    pf.left_indent = Inches(0.2)
    pf.line_spacing = 1.0
    # 整段浅灰底纹（加个边框感：用 shading 模拟）
    pPr = p._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), "F2F2F2")
    pPr.append(shd)
    run = p.add_run(lines)
    run.font.name = MONO_FONT
    run.font.size = Pt(9)
    run._element.rPr.rFonts.set(qn("w:eastAsia"), MONO_FONT)


def add_inline_run(paragraph, text, mono=False):
    run = paragraph.add_run(text)
    if mono:
        run.font.name = MONO_FONT
        run.font.size = Pt(10)
        run._element.rPr.rFonts.set(qn("w:eastAsia"), MONO_FONT)
    return run


def add_paragraph_with_inline_code(doc, text, style=None):
    """把行内 `code` 用等宽样式渲染，其余为正文。"""
    p = doc.add_paragraph(style=style)
    # 按 `...` 切分
    parts = re.split(r"(`[^`]+`)", text)
    for part in parts:
        if not part:
            continue
        if part.startswith("`") and part.endswith("`"):
            run = add_inline_run(p, part[1:-1], mono=True)
        else:
            run = p.add_run(part)
    return p


def add_table(doc, rows):
    """rows: list[list[str]]，首行为表头。"""
    if not rows:
        return
    n_cols = max(len(r) for r in rows)
    table = doc.add_table(rows=0, cols=n_cols)
    table.style = "Table Grid"
    for i, row in enumerate(rows):
        cells = table.add_row().cells
        for j in range(n_cols):
            val = row[j] if j < len(row) else ""
            if i == 0:
                run = cells[j].paragraphs[0].add_run(val)
                run.bold = True
                set_cell_shading(cells[j], "D9E2F3")
            else:
                cells[j].paragraphs[0].add_run(val)
    doc.add_paragraph()  # 表格后空一行


def main():
    content_files = sorted(glob.glob(CONTENT_GLOB))
    if not content_files:
        raise SystemExit(f"未找到源文件: {CONTENT_GLOB}（请先运行，确保 _content_*.md 存在）")
    print(f"找到 {len(content_files)} 个源文件")
    for f in content_files:
        print("  -", os.path.basename(f))

    doc = Document()
    # 基础字体
    normal = doc.styles["Normal"]
    normal.font.name = "Microsoft YaHei"
    normal.font.size = Pt(11)
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")

    # 合并所有源码
    for fname in content_files:
        with open(fname, "r", encoding="utf-8") as fp:
            lines = fp.read().split("\n")

        in_code = False
        code_buffer = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.rstrip()

            # 代码块开/闭 (```)
            if stripped.strip().startswith("```"):
                if in_code:
                    # 结束
                    add_code_block(doc, "\n".join(code_buffer))
                    code_buffer = []
                    in_code = False
                else:
                    in_code = True
                i += 1
                continue

            if in_code:
                code_buffer.append(line)
                i += 1
                continue

            # 空行
            if stripped == "":
                i += 1
                continue

            # 标题 (#### 等)
            m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
            if m:
                hashes = len(m.group(1))
                text = m.group(2).strip()
                level = max(1, min(hashes, 4))  # Heading1-4
                heading = doc.add_heading("", level=level)
                add_paragraph_with_inline_code_parts(heading, text, is_heading=True)
                i += 1
                continue

            # 表格行（含 |）
            if stripped.startswith("|"):
                table_rows = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    row_content = lines[i].strip().strip("|")
                    cells = [c.strip() for c in row_content.split("|")]
                    # 跳过分隔行 |---|---|
                    if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                        table_rows.append(cells)
                    i += 1
                if table_rows:
                    add_table(doc, table_rows)
                continue

            # 列表项 (- , * , 数字.)
            m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", stripped)
            if m:
                indent = len(m.group(1)) // 3
                text = m.group(3)
                style = "List Bullet" if m.group(2) in ("-", "*") else "List Number"
                if indent > 0:
                    style = "List Bullet 2" if m.group(2) in ("-", "*") else "List Number 2"
                add_paragraph_with_inline_code(doc, text, style=style)
                i += 1
                continue

            # 引用 (>  )
            if stripped.startswith(">"):
                text = stripped.lstrip(">").strip()
                p = doc.add_paragraph()
                run = p.add_run(text)
                run.italic = True
                run.font.color.rgb = RGBColor(0x60, 0x60, 0x60)
                i += 1
                continue

            # 普通段落
            add_paragraph_with_inline_code(doc, stripped)
            i += 1

        doc.add_page_break()

    if not os.path.exists(OUTPUT_DOCX):
        pass
    doc.save(OUTPUT_DOCX)
    print(f"\n已生成: {OUTPUT_DOCX}")


def add_paragraph_with_inline_code_parts(paragraph, text, is_heading=False):
    """向已创建的段落填充行内 code 片段（用于标题也渲染行内 `code`）。"""
    parts = re.split(r"(`[^`]+`)", text)
    for part in parts:
        if not part:
            continue
        if part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1])
            run.font.name = MONO_FONT
            run._element.rPr.rFonts.set(qn("w:eastAsia"), MONO_FONT)
            if is_heading:
                run.bold = True
        else:
            run = paragraph.add_run(part)
            if is_heading:
                run.bold = True


if __name__ == "__main__":
    main()
