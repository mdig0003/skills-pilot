"""Execute one Run: fresh workspace -> task turn -> verification -> explanation turn -> record.

Usage: python run_one.py <program> <L2|L5> <run_id> [--max-budget-usd X]
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

import compliance
from common import (AGENT_FLAGS, AGENT_TIMEOUT_S, CONDITIONS, EXPLANATION_PROMPT, EXPLANATIONS, MODEL,
                    QUIXBUGS, QUIXBUGS_COMMIT, RUNS, SKILL_NAME, TASK_PROMPT, TEST_TIMEOUT_S, VERIFICATION,
                    WORKSPACE_ITEMS, WORKSPACE_ROOT, agent_env)
from gold import changed_lines, gold_lines

IGNORED_PARTS = {"__pycache__", ".pytest_cache", ".git"}


def git(ws, *args):
    return subprocess.run(["git", "-C", str(ws), *args], capture_output=True, text=True, check=True).stdout


def make_workspace(ws, condition):
    if ws.exists():
        raise SystemExit(f"workspace already exists: {ws}")
    ws.mkdir(parents=True)
    for item in WORKSPACE_ITEMS:
        src = QUIXBUGS / item
        (shutil.copytree if src.is_dir() else shutil.copy2)(src, ws / item)
    skill_dir = ws / ".claude" / "skills" / SKILL_NAME
    skill_dir.mkdir(parents=True)
    shutil.copy2(CONDITIONS[condition], skill_dir / "SKILL.md")
    git(ws, "init", "-q")
    git(ws, "-c", "user.name=pilot", "-c", "user.email=pilot@localhost", "add", "-A")
    git(ws, "-c", "user.name=pilot", "-c", "user.email=pilot@localhost", "commit", "-qm", "initial state")
    return git(ws, "rev-parse", "HEAD").strip()


def run_agent(ws, prompt, out_path, session_flags, budget):
    claude = shutil.which("claude") or "claude"
    cmd = [claude, "-p", prompt, *AGENT_FLAGS, *session_flags]
    if budget:
        cmd += ["--max-budget-usd", str(budget)]
    with open(out_path, "w", encoding="utf-8") as out, open(out_path.with_suffix(".stderr.txt"), "w") as err:
        try:
            rc = subprocess.run(cmd, cwd=ws, env=agent_env(), stdin=subprocess.DEVNULL, stdout=out, stderr=err, timeout=AGENT_TIMEOUT_S).returncode
        except subprocess.TimeoutExpired:
            rc = "timeout"
    events = compliance.load_events(out_path)
    result = next((e for e in reversed(events) if e.get("type") == "result"), {})
    init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), {})
    return {"returncode": rc, "result": result, "init": init, "events": events}


def changed_files(ws):
    out = git(ws, "status", "--porcelain", "--untracked-files=all")
    files = [l[3:].strip() for l in out.splitlines()]
    return [f for f in files if not IGNORED_PARTS & set(Path(f).parts)]


def verify_fix(ws, program, vdir):
    """Run the Task's tests on a copy of the workspace, so the agent never sees verification artefacts."""
    with tempfile.TemporaryDirectory() as tmp:
        for item in ("python_programs", "python_testcases", "json_testcases", "conftest.py"):
            src = ws / item
            (shutil.copytree if src.is_dir() else shutil.copy2)(src, Path(tmp) / item)
        cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--color=no", f"--timeout={TEST_TIMEOUT_S}",
               f"python_testcases/test_{program}.py"]
        p = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True)
    (vdir / "pytest_after.txt").write_text(" ".join(cmd) + "\n\n" + p.stdout + p.stderr, encoding="utf-8")
    return p.returncode == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("program")
    ap.add_argument("condition", choices=sorted(CONDITIONS))
    ap.add_argument("run_id")
    ap.add_argument("--max-budget-usd", type=float)
    a = ap.parse_args()

    ws = WORKSPACE_ROOT / a.run_id
    vdir = VERIFICATION / a.run_id
    for d in (RUNS, vdir, EXPLANATIONS):
        d.mkdir(parents=True, exist_ok=True)
    skill_text = CONDITIONS[a.condition].read_text(encoding="utf-8")
    session = str(uuid.uuid4())
    started = datetime.now(timezone.utc).isoformat()

    initial_state = make_workspace(ws, a.condition)
    prompt = TASK_PROMPT.format(program=a.program)
    task = run_agent(ws, prompt, RUNS / f"{a.run_id}.jsonl", ["--session-id", session], a.max_budget_usd)

    # Objective verification (before the explanation turn, and never shown to the agent)
    diff = git(ws, "diff", "-w", initial_state)
    (vdir / "diff.patch").write_text(diff, encoding="utf-8")
    files = changed_files(ws)
    prog_rel = f"python_programs/{a.program}.py"
    original = (QUIXBUGS / prog_rel).read_text(encoding="utf-8")
    final = (ws / prog_rel).read_text(encoding="utf-8") if (ws / prog_rel).exists() else ""
    try:
        agent_lines = changed_lines(original, final)
    except SyntaxError:
        agent_lines = None                                   # agent left the program unparseable
    gold = gold_lines(QUIXBUGS, a.program)
    comp = compliance.check(RUNS / f"{a.run_id}.jsonl", a.program, prog_rel in files)
    fix_success = verify_fix(ws, a.program, vdir)
    loc = None
    if agent_lines is not None:
        tp = len(set(gold) & set(agent_lines))
        loc = {"gold": gold, "changed": agent_lines, "tp": tp, "fp": len(set(agent_lines) - set(gold)),
               "fn": len(set(gold) - set(agent_lines)), "alt_fix": fix_success and tp == 0}

    # Explanation turn: same session, same flags, fixed prompt
    expl = run_agent(ws, EXPLANATION_PROMPT, RUNS / f"{a.run_id}.explain.jsonl", ["--resume", session],
                     a.max_budget_usd)
    explanation = expl["result"].get("result", "")
    (EXPLANATIONS / f"{a.run_id}.md").write_text(explanation, encoding="utf-8")
    expl_tools = [c["name"] for c in compliance.tool_calls(expl["events"])]

    record = {
        "run_id": a.run_id, "task_id": a.program, "condition": a.condition,
        "agent_model_requested": MODEL, "agent_model_reported": task["init"].get("model"),
        "claude_code_version": task["init"].get("claude_code_version"),
        "timestamp": started, "session_id": session,
        "skill_text": skill_text, "skill_sha256": hashlib.sha256(skill_text.encode()).hexdigest(),
        "skills_visible_to_agent": task["init"].get("skills"),
        "tools_visible_to_agent": task["init"].get("tools"),
        "dataset": f"QuixBugs@{QUIXBUGS_COMMIT}", "workspace": str(ws), "initial_state": initial_state,
        "agent_task": prompt, "explanation_prompt": EXPLANATION_PROMPT,
        "task_returncode": task["returncode"], "task_subtype": task["result"].get("subtype"),
        "task_cost_usd": task["result"].get("total_cost_usd"),
        "explain_cost_usd": expl["result"].get("total_cost_usd"),
        "task_num_turns": task["result"].get("num_turns"),
        "files_changed": files, "fix_success": fix_success,
        "objective_compliance": comp["compliance"], "compliance_flags": comp["flags"],
        "skill_loaded": comp["skill_loaded"],
        "verification_evidence": {"program_edit_idx": comp["program_edit_idx"],
                                  "test_run_idx": comp["test_run_idx"],
                                  "test_run_commands": comp["test_run_commands"],
                                  "n_tool_calls": comp["n_tool_calls"]},
        "localisation": loc,
        "explanation_turn_tool_calls": expl_tools,
        "agent_explanation": explanation,
    }
    (vdir / "record.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(json.dumps({k: record[k] for k in ("run_id", "objective_compliance", "compliance_flags", "skill_loaded",
                                             "fix_success", "files_changed", "task_cost_usd")}, indent=2))


if __name__ == "__main__":
    main()
