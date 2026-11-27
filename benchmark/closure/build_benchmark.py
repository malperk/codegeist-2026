"""Build the Closure Compiler benchmark files before any run: cases, split and controls.

  python3 build_benchmark.py FONTE_COMBINED_CSV DEFECTS4J_CLOSURE_ACTIVE_BUGS_CSV

cases.csv     every Closure bug in Fonte's combined.csv (ICSE'23) that is active in Defects4J;
              buggy/fixed commits from Defects4J, bug-inducing commit from Fonte. All hashes are
              native git hashes of github.com/google/closure-compiler (checked: each exists and the
              BIC is an ancestor of the buggy commit).
split.csv     12 dev / rest held-out, by sha256(seed + case id).
controls.csv  9 controls: 6 bug reports Google Code closed as Invalid, WorkingAsIntended or WontFix
              (sha256 order, seed below), revision = last first-parent commit before the report;
              3 planted wrong fixes on held-out cases (claimed fix = middle first-parent commit
              strictly between the BIC and the buggy commit).
"""

import csv
import hashlib
import json
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
GIT = str(HERE.parents[1] / ".cache" / "closure-compiler.git")
ARCHIVE = "https://storage.googleapis.com/google-code-archive/v2/code.google.com/closure-compiler"
SPLIT_SEED, CONTROL_SEED, DEV = "codegeist-2026-closure-split", "codegeist-2026-closure-controls", 12
NOT_A_BUG = {"Invalid", "WorkingAsIntended", "WontFix"}


def git(*a: str) -> str:
    return subprocess.run(["git", "--git-dir", GIT, *a], capture_output=True, text=True, check=True).stdout.strip()


def order(seed: str, keys: list[str]) -> list[str]:
    return sorted(keys, key=lambda k: hashlib.sha256((seed + k).encode()).hexdigest())


def get(url: str):
    return json.load(urllib.request.urlopen(url, timeout=60))


def main(fonte: str, active: str) -> None:
    d4j = {r["bug.id"]: r for r in csv.DictReader(open(active))}
    cases = []
    for r in csv.DictReader(open(fonte)):
        if r["pid"] != "Closure" or r["vid"] not in d4j:
            continue
        a = d4j[r["vid"]]
        bic = git("rev-parse", r["commit"] + "^{commit}")
        assert subprocess.run(["git", "--git-dir", GIT, "merge-base", "--is-ancestor", bic, a["revision.id.buggy"]]).returncode == 0
        cases.append({"case_id": f"CLOSURE-D4J-{r['vid']}", "issue": f"closure-compiler-{a['report.id']}",
                      "report_url": a["report.url"], "repo": "https://github.com/google/closure-compiler",
                      "buggy_commit": a["revision.id.buggy"], "fixed_commit": a["revision.id.fixed"],
                      "bug_inducing_commit": bic, "bic_source": f"Fonte ICSE'23 combined.csv ({r['provenance']})"})
    cases.sort(key=lambda c: int(c["case_id"].rsplit("-", 1)[1]))
    with open(HERE / "cases.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(cases[0]))
        w.writeheader(); w.writerows(cases)
    dev = set(order(SPLIT_SEED, [c["case_id"] for c in cases])[:DEV])
    with open(HERE / "split.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["case_id", "set"])
        for c in cases:
            w.writerow([c["case_id"], "dev" if c["case_id"] in dev else "heldout"])

    # Controls: not-a-bug reports, defects only, never used as a Defects4J case.
    used = {c["issue"].rsplit("-", 1)[1] for c in cases}
    pool = []
    for page in range(1, get(f"{ARCHIVE}/issues-page-1.json")["totalPages"] + 1):
        for i in get(f"{ARCHIVE}/issues-page-{page}.json")["issues"]:
            if i["status"] in NOT_A_BUG and "Type-Defect" in i["labels"] and str(i["id"]) not in used:
                pool.append(str(i["id"]))
    rows = []
    for iid in order(CONTROL_SEED, pool):
        issue = get(f"{ARCHIVE}/issues/issue-{iid}.json")
        created = datetime.fromtimestamp(issue["comments"][0]["timestamp"], timezone.utc)
        rev = git("rev-list", "-1", "--first-parent", f"--before={created.isoformat()}", "master")
        if not rev:
            continue  # reported before the first commit
        rows.append({"control_id": f"CCTRL-NAB-{iid}", "kind": "not_a_bug", "issue": f"closure-compiler-{iid}",
                     "report_url": f"{ARCHIVE}/issues/issue-{iid}.json", "revision": rev, "expected_outcome": "abstain",
                     "note": f"Google Code status '{issue['status']}'; revision = last first-parent commit before {created.date()}"})
        if len(rows) == 6:
            break
    held = [c for c in order(CONTROL_SEED, [c["case_id"] for c in cases]) if c not in dev]
    by_id = {c["case_id"]: c for c in cases}
    for cid in held[:3]:
        c = by_id[cid]
        between = git("rev-list", "--first-parent", "--reverse", f"{c['bug_inducing_commit']}..{c['buggy_commit']}").split()[:-1]
        rows.append({"control_id": f"CCTRL-WRONGFIX-{cid}", "kind": "planted_wrong_fix", "issue": c["issue"],
                     "report_url": c["report_url"], "revision": f"buggy={c['buggy_commit']};claimed_fix={between[len(between) // 2]}",
                     "expected_outcome": "abstain",
                     "note": f"claimed_fix = middle first-parent commit strictly between BIC and buggy ({len(between)} candidates)"})
    with open(HERE / "controls.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print(len(cases), "cases,", DEV, "dev;", len(pool), "not-a-bug pool;", [r["control_id"] for r in rows])


if __name__ == "__main__":
    main(*sys.argv[1:3])
