#!/usr/bin/env python3
"""PROJECT ENGINE — core helpers (paths, state, backups, memory appends)."""
import json
import os
import shutil
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def p(*parts):
    return os.path.join(ROOT, *parts)

def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def load_state():
    return load_json(p("STATE", "PROJECT_STATE.json"))

def save_state(state):
    state["last_updated"] = now_iso()
    save_json(p("STATE", "PROJECT_STATE.json"), state)

def load_progress():
    return load_json(p("STATE", "PROGRESS.json"))

def save_progress(prog):
    prog["last_updated"] = now_iso()
    save_json(p("STATE", "PROGRESS.json"), prog)

def backup(file_rel):
    """Keep a timestamped copy of a file before overwriting it."""
    src = p(file_rel)
    if not os.path.exists(src):
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dst_dir = p("BACKUPS", os.path.dirname(file_rel))
    os.makedirs(dst_dir, exist_ok=True)
    base = os.path.basename(file_rel)
    dst = os.path.join(dst_dir, f"{base}.{stamp}.bak")
    shutil.copy2(src, dst)
    return dst

def set_unit_state(unit_id, status, extra=None):
    prog = load_progress()
    rec = prog["units"].setdefault(unit_id, {"status": "NOT_STARTED", "history": []})
    prev = rec["status"]
    rec["status"] = status
    rec["history"].append({"from": prev, "to": status, "at": now_iso()})
    if extra:
        rec.update(extra)
    save_progress(prog)

def get_unit_state(unit_id):
    prog = load_progress()
    return prog["units"].get(unit_id, {}).get("status", "NOT_STARTED")

def append_table_row(memory_file, row_cells):
    """Append a row to a Markdown pipe-table in a MEMORY file (creates table if header-only)."""
    path = p("MEMORY", memory_file)
    backup(os.path.join("MEMORY", memory_file))
    with open(path, encoding="utf-8") as f:
        content = f.read()
    line = "| " + " | ".join(str(c).replace("|", "\\|") for c in row_cells) + " |\n"
    if not content.endswith("\n"):
        content += "\n"
    content += line
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def next_decision_id():
    path = p("MEMORY", "DECISION_LOG.md")
    n = 0
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("| DEC-"):
                    try:
                        n = max(n, int(line.split("|")[1].strip().split("-")[1]))
                    except (ValueError, IndexError):
                        pass
    return f"DEC-{n + 1:04d}"

def recompute_state_counters():
    prog = load_progress()
    units = prog["units"]
    state = load_state()
    statuses = [u.get("status", "NOT_STARTED") for u in units.values()]
    state["total_units"] = len(units)
    state["translated_units"] = sum(1 for s in statuses if s in
        ("TRANSLATED", "QA", "QA_PASSED", "APPROVED", "FINAL"))
    state["qa_passed_units"] = sum(1 for s in statuses if s in ("QA_PASSED", "APPROVED", "FINAL"))
    state["approved_units"] = sum(1 for s in statuses if s in ("APPROVED", "FINAL"))
    state["final_units"] = sum(1 for s in statuses if s == "FINAL")
    finals = sorted(u for u, v in units.items() if v.get("status") == "FINAL")
    state["last_final_unit"] = finals[-1] if finals else ""
    if state["total_units"] and len(finals) < state["total_units"]:
        for i in range(1, state["total_units"] + 1):
            uid = f"U{i:04d}"
            if units.get(uid, {}).get("status") not in ("FINAL",):
                state["next_unit"] = uid
                break
    elif state["total_units"]:
        state["next_unit"] = ""
    save_state(state)
    return state
