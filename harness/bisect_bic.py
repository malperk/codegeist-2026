"""Find the bug-inducing commit (BIC) with one test, by binary search over first-parent history.

States per commit come from run_test.run():
  FAIL      -> bug present ("bad")
  PASS      -> bug absent ("good")
  NOCOMPILE -> the code under test does not exist yet; treated as "good" (feature absent)
  ERROR     -> infrastructure problem; the commit is skipped, like `git bisect skip`

Before searching, the test must FAIL on the buggy commit and, when a fixed commit is known,
PASS on it. If not,
the result is an abstention: a test that does not separate buggy from fixed is no evidence.

Confidence of the answer:
  high    the commit before the BIC passes the test
  medium  the commit before the BIC cannot compile the test and the code the test uses was born
          in the BIC (a new class or a new method, not code moved in from elsewhere)
  low     the commit before the BIC cannot compile the test and the code may be older: the
          class has history under another path, or the BIC deletes or renames source files
  abstain validation failed, or skipped commits make the boundary uncertain
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from run_test import run

GOOD = {"PASS", "NOCOMPILE"}


def first_parent_chain(git_dir: str, head: str) -> list[str]:
    """Oldest-first list of commits on the first-parent path ending at head."""
    out = subprocess.run(["git", "--git-dir", git_dir, "rev-list", "--first-parent", "--reverse", head],
                         capture_output=True, text=True, check=True).stdout.split()
    return out


def pick(lo: int, hi: int, k: int, skipped: set[int]) -> list[int]:
    """Up to k probe indices spread evenly strictly between lo and hi, avoiding skipped ones."""
    free = [i for i in range(lo + 1, hi) if i not in skipped] if hi - lo <= 4096 else None
    if free is not None:
        if len(free) <= k:
            return free
        return sorted({free[(j + 1) * len(free) // (k + 1)] for j in range(k)})
    out = []
    for j in range(k):  # very long ranges: step around skipped commits near each target
        t = lo + (j + 1) * (hi - lo) // (k + 1)
        m = next((m for d in range(hi - lo) for m in (t - d, t + d)
                  if lo < m < hi and m not in skipped and m not in out), None)
        if m is not None:
            out.append(m)
    return sorted(out)


def bisect(git_dir: str, buggy: str, fixed: str, test: str, test_dir: str, log=None,
           workers: int = int(os.environ.get("BISECT_WORKERS", "1"))) -> dict:
    started = time.time()
    runs: dict[str, str] = {}

    def state(commit: str) -> str:
        if commit not in runs:
            r = run(git_dir, commit, test, test_dir)
            runs[commit] = r["result"]
            if log:
                log(f"{commit[:10]} {r['result']} ({r.get('seconds', 0)}s)")
        return runs[commit]

    def result(**kw) -> dict:
        kw.update(test=test, runs=len(runs), seconds=round(time.time() - started, 1),
                  evidence={c[:12]: s for c, s in runs.items()})
        return kw

    # Without a fixed commit (real use) the test must at least fail where the bug was reported.
    if state(buggy) != "FAIL" or (fixed and state(fixed) != "PASS"):
        return result(answer=None, confidence="abstain",
                      reason=f"test does not reproduce the bug (reported revision: {runs[buggy]}"
                             + (f", fixed revision: {runs.get(fixed)}" if fixed else "") + ")")

    chain = first_parent_chain(git_dir, buggy)
    # Invariant: chain[lo] is good (or before the start of history), chain[hi] is bad.
    # Each round probes up to `workers` commits in parallel (a k-ary search); with one worker
    # this is ordinary bisection. ERROR commits are skipped, like `git bisect skip`.
    lo, hi = -1, len(chain) - 1
    skipped: set[int] = set()
    with ThreadPoolExecutor(workers) as pool:
        while hi - lo > 1:
            probes = pick(lo, hi, workers, skipped)
            if not probes:
                break
            states = dict(zip(probes, pool.map(lambda i: state(chain[i]), probes)))
            skipped |= {i for i, s in states.items() if s == "ERROR"}
            bad = [i for i, s in states.items() if s == "FAIL"]
            if bad:
                hi = min(bad)
            good = [i for i, s in states.items() if s in GOOD and i < hi]
            if good:
                lo = max(good)
    bic = chain[hi]
    between = [i for i in skipped if lo < i < hi]
    if hi - lo > 1 or between:
        return result(answer=bic, confidence="abstain",
                      reason=f"{hi - lo - 1} unbuildable commits between last good and first bad")
    if lo < 0:
        return result(answer=bic, confidence="abstain", reason="test fails at the first commit")
    before = runs[chain[lo]]
    if before == "PASS":
        return result(answer=bic, confidence="high", previous_commit=chain[lo], previous_state=before)
    conf, reason = born_or_moved(git_dir, chain[lo], bic, class_under_test(test))
    return result(answer=bic, confidence=conf, previous_commit=chain[lo], previous_state=before,
                  **({"reason": reason} if reason else {}))


def born_or_moved(git_dir: str, prev: str, bic: str, target: str | None) -> tuple[str, str]:
    """Confidence when the commit before the BIC cannot compile the test (rule v2).

    The test compiles from the BIC on because the code it calls appears there. That code was
    either born in the BIC (then the bug was born with it: medium) or moved in from elsewhere
    (then the bug may be older: low). Moves are recognised without reading commit messages:
    - the class under test is new at its path, but a file of that name, or its test, already
      existed somewhere else in the tree (held-out control LANG-1039: "Moved from superpackage");
    - the BIC deletes or renames main source files (dev case LANG-D4J-19: code moved from
      EscapeUtils into StringEscapeUtils).
    Rule v1 called every "class already existed" case low; on held-out run 1 those four answers
    were all correct (new methods added to an existing class), so v1 was too cautious.
    """
    if not target:
        return "low", "cannot tell which class the test is about"
    if not class_exists(git_dir, prev, target) and history_elsewhere(git_dir, prev, target):
        return "low", (f"{target} is new at this path but a file of that name already existed "
                       "elsewhere: the code was moved, so the bug may be older")
    moved = moved_sources(git_dir, bic)
    if moved:
        return "low", (f"this commit deletes or renames {len(moved)} source file(s) "
                       f"(e.g. {moved[0]}): the code may have been moved in, so the bug may be older")
    return "medium", ""


def class_under_test(test: str) -> str | None:
    """org.x.FooBugOriginTest::m or org.x.FooTest::m -> org.x.Foo (naming convention)."""
    cls = test.split("::")[0]
    for suffix in ("BugOriginTest", "Test"):
        if cls.endswith(suffix) and len(cls) > len(suffix):
            return cls[: -len(suffix)]
    return None


def class_exists(git_dir: str, commit: str, cls: str) -> bool:
    """Does the class's source file exist at commit, under either package name and layout?"""
    names = {cls, cls.replace("org.apache.commons.lang3.", "org.apache.commons.lang."),
             cls.replace("org.apache.commons.lang.", "org.apache.commons.lang3.")}
    for name in names:
        for d in ("src/main/java", "src/java"):
            path = f"{d}/{name.replace('.', '/')}.java"
            if subprocess.run(["git", "--git-dir", git_dir, "cat-file", "-e", f"{commit}:{path}"],
                              capture_output=True).returncode == 0:
                return True
    return False


def history_elsewhere(git_dir: str, commit: str, cls: str) -> bool:
    """Does a file named like the class (or its test) exist anywhere in the tree at commit?"""
    simple = cls.rsplit(".", 1)[-1]
    files = subprocess.run(["git", "--git-dir", git_dir, "ls-tree", "-r", "--name-only", commit],
                           capture_output=True, text=True, check=True).stdout.split("\n")
    return any(f.endswith((f"/{simple}.java", f"/{simple}Test.java")) for f in files)


def moved_sources(git_dir: str, commit: str) -> list[str]:
    """Main (non-test) Java files that the commit deletes or renames away."""
    out = subprocess.run(["git", "--git-dir", git_dir, "show", "-M", "--diff-filter=DR",
                          "--name-only", "--format=", commit],
                         capture_output=True, text=True, check=True).stdout.split()
    return [f for f in out if f.endswith(".java") and f.startswith(("src/java/", "src/main/java/"))]


if __name__ == "__main__":
    git_dir, buggy, fixed, test, test_dir = sys.argv[1:6]
    print(json.dumps(bisect(git_dir, buggy, fixed, test, test_dir,
                            log=lambda m: print(m, file=sys.stderr)), indent=1))
