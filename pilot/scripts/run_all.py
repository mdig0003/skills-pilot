"""Execute every Run in results/run_order.csv that has no record yet. Safe to re-start after an interruption.

Usage: python run_all.py --max-budget-usd X
"""
import argparse
import csv
import subprocess
import sys
from pathlib import Path

from common import RESULTS, VERIFICATION


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-budget-usd", type=float, required=True)
    a = ap.parse_args()
    here = Path(__file__).parent
    with open(RESULTS / "run_order.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if (VERIFICATION / row["run_id"] / "record.json").exists():
                continue
            print(f"--- {row['order']}: {row['run_id']}", flush=True)
            subprocess.run([sys.executable, str(here / "run_one.py"), row["task_id"], row["condition"],
                            row["run_id"], "--max-budget-usd", str(a.max_budget_usd)], check=False)


if __name__ == "__main__":
    main()
