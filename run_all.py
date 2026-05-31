"""
=============================================================
  VENDOR PERFORMANCE ANALYSIS — Master Runner
  Runs all phases in sequence: SQL → EDA → Stats → Dashboard
=============================================================
"""

import subprocess
import sys
from pathlib import Path

BASE_DIR  = Path(__file__).resolve().parent
NOTEBOOKS = BASE_DIR / "notebooks"

steps = [
    ("Phase 1 — SQL Setup & Data Loading",    NOTEBOOKS / "01_sql_setup.py"),
    ("Phase 2 — EDA & Visualizations",        NOTEBOOKS / "02_eda_analysis.py"),
    ("Phase 3 — Hypothesis Testing",          NOTEBOOKS / "03_hypothesis_testing.py"),
]

print("=" * 60)
print("  VENDOR PERFORMANCE ANALYSIS — MASTER RUNNER")
print("=" * 60)

for i, (label, script) in enumerate(steps, 1):
    print(f"\n\n{'═'*60}")
    print(f"  STEP {i}: {label}")
    print(f"{'═'*60}")
    result = subprocess.run([sys.executable, str(script)], check=True)
    if result.returncode != 0:
        print(f"\n❌ Step {i} failed. Stopping.")
        sys.exit(1)

print("\n\n" + "=" * 60)
print("  ALL ANALYSIS STEPS COMPLETE ✅")
print("=" * 60)
print("\n  Charts saved to: reports/")
print("\n  Starting interactive dashboard on http://127.0.0.1:8050 ...")
print("  Press Ctrl+C to stop.\n")

# Launch dashboard
subprocess.run([sys.executable, str(NOTEBOOKS / "04_dashboard.py")])
