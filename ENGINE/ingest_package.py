#!/usr/bin/env python3
"""PROJECT ENGINE — package ingestion: validate + accept or reject a TRANSLATION PACKAGE.

Usage:
  python3 ingest_package.py PACKAGES/inbox/<file>.txt

Protocol markers (fixed, per Constitution §15):
  PACKAGE_START / PACKAGE_END with header fields PACKAGE_ID, BOOK_ID, CHAPTER_ID,
  UNIT_START, UNIT_END, SOURCE_RANGE, SOURCE_WORD_COUNT, TRANSLATION_STATUS,
  and blocks TRANSLATION, GLOSSARY, NAME_REGISTER, DECISIONS, QA.

Validation (§18): markers integrity, header fields, known unit range, translation
present, no duplicate units, no sequence gap. Reject -> PACKAGES/rejected/.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine_core import (p, now_iso, load_state, save_state, load_progress,
                         save_progress, set_unit_state, backup,
                         append_table_row, next_decision_id, recompute_state_counters)

MARKERS = ["PACKAGE_START", "TRANSLATION_START", "TRANSLATION_END",
           "GLOSSARY_START", "GLOSSARY_END", "NAME_REGISTER_START",
           "NAME_REGISTER_END", "DECISIONS_START", "DECISIONS_END",
           "QA_START", "QA_END", "PACKAGE_END"]
OPTIONAL_MARKERS = ["ANOMALIES_START", "ANOMALIES_END"]

def reject(pkg_file, reason):
    dst = p("PACKAGES", "rejected", os.path.basename(pkg_file))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(pkg_file):
        with open(pkg_file, encoding="utf-8") as f:
            body = f.read()
        with open(dst, "w", encoding="utf-8") as f:
            f.write(body)
    prog = load_progress()
    prog["packages_rejected"] = prog.get("packages_rejected", 0) + 1
    save_progress(prog)
    print(f"PACKAGE_REJECTED: {reason}")
    return 1

def block(text, start, end):
    m = re.search(rf"^{start}\s*\n(.*?)^{end}\s*$", text, re.M | re.S)
    return m.group(1).strip() if m else None

def parse_pkg(text):
    if not text.lstrip().startswith("PACKAGE_START") or not text.rstrip().endswith("PACKAGE_END"):
        return None, "missing PACKAGE_START/PACKAGE_END integrity"
    for mk in MARKERS:
        if not re.search(rf"^{mk}\s*$", text, re.M):
            return None, f"missing marker: {mk}"
    header = {}
    head_m = re.search(r"^PACKAGE_START\s*\n(.*?)(?=^TRANSLATION_START$)", text, re.M | re.S)
    for line in head_m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            header[k.strip()] = v.strip()
    return {
        "header": header,
        "translation": block(text, "TRANSLATION_START", "TRANSLATION_END"),
        "glossary": block(text, "GLOSSARY_START", "GLOSSARY_END") or "",
        "names": block(text, "NAME_REGISTER_START", "NAME_REGISTER_END") or "",
        "decisions": block(text, "DECISIONS_START", "DECISIONS_END") or "",
        "anomalies": block(text, "ANOMALIES_START", "ANOMALIES_END") or "",
        "qa": block(text, "QA_START", "QA_END") or "",
    }, None

def parse_table_rows(md):
    rows = []
    for line in md.splitlines():
        line = line.strip()
        if line.startswith("|") and not re.match(r"^\|[\s:\-|]+\|$", line):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if cells and cells[0] and cells[0] not in ("SOURCE TERM", "ORIGINAL", "DECISION_ID", "ANOMALY_ID"):
                rows.append(cells)
    return rows

def main():
    if len(sys.argv) != 2:
        sys.exit("usage: ingest_package.py <package-file>")
    pkg_file = sys.argv[1]
    if not os.path.exists(pkg_file):
        return reject(pkg_file, f"file not found: {pkg_file}")

    with open(pkg_file, encoding="utf-8") as f:
        text = f.read()
    pkg, err = parse_pkg(text)
    if err:
        return reject(pkg_file, err)

    h = pkg["header"]
    for field in ("PACKAGE_ID", "BOOK_ID", "CHAPTER_ID", "UNIT_START", "UNIT_END"):
        if not h.get(field):
            return reject(pkg_file, f"missing header field: {field}")

    state = load_state()
    if h["PACKAGE_ID"] == state.get("last_package_id"):
        return reject(pkg_file, f"duplicate PACKAGE_ID: {h['PACKAGE_ID']}")

    m_s, m_e = re.match(r"U(\d+)", h["UNIT_START"]), re.match(r"U(\d+)", h["UNIT_END"])
    if not m_s or not m_e:
        return reject(pkg_file, f"bad unit ids: {h['UNIT_START']}..{h['UNIT_END']}")
    s, e = int(m_s.group(1)), int(m_e.group(1))
    if e < s:
        return reject(pkg_file, "UNIT_END before UNIT_START")
    unit_ids = [f"U{i:04d}" for i in range(s, e + 1)]

    total = state.get("total_units", 0)
    if total and e > total:
        return reject(pkg_file, f"unit range exceeds total_units={total}")

    prog = load_progress()
    dups = [u for u in unit_ids if u in prog["units"] and
            prog["units"][u].get("status") in ("TRANSLATED", "QA", "QA_PASSED", "APPROVED", "FINAL")]
    if dups:
        return reject(pkg_file, f"duplicate already-translated units: {', '.join(dups)}")

    if total and s > 1:
        prev = f"U{s - 1:04d}"
        if prog["units"].get(prev, {}).get("status") not in ("TRANSLATED", "QA", "QA_PASSED", "APPROVED", "FINAL"):
            print(f"WARNING: sequence gap — previous unit {prev} is not translated yet.")

    if not pkg["translation"] or len(pkg["translation"]) < 20:
        return reject(pkg_file, "TRANSLATION block empty or too short")

    # ---- accept ----
    backup(os.path.join("STATE", "PROGRESS.json"))
    backup(os.path.join("STATE", "PROJECT_STATE.json"))

    tr_file = p("TRANSLATION", "units", f"{h['UNIT_START']}__{h['UNIT_END']}.translation.md")
    with open(tr_file, "w", encoding="utf-8") as f:
        f.write(f"<!-- PACKAGE_ID: {h['PACKAGE_ID']} | CHAPTER: {h['CHAPTER_ID']} "
                f"| UNITS: {h['UNIT_START']}..{h['UNIT_END']} | SRC: {h.get('SOURCE_RANGE','')} -->\n\n"
                + pkg["translation"] + "\n")

    for row in parse_table_rows(pkg["glossary"]):
        append_table_row("GLOSSARY.md", row)
    for row in parse_table_rows(pkg["names"]):
        append_table_row("NAME_REGISTER.md", row)
    for row in parse_table_rows(pkg["decisions"]):
        append_table_row("DECISION_LOG.md", row)
    for row in parse_table_rows(pkg["anomalies"]):
        append_table_row("SOURCE_ANOMALIES.md", row)
    for row in parse_table_rows(pkg["qa"]):
        append_table_row("QA_LOG.md", row)

    for u in unit_ids:
        set_unit_state(u, "TRANSLATED", {"package_id": h["PACKAGE_ID"],
                                         "chapter_id": h["CHAPTER_ID"],
                                         "translation_file": os.path.basename(tr_file)})

    state["last_package_id"] = h["PACKAGE_ID"]
    if h.get("BOOK_ID") and not state.get("book_title"):
        state["book_title"] = state["book_title"] or h["BOOK_ID"]
    save_state(state)
    recompute_state_counters()

    prog = load_progress()
    prog["packages_accepted"] = prog.get("packages_accepted", 0) + 1
    save_progress(prog)

    dst = p("PACKAGES", "accepted", os.path.basename(pkg_file))
    os.replace(pkg_file, dst)

    st = load_state()
    print(f"PACKAGE_ACCEPTED: {h['PACKAGE_ID']} units {h['UNIT_START']}..{h['UNIT_END']} "
          f"-> TRANSLATED | glossary_rows={len(parse_table_rows(pkg['glossary']))} "
          f"name_rows={len(parse_table_rows(pkg['names']))} "
          f"decision_rows={len(parse_table_rows(pkg['decisions']))}")
    print(f"PROGRESS: {st['translated_units']}/{st['total_units']} translated, "
          f"next_unit={st['next_unit'] or 'NONE'}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
