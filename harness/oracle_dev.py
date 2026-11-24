"""Upper bound of the method on the dev cases: bisect with the developer's own test.

The agent will write its own test; this run shows how often bisection finds the published BIC
when the test is as good as the developer's. Dev cases only.

Usage: python3 oracle_dev.py > ../benchmark/results/oracle-dev.json
"""

import csv
import json
import sys
from concurrent.futures import ThreadPoolExecutor

from bisect_bic import bisect
from selfcheck import GIT, ROOT, minimal_test_dir, trigger_tests


def one(case: dict) -> dict:
    test = trigger_tests(case["case_id"].rsplit("-", 1)[1])[0]
    r = bisect(GIT, case["buggy_commit"], case["fixed_commit"], test,
               minimal_test_dir(case["fixed_commit"], test))
    r.update(case_id=case["case_id"], jira=case["jira_issue"], expected=case["bug_inducing_commit"],
             exact_match=r["answer"] == case["bug_inducing_commit"])
    return r


def main() -> None:
    dev = {r["case_id"] for r in csv.DictReader(open(ROOT / "benchmark/split.csv")) if r["set"] == "dev"}
    cases = [c for c in csv.DictReader(open(ROOT / "benchmark/cases.csv")) if c["case_id"] in dev]
    with ThreadPoolExecutor(3) as pool:
        out = list(pool.map(one, cases))
    json.dump(out, sys.stdout, indent=1)


if __name__ == "__main__":
    main()
