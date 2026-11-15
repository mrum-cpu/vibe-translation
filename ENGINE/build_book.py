#!/usr/bin/env python3
"""PROJECT ENGINE — final assembly: FINAL units -> chapters -> MASTER_BOOK.docx.

Usage: python3 build_book.py
Refuses to assemble unless completeness checks pass (Constitution §37).
PDF export requires LibreOffice (soffice); skipped with a notice if absent.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine_core import p, now_iso, load_state, load_progress

def main():
    state = load_state()
    prog = load_progress()
    total = state.get("total_units", 0)
    final_ids = sorted(uid for uid, u in prog["units"].items() if u.get("status") == "FINAL")
    if total == 0 or len(final_ids) != total:
        sys.exit(f"ASSEMBLY BLOCKED: FINAL units {len(final_ids)}/{total}. "
                 "Run completeness.py and approve all units first.")

    manifest_file = p("SOURCE", "source_units", "units_manifest.json")
    with open(manifest_file, encoding="utf-8") as f:
        manifest = json.load(f)

    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn

    def set_bidi(para):
        """Real RTL: inject <w:bidi/> into pPr (python-docx has no rtl API)."""
        ppr = para._p.get_or_add_pPr()
        if ppr.find(qn("w:bidi")) is None:
            ppr.append(ppr.makeelement(qn("w:bidi"), {}))

    doc = Document()
    title = state.get("book_title") or manifest["book_id"]
    t = doc.add_heading(title, level=0)
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ar_title = doc.add_paragraph("الوجه الروحي للتاريخ")
    ar_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_bidi(ar_title)
    ed = doc.add_paragraph(f"الطبعة الرقمية — أُنشئت في {now_iso()}")
    ed.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_bidi(ed)

    # Amiri font (الخط الأميري) on every style used, including complex-script (cs)
    # so Word renders Arabic with Amiri, not the default cs font.
    def set_amiri(style):
        try:
            style.font.name = "Amiri"
            rpr = style.element.get_or_add_rPr()
            rfonts = rpr.get_or_add_rFonts()
            for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
                rfonts.set(qn(attr), "Amiri")
            sz = rpr.find(qn("w:sz"))
            szcs = rpr.makeelement(qn("w:szCs"), {qn("w:val"): sz.get(qn("w:val")) if sz is not None else "28"})
            rpr.append(szcs)
        except AttributeError:
            pass

    for sname in ("Normal", "Title", "Heading 1", "Heading 2", "Heading 3", "Heading 4"):
        try:
            set_amiri(doc.styles[sname])
        except KeyError:
            pass
    doc.styles["Normal"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    def add_rtl_heading(text, level):
        h = doc.add_heading(text, level=level)
        set_bidi(h)
        return h

    def add_rtl_para(text):
        para = doc.add_paragraph(text)
        set_bidi(para)
        para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        return para

    units_dir = p("TRANSLATION", "units")
    count = 0
    seen_files = set()
    for uid in final_ids:
        rec = prog["units"][uid]
        tf = rec.get("translation_file")
        fp = os.path.join(units_dir, tf) if tf else None
        if not fp or not os.path.exists(fp):
            sys.exit(f"ASSEMBLY BLOCKED: missing translation file for {uid}")
        if fp in seen_files:
            continue  # shared unit file (e.g. U0001+U0002) — assemble once
        seen_files.add(fp)
        with open(fp, encoding="utf-8") as f:
            body = f.read()
        body = re.sub(r"^<!--.*?-->\s*", "", body, flags=re.S)
        # render markdown: headings -> Word headings; other lines grouped into paragraphs
        buf = []
        def flush():
            if buf:
                add_rtl_para(" ".join(buf).strip())
                buf.clear()
        for line in body.splitlines():
            st = line.strip()
            if not st:
                flush()
            elif st.startswith("### "):
                flush(); add_rtl_heading(st[4:].strip(), 3)
            elif st.startswith("## "):
                flush(); add_rtl_heading(st[3:].strip(), 2)
            elif st.startswith("# "):
                flush(); add_rtl_heading(st[2:].strip(), 1)
            else:
                buf.append(st)
        flush()
        count += 1

    out = p("OUTPUT", "MASTER_BOOK.docx")
    doc.save(out)
    print(f"ASSEMBLY OK: {count} FINAL units -> {out}")

    soffice = None
    for c in ("/usr/bin/soffice", "/usr/bin/libreoffice"):
        if os.path.exists(c):
            soffice = c
            break
    if soffice:
        os.system(f'{soffice} --headless --convert-to pdf --outdir "{p("OUTPUT")}" "{out}"')
        print(f"PDF: {p('OUTPUT', 'MASTER_BOOK.pdf')}")
    else:
        print("PDF: skipped — LibreOffice not installed; MASTER_BOOK.docx is the master copy.")

if __name__ == "__main__":
    main()
