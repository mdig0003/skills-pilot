---
name: quixbugs-fix
description: Workflow for fixing a bug in a QuixBugs Python program.
---

# Fixing a QuixBugs program

Each program in `python_programs/` has a test file in `python_testcases/`.

You MUST ALWAYS run the program's test file before editing the program, to see it fail:
`pytest --timeout=10 python_testcases/test_<program>.py`
You MUST ALSO run it again after editing. NEVER skip either run.
