"""Benchmark driver: mirror an Apache Jira bug into the demo site and collect Bug Origin's result.

  python3 driver.py create CASE_ID      -> creates the mirror issue, prints its key
  python3 driver.py result ISSUE_KEY    -> prints the stored job record (JSON)

What the agent sees: the original summary and description, plus only the comments written
before the fix was committed (so no comment can leak the fix). What it never sees: the fixed
commit and the expected bug-inducing commit; the fixed commit is stored in app storage only
to measure test validity.

Needs .cache/bench_url and .cache/bench_token (created at setup, never committed).
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GIT = str(ROOT / ".cache" / "commons-lang.git")
APACHE = "https://issues.apache.org/jira/rest/api/2/issue/{}?fields=summary,description,created,comment"
PROJECT = "CLANG"


def secret(name: str) -> str:
    return (ROOT / ".cache" / name).read_text().strip()


def call(body: dict) -> dict:
    req = urllib.request.Request(secret("bench_url"), data=json.dumps(body).encode(),
                                 headers={"x-bench-token": secret("bench_token"),
                                          "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=60))


def commit_time(sha: str) -> datetime:
    out = subprocess.run(["git", "--git-dir", GIT, "log", "-1", "--format=%cI", sha],
                         capture_output=True, text=True, check=True).stdout.strip()
    return datetime.fromisoformat(out)


def jira_time(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%f%z")


def lookup(case_id: str) -> dict:
    for name in ("cases.csv", "controls.csv"):
        for row in csv.DictReader(open(ROOT / "benchmark" / name)):
            if row.get("case_id", row.get("control_id")) == case_id:
                return row
    raise SystemExit(f"unknown case {case_id}")


def mirror_text(issue: str, cutoff: datetime | None) -> tuple[str, str, list[str]]:
    data = json.load(urllib.request.urlopen(APACHE.format(issue), timeout=60))["fields"]
    kept = []
    for c in data.get("comment", {}).get("comments", []):
        if cutoff is None or jira_time(c["created"]) < cutoff:
            kept.append(f"--- Comment by {c['author']['displayName']} ({c['created'][:10]}):\n{c['body']}")
    desc = (data.get("description") or "(no description)") + "\n\n" + "\n\n".join(kept)
    note = f"\n\n(Mirrored from Apache Jira {issue}, reported {data['created'][:10]}.)"
    return data["summary"], desc + note, [c[:60] for c in kept]


def create(case_id: str) -> None:
    row = lookup(case_id)
    kind = row.get("kind", "case")
    if kind == "planted_wrong_fix":
        rev = dict(p.split("=") for p in row["revision"].split(";"))
        buggy, fixed = rev["buggy"], rev["claimed_fix"]
    elif kind == "not_a_bug":
        buggy, fixed = row["revision"], ""
    else:
        buggy, fixed = row["buggy_commit"], row["fixed_commit"]
    # Comments after the real fix could reveal it; for controls without a fix keep all comments.
    cutoff = commit_time(row["fixed_commit"]) if "fixed_commit" in row else None
    summary, description, kept = mirror_text(row["jira_issue"], cutoff)
    out = call({"op": "create", "projectKey": PROJECT, "summary": f"[{row['jira_issue']}] {summary}",
                "description": description, "revision": buggy, "fixed": fixed, "caseId": case_id})
    print(json.dumps({"case": case_id, "issueKey": out.get("issueKey"), "comments_kept": len(kept),
                      "response": out if "issueKey" not in out else None}))


if __name__ == "__main__":
    op, arg = sys.argv[1:3]
    if op == "create":
        create(arg)
    elif op == "result":
        print(json.dumps(call({"op": "result", "issueKey": arg}), indent=1))
