"""Gold buggy lines: code lines of the buggy program that differ from the correct program.

Docstrings, comments, blank lines and whitespace are ignored, because the correct
versions in QuixBugs drop the buggy versions' docstrings.
"""
import ast
import difflib
import io
import tokenize
from pathlib import Path


def code_lines(src):
    """Return [(lineno, normalised_code)] for lines holding real code."""
    skip = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Expr) and isinstance(getattr(node, "value", None), ast.Constant) \
                and isinstance(node.value.value, str):
            skip.update(range(node.lineno, node.end_lineno + 1))
    lines = src.splitlines()
    # strip comments via tokenize
    kept = {i + 1: l for i, l in enumerate(lines)}
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.COMMENT:
            r, c = tok.start
            kept[r] = kept[r][:c]
    out = []
    for n in sorted(kept):
        if n in skip:
            continue
        norm = "".join(kept[n].split())
        if norm:
            out.append((n, norm))
    return out


def changed_lines(before_src, after_src):
    """Line numbers in before_src whose code was modified or deleted in after_src.

    A pure insertion is attributed to the preceding before-line (or line 1)."""
    a, b = code_lines(before_src), code_lines(after_src)
    sm = difflib.SequenceMatcher(a=[x for _, x in a], b=[x for _, x in b], autojunk=False)
    out = set()
    for op, i1, i2, _, _ in sm.get_opcodes():
        if op in ("replace", "delete"):
            out.update(a[i][0] for i in range(i1, i2))
        elif op == "insert":
            out.add(a[i1 - 1][0] if i1 > 0 else (a[0][0] if a else 1))
    return sorted(out)


def gold_lines(quixbugs_dir, program):
    q = Path(quixbugs_dir)
    return changed_lines((q / "python_programs" / f"{program}.py").read_text(encoding="utf-8"),
                         (q / "correct_python_programs" / f"{program}.py").read_text(encoding="utf-8"))
