# QuixBugs (Python) as the pilot dataset

The pilot uses the 40 Python programs from QuixBugs (pinned commit, vendored into `pilot/dataset/`) instead of `data/code_bug_fix_pairs.csv`. The CSV collapses to 10 unique templates of one-token syntax errors (111 of its 1000 rows contain no bug at all), its commit messages are randomly assigned, and it has no tests. There is therefore no rule an agent could plausibly skip whose compliance can be checked. QuixBugs provides one-line bugs with known locations, corrected versions and pytest suites, which gives an objective fix check and a natural test-running rule.

## Consequences

- QuixBugs is well known and almost certainly in the model's training data, so fix success is expected to be near ceiling. Fix success is a manipulation check, not the dependent variable.
- `data/code_bug_fix_pairs.csv` is kept unchanged but is not used by the pilot.
