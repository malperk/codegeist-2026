"""Draw a fresh set of controls with a given seed, excluding every control used before.

  python3 draw_controls.py SEED PREFIX OUT.csv

Not a bug (6): LANG bugs resolved "Not A Problem" or "Invalid", created 2008-2014, ordered by
sha256(seed + issue key), skipping issues already used as controls. Revision = last first-parent
commit on master before the report was created.
Planted wrong fix (3): held-out cases ordered by sha256(seed + case id), skipping cases already
used for this kind of control. Claimed fix = middle first-parent commit strictly between the
bug-inducing commit and the buggy commit (the bug is present there, so a correct test fails).
"""

import csv
import hashlib
import json
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GIT = str(ROOT / ".cache" / "commons-lang.git")
JQL = ('project = LANG AND issuetype = Bug AND resolution in ("Not A Problem", Invalid) '
       'AND created >= 2008-01-01 AND created < 2015-01-01 ORDER BY key')
FIELDS = "control_id,kind,jira_issue,jira_url,repo,revision,expected_outcome,note".split(",")


def order(seed: str, keys: list[str]) -> list[str]:
    return sorted(keys, key=lambda k: hashlib.sha256((seed + k).encode()).hexdigest())


def git(*args: str) -> str:
    return subprocess.run(["git", "--git-dir", GIT, *args], capture_output=True, text=True, check=True).stdout


def used() -> tuple[set[str], set[str]]:
    issues, cases = set(), set()
    for name in sorted((ROOT / "benchmark").glob("controls*.csv")):
        for r in csv.DictReader(open(name)):
            if r["kind"] == "not_a_bug":
                issues.add(r["jira_issue"])
            else:
                cases.add(r["control_id"].split("WRONGFIX")[-1].lstrip("2-"))
    return issues, cases


def main(seed: str, prefix: str, out: str) -> None:
    used_issues, used_cases = used()
    url = ("https://issues.apache.org/jira/rest/api/2/search?maxResults=200&fields=summary,created,resolution&jql="
           + urllib.parse.quote(JQL))
    pool = {i["key"]: i["fields"] for i in json.load(urllib.request.urlopen(url, timeout=60))["issues"]}
    fresh = [k for k in order(seed, list(pool)) if k not in used_issues]
    print(f"{len(pool)} not-a-bug issues, {len(fresh)} unused")
    rows = []
    for key in fresh[:6]:
        f = pool[key]
        day = f["created"][:10]
        rev = git("rev-list", "-1", "--first-parent", f"--before={f['created']}", "master").strip()
        rows.append({"control_id": f"{prefix}-NAB-{key}", "kind": "not_a_bug", "jira_issue": key,
                     "jira_url": f"https://issues.apache.org/jira/browse/{key}",
                     "repo": "https://github.com/apache/commons-lang", "revision": rev,
                     "expected_outcome": "abstain",
                     "note": f"Resolved '{f['resolution']['name']}'; revision = last first-parent commit before {day}"})
    cases = {r["case_id"]: r for r in csv.DictReader(open(ROOT / "benchmark/cases.csv"))}
    heldout = [r["case_id"] for r in csv.DictReader(open(ROOT / "benchmark/split.csv")) if r["set"] == "heldout"]
    for cid in [c for c in order(seed, heldout) if c not in used_cases][:3]:
        c = cases[cid]
        chain = git("rev-list", "--first-parent", "--reverse", f"{c['bug_inducing_commit']}..{c['buggy_commit']}").split()
        between = chain[:-1]  # strictly between BIC and buggy
        claimed = between[len(between) // 2]
        rows.append({"control_id": f"{prefix}-WRONGFIX-{cid}", "kind": "planted_wrong_fix",
                     "jira_issue": c["jira_issue"], "jira_url": c["jira_url"], "repo": c["repo"],
                     "revision": f"buggy={c['buggy_commit']};claimed_fix={claimed}", "expected_outcome": "abstain",
                     "note": f"claimed_fix = middle first-parent commit strictly between BIC and buggy ({len(between)} candidates)"})
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, FIELDS)
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(r["control_id"], r["revision"][:60])


if __name__ == "__main__":
    main(*sys.argv[1:4])
