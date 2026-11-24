"""Deterministic dev / held-out split of the benchmark cases.

Cases are split by Jira issue, so two Defects4J bugs that share one issue land in the same set.
Order is sha256(SEED + issue), so the split does not depend on any RNG implementation and can be
re-derived by anyone from the committed files.

Usage: python3 split.py cases.csv > split.csv
"""

import csv
import hashlib
import sys

SEED = "codegeist-2026-freeze"
DEV_ISSUES = 9  # one third of the 27 issues; the rest are held out


def main(path: str) -> None:
    rows = list(csv.DictReader(open(path, newline="")))
    issues = sorted({r["jira_issue"] for r in rows},
                    key=lambda i: hashlib.sha256((SEED + i).encode()).hexdigest())
    dev = set(issues[:DEV_ISSUES])
    out = csv.writer(sys.stdout)
    out.writerow(["case_id", "jira_issue", "set"])
    for r in rows:
        out.writerow([r["case_id"], r["jira_issue"], "dev" if r["jira_issue"] in dev else "heldout"])


if __name__ == "__main__":
    main(sys.argv[1])
