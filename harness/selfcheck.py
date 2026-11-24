"""Harness self-check on the dev cases, using the developers' own tests (Defects4J trigger tests).

For each dev case it checks four runs of the developer's test, taken from the fixed commit:
  buggy commit -> FAIL, fixed commit -> PASS, bug-inducing commit -> FAIL, its parent -> PASS.
This validates the runner and shows how far the ground truth can be reproduced by testing.
It does not involve the agent and is run on dev cases only.

Usage: python3 selfcheck.py > ../benchmark/results/selfcheck-dev.json
"""

import csv
import json
import subprocess
import sys
import tempfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from minimal_test import minimal
from run_test import read_test_source, run

ROOT = Path(__file__).resolve().parent.parent
GIT = str(ROOT / ".cache" / "commons-lang.git")
TRIGGER = "https://raw.githubusercontent.com/rjust/defects4j/master/framework/projects/Lang/trigger_tests/{}"


def trigger_tests(bug_id: str) -> list[str]:
    text = urllib.request.urlopen(TRIGGER.format(bug_id)).read().decode()
    return [l[4:].strip() for l in text.splitlines() if l.startswith("--- ")]


def parent(sha: str) -> str:
    return subprocess.run(["git", "--git-dir", GIT, "rev-parse", sha + "^"],
                          capture_output=True, text=True, check=True).stdout.strip()


def minimal_test_dir(fixed: str, test: str) -> str:
    """Write the developer's test, cut down to the one trigger method, into a temp dir."""
    cls, method = test.split("::")
    src = read_test_source(GIT, fixed, cls).decode("utf-8", "replace")
    d = tempfile.mkdtemp(prefix="mintest-")
    path = Path(d) / "src/test/java" / (cls.replace(".", "/") + ".java")
    path.parent.mkdir(parents=True)
    path.write_text(minimal(src, method))
    return d


def check(case: dict) -> dict:
    bug_id = case["case_id"].rsplit("-", 1)[1]
    test = trigger_tests(bug_id)[0]
    fixed = case["fixed_commit"]
    bic = case["bug_inducing_commit"]
    t = minimal_test_dir(fixed, test)
    runs = {
        "buggy": run(GIT, case["buggy_commit"], test, t),
        "fixed": run(GIT, fixed, test, t),
        "bic": run(GIT, bic, test, t),
        "bic_parent": run(GIT, parent(bic), test, t),
    }
    # At the BIC parent the code under test may not exist yet: NOCOMPILE is accepted there.
    expect = {"buggy": {"FAIL"}, "fixed": {"PASS"}, "bic": {"FAIL"}, "bic_parent": {"PASS", "NOCOMPILE"}}
    return {"case_id": case["case_id"], "jira": case["jira_issue"], "test": test,
            "results": {k: v["result"] for k, v in runs.items()},
            "as_expected": {k: runs[k]["result"] in expect[k] for k in expect},
            "errors": {k: v.get("log_tail", v.get("reason", ""))[-600:] for k, v in runs.items()
                       if v["result"] in ("ERROR", "NOCOMPILE")}}


def main() -> None:
    dev = {r["case_id"] for r in csv.DictReader(open(ROOT / "benchmark/split.csv")) if r["set"] == "dev"}
    cases = [c for c in csv.DictReader(open(ROOT / "benchmark/cases.csv")) if c["case_id"] in dev]
    with ThreadPoolExecutor(4) as pool:
        out = list(pool.map(check, cases))
    json.dump(out, sys.stdout, indent=1)


if __name__ == "__main__":
    main()
