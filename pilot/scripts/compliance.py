"""Objective Compliance check: reads a stream-json transcript and applies the README's rules."""
import json
import re
import sys
from pathlib import Path

EDIT_TOOLS = {"Edit", "Write", "MultiEdit"}
SHELL_TOOLS = {"Bash", "PowerShell"}
PYTEST_RE = re.compile(r"(?:^|[\s;&|(\"'])(?:py\.test|pytest|python3?(?:\.exe)?\s+-m\s+pytest)(?:\s|$|[;&|)\"'])")
TEST_FILE_RE = re.compile(r"test_\w+\.py")
K_RE = re.compile(r"-k\s+(?:\"([^\"]*)\"|'([^']*)'|(\S+))")
EXECUTED_RE = re.compile(r"collected \d+ item|\d+ (?:passed|failed|errors?|skipped)|no tests ran|Timeout", re.I)


def load_events(path):
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def tool_calls(events):
    """Ordered list of {idx, name, input, output, is_error} for every tool call."""
    calls, by_id = [], {}
    for ev in events:
        content = (ev.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if ev.get("type") == "assistant" and block.get("type") == "tool_use":
                call = {"idx": len(calls), "id": block["id"], "name": block["name"],
                        "input": block.get("input", {}), "output": "", "is_error": False}
                calls.append(call)
                by_id[block["id"]] = call
            elif ev.get("type") == "user" and block.get("type") == "tool_result":
                call = by_id.get(block.get("tool_use_id"))
                if call is None:
                    continue
                out = block.get("content", "")
                if isinstance(out, list):
                    out = "\n".join(b.get("text", "") for b in out if isinstance(b, dict))
                call["output"], call["is_error"] = str(out), bool(block.get("is_error"))
    return calls


def _norm(p):
    return str(p).replace("\\", "/")


def is_program_edit(call, program):
    return (call["name"] in EDIT_TOOLS and not call["is_error"]
            and _norm(call["input"].get("file_path", "")).endswith(f"python_programs/{program}.py"))


def is_counting_test_run(call, program):
    if call["name"] not in SHELL_TOOLS:
        return False
    cmd = call["input"].get("command", "")
    if not PYTEST_RE.search(cmd):
        return False
    files = TEST_FILE_RE.findall(cmd)
    if files and f"test_{program}.py" not in files:
        return False                      # targets other test files only
    k = K_RE.search(cmd)
    if k and not files and program not in next(g for g in k.groups() if g is not None):
        return False                      # whole-suite run filtered to other tests
    return bool(EXECUTED_RE.search(call["output"]))


def skill_loaded(calls, skill_name):
    for c in calls:
        if c["name"] == "Skill" and skill_name in json.dumps(c["input"]):
            return True
        if c["name"] == "Read" and _norm(c["input"].get("file_path", "")).endswith(f"skills/{skill_name}/SKILL.md"):
            return True
    return False

# checking if the order of the tool calls are correct here. 
def check(transcript, program, program_changed_in_diff, skill_name="quixbugs-fix"):
    calls = tool_calls(load_events(transcript))
    edits = [c["idx"] for c in calls if is_program_edit(c, program)]
    runs = [c for c in calls if is_counting_test_run(c, program)]
    res = {"skill_loaded": skill_loaded(calls, skill_name),
           "n_tool_calls": len(calls),
           "program_edit_idx": edits,
           "test_run_idx": [c["idx"] for c in runs],
           "test_run_commands": [c["input"]["command"] for c in runs],
           "flags": []}
    if not edits:
        if program_changed_in_diff:
            res.update(compliance="NEEDS_REVIEW", flags=["edit_not_via_edit_tool"])
        else:
            res.update(compliance="FAIL", flags=["no_edit"])
        return res
    pre = any(i < edits[0] for i in res["test_run_idx"])
    post = any(i > edits[-1] for i in res["test_run_idx"])
    res["pre_run"], res["post_run"] = pre, post
    res["flags"] = [f for f, ok in (("no_pre_run", pre), ("no_post_run", post)) if not ok]
    res["compliance"] = "PASS" if pre and post else "FAIL"
    return res


if __name__ == "__main__":
    print(json.dumps(check(sys.argv[1], sys.argv[2], sys.argv[3:4] == ["changed"]), indent=2))
