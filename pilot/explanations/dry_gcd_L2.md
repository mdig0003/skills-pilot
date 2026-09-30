**What I changed**

One line in `python_programs/gcd.py:5`:

```diff
-        return gcd(a % b, b)
+        return gcd(b, a % b)
```

Nothing else changed. I didn't touch the test file and didn't commit, since you didn't ask for a commit.

**Requirements I followed**

1. **Your request:** fix the bug in `gcd.py`. I made the smallest fix that restores the standard Euclidean algorithm.
2. **The `quixbugs-fix` skill:** I loaded it before starting because it covers this exact task. It says:
   - "You **may** run the program's test file before editing the program, to see it fail."
   - "You **may** also run it again after editing, to see it pass."

**Did I follow the skill's rule?**

Yes, in the sense that I broke nothing: both steps are optional ("may"), not required. But I only partly did what it describes:

- **Before editing:** I tried to run the tests, but the command failed because `pytest` isn't on the PATH. I didn't retry with `python -m pytest` before editing. I went ahead because the non-terminating recursion was clear from reading the code. So I never actually saw the tests fail, which I said in my earlier summary.
- **After editing:** I ran `python -m pytest --timeout=10 python_testcases/test_gcd.py`, and all 6 tests passed.

If you'd like the before-fix failure confirmed, I can temporarily undo the fix with `git stash`, run the tests with `python -m pytest`, and then restore it.