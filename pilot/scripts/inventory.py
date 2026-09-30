"""Build the dataset inventory (dataset/inventory.csv + .md) and gold lines (verification/gold_lines.json).

Runs every Task's tests against the buggy and the correct program, so every row is backed by evidence.
"""
import csv
import difflib
import json
import subprocess
import sys

from common import PILOT, QUIXBUGS, TEST_TIMEOUT_S, VERIFICATION
from gold import code_lines, gold_lines


def pytest_summary(program, correct):
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--color=no", f"--timeout={TEST_TIMEOUT_S}",
           f"python_testcases/test_{program}.py"] + (["--correct"] if correct else [])
    p = subprocess.run(cmd, cwd=QUIXBUGS, capture_output=True, text=True, timeout=600)
    lines = [l for l in (p.stdout + p.stderr).splitlines() if l.strip()]
    last = lines[-1].strip("= ") if lines else ""
    return ("TIMEOUT (hang)" if "Timeout" in last else last), p.returncode


def fix_text(program):
    """The correct program's replacement for the gold line(s), for the inventory's Expected Behaviour column."""
    b = code_lines((QUIXBUGS / "python_programs" / f"{program}.py").read_text(encoding="utf-8"))
    c_src = (QUIXBUGS / "correct_python_programs" / f"{program}.py").read_text(encoding="utf-8").splitlines()
    c = code_lines("\n".join(c_src))
    sm = difflib.SequenceMatcher(a=[x for _, x in b], b=[x for _, x in c], autojunk=False)
    return " / ".join(c_src[c[j][0] - 1].strip() for op, _, _, j1, j2 in sm.get_opcodes() if op != "equal"
                      for j in range(j1, j2))


def main():
    programs = sorted(p.stem[5:] for p in (QUIXBUGS / "python_testcases").glob("test_*.py"))
    rows, gold = [], {}
    for prog in programs:
        g = gold_lines(QUIXBUGS, prog)
        gold[prog] = g
        src = (QUIXBUGS / "python_programs" / f"{prog}.py").read_text(encoding="utf-8").splitlines()
        files = [f"python_programs/{prog}.py", f"python_testcases/test_{prog}.py"]
        if (QUIXBUGS / "json_testcases" / f"{prog}.json").exists():
            files.append(f"json_testcases/{prog}.json")
        buggy, brc = pytest_summary(prog, False)
        correct, crc = pytest_summary(prog, True)
        rows.append({
            "task_id": prog, "files": "; ".join(files), "language": "Python 3",
            "seeded_issue": "; ".join(f"L{n}: {src[n - 1].strip()}" for n in g),
            "expected_behaviour": f"Fix so tests pass (reference fix: {fix_text(prog)})",
            "verification_method": "Compliance: transcript order of pytest runs vs program edits. "
                                   "Fix: pytest on test file. Localisation: diff vs gold line.",
            "tests_on_buggy": buggy, "tests_on_correct": correct,
            "objectively_evaluable": "yes" if brc != 0 and crc == 0 else "NO",
        })
    VERIFICATION.mkdir(exist_ok=True)
    (VERIFICATION / "gold_lines.json").write_text(json.dumps(gold, indent=2), encoding="utf-8")
    with open(PILOT / "dataset" / "inventory.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    md = ["| Task ID | Files | Language | Seeded Issue | Expected Behaviour | Verification Method | Buggy tests | Correct tests | Evaluable |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append("| " + " | ".join(str(v).replace("|", "\\|") for v in r.values()) + " |")
    (PILOT / "dataset" / "inventory.md").write_text("# Dataset inventory (QuixBugs Python)\n\n" + "\n".join(md) + "\n",
                                                   encoding="utf-8")
    print(f"{len(rows)} tasks, {sum(r['objectively_evaluable'] == 'yes' for r in rows)} objectively evaluable")


if __name__ == "__main__":
    main()
