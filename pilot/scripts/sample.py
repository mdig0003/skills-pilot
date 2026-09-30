"""Draw the 20-Task sample and the shuffled order of all 120 Runs (20 Tasks x 2 Conditions x 3 repeats)."""
import csv
import random

from common import CONDITIONS, QUIXBUGS, RESULTS, SEED

N_TASKS, REPEATS = 20, 3


def main():
    rng = random.Random(SEED)
    programs = sorted(p.stem[5:] for p in (QUIXBUGS / "python_testcases").glob("test_*.py"))
    sample = sorted(rng.sample(programs, N_TASKS))
    runs = [(p, c, r) for p in sample for c in sorted(CONDITIONS) for r in range(1, REPEATS + 1)]
    rng.shuffle(runs)
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "task_sample.txt").write_text("\n".join(sample) + "\n", encoding="utf-8")
    with open(RESULTS / "run_order.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["order", "run_id", "task_id", "condition", "repeat"])
        for i, (p, c, r) in enumerate(runs, 1):
            w.writerow([i, f"{i:03d}_{p}_{c}_r{r}", p, c, r])
    print(f"seed={SEED}: {len(sample)} tasks, {len(runs)} runs -> {RESULTS}")


if __name__ == "__main__":
    main()
