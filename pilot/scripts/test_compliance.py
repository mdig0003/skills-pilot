"""Tests for the Compliance checker and the gold/changed-line logic. Run: python -m pytest pilot/scripts"""
import json

import pytest

from compliance import check
from gold import changed_lines

PYTEST_OUT = "============ 5 failed, 1 passed in 0.15s ============"
COLLECTED = "collected 6 items"


def transcript(tmp_path, *calls):
    """calls: (name, input, output[, is_error]) tuples, emitted as stream-json events in order."""
    lines = []
    for i, (name, inp, out, *err) in enumerate(calls):
        lines.append({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": f"t{i}", "name": name, "input": inp}]}})
        lines.append({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": f"t{i}", "content": out, "is_error": bool(err and err[0])}]}})
    p = tmp_path / "t.jsonl"
    p.write_text("\n".join(json.dumps(l) for l in lines), encoding="utf-8")
    return p


def bash(cmd, out=PYTEST_OUT):
    return ("Bash", {"command": cmd}, out)


EDIT = ("Edit", {"file_path": "C:\\tmp\\ws\\python_programs\\gcd.py", "old_string": "a", "new_string": "b"}, "ok")


def test_pass_before_and_after(tmp_path):
    r = check(transcript(tmp_path, bash("pytest python_testcases/test_gcd.py"), EDIT,
                         bash("python -m pytest --timeout=10 python_testcases/test_gcd.py")), "gcd", True)
    assert r["compliance"] == "PASS" and r["flags"] == []


def test_only_after_is_fail(tmp_path):
    r = check(transcript(tmp_path, EDIT, bash("pytest python_testcases/test_gcd.py")), "gcd", True)
    assert r["compliance"] == "FAIL" and r["flags"] == ["no_pre_run"]


def test_only_before_is_fail(tmp_path):
    r = check(transcript(tmp_path, bash("pytest python_testcases/test_gcd.py"), EDIT), "gcd", True)
    assert r["flags"] == ["no_post_run"]


def test_directory_run_counts(tmp_path):
    r = check(transcript(tmp_path, bash("pytest python_testcases/"), EDIT, bash("pytest")), "gcd", True)
    assert r["compliance"] == "PASS"


def test_other_test_file_does_not_count(tmp_path):
    r = check(transcript(tmp_path, bash("pytest python_testcases/test_sqrt.py"), EDIT,
                         bash("pytest python_testcases/test_gcd.py")), "gcd", True)
    assert r["flags"] == ["no_pre_run"]


def test_k_filter_to_other_program_does_not_count(tmp_path):
    r = check(transcript(tmp_path, bash("pytest python_testcases -k sqrt"), EDIT,
                         bash("pytest python_testcases -k gcd")), "gcd", True)
    assert r["flags"] == ["no_pre_run"]


def test_pytest_that_never_ran_does_not_count(tmp_path):
    r = check(transcript(tmp_path, bash("pytest python_testcases/test_gcd.py", "bash: pytest: command not found"),
                         EDIT, bash("pytest python_testcases/test_gcd.py")), "gcd", True)
    assert r["flags"] == ["no_pre_run"]


def test_timeout_output_counts(tmp_path):
    out = "+++++++ Timeout +++++++"
    r = check(transcript(tmp_path, bash("pytest python_testcases/test_gcd.py", out), EDIT,
                         bash("pytest python_testcases/test_gcd.py")), "gcd", True)
    assert r["compliance"] == "PASS"


def test_adhoc_python_does_not_count(tmp_path):
    r = check(transcript(tmp_path, bash('python -c "from python_programs.gcd import gcd; print(gcd(4,2))"', "2"),
                         EDIT, bash("pytest python_testcases/test_gcd.py")), "gcd", True)
    assert r["flags"] == ["no_pre_run"]


def test_powershell_run_counts(tmp_path):
    ps = ("PowerShell", {"command": "python -m pytest python_testcases\\test_gcd.py"}, COLLECTED)
    r = check(transcript(tmp_path, ps, EDIT, ps), "gcd", True)
    assert r["compliance"] == "PASS"


def test_failed_edit_is_not_an_edit(tmp_path):
    bad = EDIT[:3] + (True,)
    r = check(transcript(tmp_path, bad, bash("pytest python_testcases/test_gcd.py"), EDIT,
                         bash("pytest python_testcases/test_gcd.py")), "gcd", True)
    assert r["compliance"] == "PASS"


def test_no_edit(tmp_path):
    r = check(transcript(tmp_path, bash("pytest python_testcases/test_gcd.py")), "gcd", False)
    assert r["compliance"] == "FAIL" and r["flags"] == ["no_edit"]


def test_edit_via_sed_needs_review(tmp_path):
    r = check(transcript(tmp_path, bash("sed -i 's/a % b, b/b, a % b/' python_programs/gcd.py", "")), "gcd", True)
    assert r["compliance"] == "NEEDS_REVIEW"


def test_skill_loaded(tmp_path):
    r = check(transcript(tmp_path, ("Skill", {"skill": "quixbugs-fix"}, "loaded"), EDIT), "gcd", True)
    assert r["skill_loaded"] is True


def test_changed_lines_ignores_docstrings_and_whitespace():
    before = 'def f(a, b):\n    return a  -  b\n\n"""doc"""\n'
    after = 'def f(a, b):\n    return a+b\n'
    assert changed_lines(before, after) == [2]
    assert changed_lines(before, 'def f(a, b):\n    return a - b\n') == []
