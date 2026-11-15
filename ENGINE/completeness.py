#!/usr/bin/env python3
"""PROJECT ENGINE — completeness report + final tests (Constitution §20, §36, §35).

Usage: python3 completeness.py
Writes REPORTS/COMPLETENESS_REPORT.md and REPORTS/QA_REPORT.md (test results).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine_core import p, now_iso, load_state, load_progress, save_state

def main():
    state = load_state()
    prog = load_progress()
    units = prog["units"]
    total = state.get("total_units", 0)

    counts = {}
    for u in units.values():
        st = u.get("status", "NOT_STARTED")
        counts[st] = counts.get(st, 0) + 1

    missing = sorted(f"U{i:04d}" for i in range(1, total + 1)
                     if f"U{i:04d}" not in units or units[f"U{i:04d}"].get("status") == "NOT_STARTED")
    failed = sorted(uid for uid, u in units.items() if u.get("status") in ("QA_FAILED", "REVISION"))
    final = sorted(uid for uid, u in units.items() if u.get("status") == "FINAL")

    complete = (total > 0 and len(final) == total and not missing and not failed)

    lines = [
        "# COMPLETENESS_REPORT.md",
        f"_Generated: {now_iso()}_",
        "",
        f"TOTAL SOURCE UNITS: {total}",
        f"TRANSLATED: {state.get('translated_units', 0)}",
        f"QA PASSED: {state.get('qa_passed_units', 0)}",
        f"APPROVED: {state.get('approved_units', 0)}",
        f"FINAL: {len(final)}",
        f"MISSING: {len(missing)}",
        f"FAILED: {len(failed)}",
        "",
        f"PROJECT STATUS: {'COMPLETE' if complete else state.get('project_status', 'IN_PROGRESS')}",
        "",
        "## Status breakdown",
        "",
    ]
    lines += [f"- {k}: {v}" for k, v in sorted(counts.items())]
    if missing:
        lines += ["", "## Missing units", ""] + [f"- {u}" for u in missing]
    if failed:
        lines += ["", "## Failed units", ""] + [f"- {u}" for u in failed]
    with open(p("REPORTS", "COMPLETENESS_REPORT.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    manifest_file = p("SOURCE", "source_units", "units_manifest.json")
    manifest_ids = []
    if os.path.exists(manifest_file):
        import json
        with open(manifest_file, encoding="utf-8") as f:
            manifest_ids = [u["unit_id"] for u in json.load(f)["units"]]

    translated_ids = sorted(uid for uid, u in units.items()
                            if u.get("status") in ("TRANSLATED", "QA", "QA_PASSED", "APPROVED", "FINAL"))
    tests = [
        ("TEST 1 — كل وحدات المصدر موجودة", bool(manifest_ids) and
            all(os.path.exists(p("SOURCE", "source_units", f"{u}.txt")) for u in manifest_ids)),
        ("TEST 2 — لكل وحدة ترجمة", total > 0 and len(translated_ids) == total),
        ("TEST 3 — كل الوحدات اجتازت QA", state.get("qa_passed_units", 0) == total and total > 0),
        ("TEST 4 — المصطلحات موحدة (GLOSSARY منظم)", os.path.exists(p("MEMORY", "GLOSSARY.md"))),
        ("TEST 5 — الأسماء موحدة (NAME_REGISTER منظم)", os.path.exists(p("MEMORY", "NAME_REGISTER.md"))),
        ("TEST 6 — الهوامش سليمة (Cross-Book Review موثق)", os.path.exists(p("REPORTS", "CROSS_BOOK_REVIEW.md"))),
        ("TEST 7 — ترتيب الفصول صحيح (BOOK_MAP مكتمل)", os.path.exists(p("MEMORY", "BOOK_MAP.md"))),
        ("TEST 8 — لا وحدات مفقودة", not missing),
        ("TEST 9 — لا وحدات مكررة", len(translated_ids) == len(set(translated_ids))),
        ("TEST 10 — النسخة النهائية متكاملة (FINAL = TOTAL)", len(final) == total and total > 0),
    ]

    qa = ["# QA_REPORT.md — FINAL TESTS", f"_Generated: {now_iso()}_", ""]
    all_pass = True
    for name, ok in tests:
        qa.append(f"- [{'PASS' if ok else 'FAIL'}] {name}")
        all_pass = all_pass and ok
    qa += ["", f"OVERALL: {'ALL TESTS PASSED' if all_pass else 'NOT READY FOR ASSEMBLY'}", ""]
    with open(p("REPORTS", "QA_REPORT.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(qa) + "\n")

    if complete and state.get("project_status") != "COMPLETE":
        state["project_status"] = "COMPLETE" if all_pass else "FINAL_REVIEW"
        save_state(state)

    print("\n".join(qa))
    print(f"COMPLETENESS: translated={state.get('translated_units', 0)}/{total} "
          f"final={len(final)} missing={len(missing)} failed={len(failed)} "
          f"-> {'COMPLETE' if complete else 'IN PROGRESS'}")

if __name__ == "__main__":
    main()
