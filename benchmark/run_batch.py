"""Run a set of benchmark cases end to end, one after another, with no human touch.

For each case: create the mirror issue (the Automation rule starts the Rovo agent), wait for the
job record, score it, append one JSON line to the output file.

  python3 run_batch.py OUT.jsonl CASE_ID [CASE_ID ...]
"""

import csv
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from driver import ROOT, call, lookup

WAIT_S = 20 * 60


def score(row: dict, rec: dict) -> dict:
    r = rec.get("result") or {}
    conf = r.get("confidence", "none" if rec.get("status") == "none" else "abstain")
    confident = conf in ("high", "medium")
    if "bug_inducing_commit" in row:  # real case
        exact = confident and r.get("answer") == row["bug_inducing_commit"]
        return {"kind": "case", "confident": confident, "exact_match": exact,
                "confident_wrong": confident and not exact}
    return {"kind": row["kind"], "confident": confident, "false_confidence": confident}


def main(out: str, cases: list[str]) -> None:
    for case_id in cases:
        row = lookup(case_id)
        started = datetime.now(timezone.utc).isoformat()
        created = subprocess.run([sys.executable, str(ROOT / "benchmark/driver.py"), "create", case_id],
                                 capture_output=True, text=True, check=True)
        key = json.loads(created.stdout)["issueKey"]
        deadline = time.time() + WAIT_S
        rec = {"status": "none"}
        while time.time() < deadline:
            time.sleep(20)
            rec = call({"op": "result", "issueKey": key})
            if rec.get("status") in ("done", "error"):
                break
            # The agent replied without starting a job: it abstained. Give a queued job a
            # moment to register first (the reply comment is written after the action returns).
            if rec.get("status") == "none" and rec.get("agentReply"):
                time.sleep(20)
                rec = call({"op": "result", "issueKey": key})
                if rec.get("status") == "none":
                    rec["result"] = {"confidence": "abstain", "reason": "agent declined to start a job"}
                    break
        line = {"case_id": case_id, "issue": key, "created_at": started, "record": rec,
                "score": score(row, rec), "human_touches": 0}
        with open(out, "a") as f:
            f.write(json.dumps(line) + "\n")
        r = rec.get("result") or {}
        print(case_id, key, rec.get("status"), r.get("confidence"), (r.get("answer") or "")[:12],
              line["score"], flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
