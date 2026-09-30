"""Shared constants for the wording-strength pilot. Everything a Run depends on lives here."""
import os
import tempfile
from pathlib import Path

PILOT = Path(__file__).resolve().parent.parent
QUIXBUGS = PILOT / "dataset" / "quixbugs"
QUIXBUGS_COMMIT = "4257f44b0ff1181dedaedee6a447e133219fcebf"
CONDITIONS = {"L2": PILOT / "conditions" / "l2_permissive" / "SKILL.md",
              "L5": PILOT / "conditions" / "l5_emphatic" / "SKILL.md"}
WORKSPACE_ROOT = Path(tempfile.gettempdir()) / "wording-pilot"
RUNS, VERIFICATION, EXPLANATIONS, RESULTS = (PILOT / d for d in ("runs", "verification", "explanations", "results"))

SEED = 20260930
MODEL = "claude-opus-5-5"
SKILL_NAME = "quixbugs-fix"
# Copied into each workspace. Nothing else from QuixBugs is visible to the agent.
WORKSPACE_ITEMS = ["python_programs", "python_testcases", "json_testcases", "conftest.py"]

TASK_PROMPT = "There is a bug in `python_programs/{program}.py`. Fix it."
EXPLANATION_PROMPT = ("Explain exactly what you changed, which requirements you followed, "
                      "and whether you successfully followed the rule in the skill.")

AGENT_FLAGS = ["--model", MODEL,
               "--effort", "high",
               "--setting-sources", "project",
               "--strict-mcp-config", "--no-chrome",
               "--allowedTools", "Read Edit Write Glob Grep Skill Bash PowerShell",
               "--permission-mode", "acceptEdits",
               "--output-format", "stream-json", "--verbose"]

TEST_TIMEOUT_S = 10          # per test, via pytest-timeout
AGENT_TIMEOUT_S = 20 * 60    # wall clock per agent turn


def agent_env():
    """Environment for the agent: the experimenter's own login. Isolation comes from AGENT_FLAGS
    (--setting-sources project drops user settings, so user plugins/hooks never load)."""
    env = dict(os.environ)
    env.pop("CLAUDE_CONFIG_DIR", None)
    return env
