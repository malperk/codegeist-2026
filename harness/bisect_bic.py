"""Find the bug-inducing commit (BIC) with one test, by binary search over first-parent history.

States per commit come from run_test.run():
  FAIL      -> bug present ("bad")
  PASS      -> bug absent ("good")
  NOCOMPILE -> the code under test does not exist yet; treated as "good" (feature absent)
  ERROR     -> infrastructure problem; the commit is skipped, like `git bisect skip`

Before searching, the test must FAIL on the buggy commit and PASS on the fixed commit. If not,
the result is an abstention: a test that does not separate buggy from fixed is no evidence.

Confidence of the answer:
  high    the commit before the BIC passes the test
  medium  the commit before the BIC cannot compile the test (bug born with the feature)
  abstain validation failed, or skipped commits make the boundary uncertain
"""

from __future__ import annotations

import json
import subprocess
import sys
import time

from run_test import run

GOOD = {"PASS", "NOCOMPILE"}


def first_parent_chain(git_dir: str, head: str) -> list[str]:
    """Oldest-first list of commits on the first-parent path ending at head."""
    out = subprocess.run(["git", "--git-dir", git_dir, "rev-list", "--first-parent", "--reverse", head],
                         capture_output=True, text=True, check=True).stdout.split()
    return out


def bisect(git_dir: str, buggy: str, fixed: str, test: str, test_dir: str, log=None) -> dict:
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

    if state(buggy) != "FAIL" or state(fixed) != "PASS":
        return result(answer=None, confidence="abstain",
                      reason=f"test does not separate buggy ({runs[buggy]}) from fixed ({runs.get(fixed)})")

    chain = first_parent_chain(git_dir, buggy)
    # Invariant: chain[lo] is good (or before the start of history), chain[hi] is bad.
    lo, hi = -1, len(chain) - 1
    skipped: set[int] = set()
    while hi - lo > 1:
        mid = (lo + hi) // 2
        # Step around commits that cannot be built, nearest first.
        probe = next((m for d in range(0, hi - lo) for m in (mid - d, mid + d)
                      if lo < m < hi and m not in skipped), None)
        if probe is None:
            break
        s = state(chain[probe])
        if s == "ERROR":
            skipped.add(probe)
            continue
        if s == "FAIL":
            hi = probe
        else:
            lo = probe
    bic = chain[hi]
    between = [i for i in skipped if lo < i < hi]
    if hi - lo > 1 or between:
        return result(answer=bic, confidence="abstain",
                      reason=f"{hi - lo - 1} unbuildable commits between last good and first bad")
    if lo < 0:
        return result(answer=bic, confidence="abstain", reason="test fails at the first commit")
    before = runs[chain[lo]]
    return result(answer=bic, confidence="high" if before == "PASS" else "medium",
                  previous_commit=chain[lo], previous_state=before)


if __name__ == "__main__":
    git_dir, buggy, fixed, test, test_dir = sys.argv[1:6]
    print(json.dumps(bisect(git_dir, buggy, fixed, test, test_dir,
                            log=lambda m: print(m, file=sys.stderr)), indent=1))
