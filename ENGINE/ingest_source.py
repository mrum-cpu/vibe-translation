#!/usr/bin/env python3
"""PROJECT ENGINE — source ingestion: PDF/EPUB/TXT -> numbered source units.

Usage:
  python3 ingest_source.py SOURCE/source_original.pdf [--unit-words 900] [--book-id BOOK]

Produces:
  SOURCE/source_units/UNIT_0001.txt ...
  SOURCE/source_units/units_manifest.json   (unit_id, pages, word_count, char_count)
  TRANSLATION/units/UNIT_0001.source.md     (source text copy for verification)
  STATE: project_status -> MAPPING (BOOK_MAP must be built before translating)
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine_core import p, now_iso, load_state, save_state, load_progress, save_progress

def extract_pages(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        import pymupdf
        doc = pymupdf.open(path)
        pages = [pg.get_text("text") for pg in doc]
        doc.close()
        return pages
    if ext == ".epub":
        raise SystemExit("EPUB support: convert to PDF or TXT first (not yet wired).")
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read().split("\f")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--unit-words", type=int, default=900)
    ap.add_argument("--book-id", default="BOOK")
    args = ap.parse_args()

    src = args.source if os.path.isabs(args.source) else p(args.source)
    if not os.path.exists(src):
        sys.exit(f"SOURCE NOT FOUND: {src}")

    pages = extract_pages(src)
    words = [(w, i + 1) for i, txt in enumerate(pages) for w in txt.split()]
    if not words:
        sys.exit("NO EXTRACTABLE TEXT — source is likely scanned images; needs OCR pipeline.")

    units_dir = p("SOURCE", "source_units")
    os.makedirs(units_dir, exist_ok=True)

    manifest = {"book_id": args.book_id, "source_file": os.path.basename(src),
                "total_pages": len(pages), "unit_words": args.unit_words,
                "created": now_iso(), "units": []}

    chunks, buf, cur_pages = [], [], set()
    for w, pg in words:
        buf.append(w)
        cur_pages.add(pg)
        if len(buf) >= args.unit_words:
            chunks.append((" ".join(buf), cur_pages))
            buf, cur_pages = [], set()
    if buf:
        chunks.append((" ".join(buf), cur_pages))

    for idx, (text, pgs) in enumerate(chunks, 1):
        uid = f"U{idx:04d}"
        with open(os.path.join(units_dir, f"UNIT_{idx:04d}.txt"), "w", encoding="utf-8") as f:
            f.write(text)
        sp = sorted(pgs)
        manifest["units"].append({"unit_id": uid,
                                  "source_pages": [sp[0], sp[-1]],
                                  "word_count": len(text.split()),
                                  "char_count": len(text)})
        with open(p("TRANSLATION", "units", f"{uid}.source.md"), "w", encoding="utf-8") as f:
            f.write(f"# SOURCE OF {uid} (pages {sp[0]}-{sp[-1]})\n\n{text}\n")

    with open(os.path.join(units_dir, "units_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    prog = load_progress()
    for u in manifest["units"]:
        prog["units"].setdefault(u["unit_id"], {"status": "INGESTED", "history": []})
    save_progress(prog)

    state = load_state()
    state["project_id"] = state["project_id"] or f"{args.book_id}-{now_iso()[:10]}"
    state["total_units"] = len(manifest["units"])
    state["project_status"] = "MAPPING"
    save_state(state)

    print(f"INGESTION OK: pages={len(pages)} units={len(manifest['units'])} "
          f"words={sum(u['word_count'] for u in manifest['units'])}")
    print("STATUS: MAPPING — build BOOK_MAP.md before translating")

if __name__ == "__main__":
    main()
