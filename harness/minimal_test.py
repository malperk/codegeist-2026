"""Cut a JUnit test file down to one test method.

Keeps the package, imports, class declaration, fields, and every method that is not a test
(constructors, setUp/tearDown, helpers), plus the one target test. Drops every other test, so the class
can compile on older commits that lack APIs used by unrelated tests. Brace matching skips
string and char literals and comments. If extraction fails it raises ValueError.
"""

from __future__ import annotations

import re

KEEP = {"setUp", "tearDown", "suite", "main"}


def _skip_literal(src: str, i: int) -> int:
    q = src[i]
    i += 1
    while src[i] != q:
        i += 2 if src[i] == "\\" else 1
    return i + 1


def _match_brace(src: str, i: int) -> int:
    """Index just past the brace that closes the one at src[i]."""
    depth = 0
    while i < len(src):
        c = src[i]
        if src.startswith("//", i):
            i = src.index("\n", i)
            continue
        if src.startswith("/*", i):
            i = src.index("*/", i) + 2
            continue
        if c in "\"'":
            i = _skip_literal(src, i)
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError("unbalanced braces")


def members(body: str):
    """Yield (start, end, header) for each top-level member of a class body."""
    i, start = 0, 0
    while i < len(body):
        if body.startswith("//", i):
            i = body.index("\n", i)
            continue
        if body.startswith("/*", i):
            i = body.index("*/", i) + 2
            continue
        c = body[i]
        if c in "\"'":
            i = _skip_literal(body, i)
            continue
        if c == ";":
            yield start, i + 1, body[start:i + 1]
            i += 1
            start = i
            continue
        if c == "{":
            end = _match_brace(body, i)
            yield start, end, body[start:i]
            i = start = end
            continue
        i += 1


def minimal(src: str, method: str) -> str:
    cls_match = re.search(r"\bclass\s+\w+[^{]*\{", src)
    if not cls_match:
        raise ValueError("no class declaration")
    open_brace = cls_match.end() - 1
    close = _match_brace(src, open_brace)
    head, body = src[:open_brace + 1], src[open_brace + 1:close - 1]
    kept, found = [], False
    class_name = re.search(r"\bclass\s+(\w+)", cls_match.group(0)).group(1)
    for s, e, header in members(body):
        h = re.sub(r"/\*.*?\*/|//[^\n]*", "", header, flags=re.S)
        name = re.search(r"(\w+)\s*\(", h)
        is_method = name is not None and "=" not in h.split("(")[0]
        if not is_method:
            kept.append(body[s:e])  # field, initializer or inner class
            continue
        n = name.group(1)
        if n == method:
            found = True
        is_test = n.startswith("test") or re.search(r"@Test\b", h)
        if n == method or not is_test:
            kept.append(body[s:e])
    if not found:
        raise ValueError(f"method {method} not found")
    return head + "".join(kept) + "\n}\n"
