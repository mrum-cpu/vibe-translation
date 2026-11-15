#!/usr/bin/env python3
"""PROJECT ENGINE — unit lifecycle transitions (Constitution §6).

Usage:
  python3 unit_state.py U0001 QA_PASSED
  python3 unit_state.py U0001 QA_FAILED --reason "فقرة مفقودة"
  python3 unit_state.py U0001 APPROVED
  python3 unit_state.py U0001 FINAL
  python3 unit_state.py --list
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) )
from engine_core import set_unit_state, get_unit_state, recompute_state_counters, load_progress

ALLOWED = {
    "NOT_STARTED": {"INGESTED"},
    "INGESTED": {"TRANSLATING", "TRANSLATED"},
    "TRANSLATING": {"TRANSLATED"},
    "TRANSLATED": {"QA", "QA_FAILED"},
    "QA": {"QA_PASSED", "QA_FAILED"},
    "QA_FAILED": {"REVISION", "QA"},
    "REVISION": {"QA", "TRANSLATED"},
    "QA_PASSED": {"APPROVED", "QA"},
    "APPROVED": {"FINAL", "REVISION"},
    "FINAL": set(),
}

def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if args[0] == "--list":
        prog = load_progress()
        for uid in sorted(prog["units"]):
            print(f"{uid}: {prog['units'][uid].get('status')}")
        return 0

    uid, status = args[0], args[1]
    reason = args[3] if len(args) > 3 and args[2] == "--reason" else ""
    cur = get_unit_state(uid)
    allowed = ALLOWED.get(cur, set())
    if status not in allowed:
        print(f"TRANSITION REJECTED: {uid} is {cur}; '{status}' not allowed "
              f"(allowed: {', '.join(sorted(allowed)) or 'none — FINAL is terminal'})")
        return 1
    set_unit_state(uid, status, {"reason": reason} if reason else None)
    st = recompute_state_counters()
    print(f"{uid}: {cur} -> {status} | translated={st['translated_units']}/{st['total_units']} "
          f"final={st['final_units']} next={st['next_unit'] or 'NONE'}")
    return 0

if __name__ == "__main__":
    import os
    sys.exit(main())
