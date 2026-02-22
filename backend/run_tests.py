"""
Standalone test runner — no server needed.

Usage (run from backend/ directory):
  python run_tests.py                          # run ALL scenarios
  python run_tests.py full_booking_blood_test  # run one scenario by name
  python run_tests.py --cleanup                # run all + delete test reservations
"""

import os
import sys

# ── Make sure we always run from backend/ so relative file paths work ──
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.tests.scenarios import SCENARIOS
from app.tests.runner import run_all_scenarios


if __name__ == "__main__":
    args = sys.argv[1:]

    cleanup = "--cleanup" in args
    filter_names = [a for a in args if not a.startswith("--")]

    scenarios_to_run = (
        [s for s in SCENARIOS if s.name in filter_names]
        if filter_names
        else SCENARIOS
    )

    if not scenarios_to_run:
        print(f"\n  No scenarios found matching: {filter_names}")
        print(f"  Available: {[s.name for s in SCENARIOS]}\n")
        sys.exit(1)

    results = run_all_scenarios(scenarios_to_run, cleanup_after=cleanup)

    # Non-zero exit code if any scenario crashed (useful for CI pipelines)
    failed = sum(1 for r in results if r.get("error"))
    sys.exit(failed)
