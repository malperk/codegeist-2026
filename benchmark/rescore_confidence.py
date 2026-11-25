"""Re-apply the current confidence rule to recorded bisection results (no re-runs).

For every recorded answer whose previous commit could not compile the test (medium or low),
recompute the confidence with harness.bisect_bic.born_or_moved and print old vs new next to
the ground truth. This is a retrospective check on data the rule was designed after seeing;
it is not a held-out result.

  python3 benchmark/rescore_confidence.py FILE.jsonl [FILE.jsonl ...]
"""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))
from bisect_bic import born_or_moved, class_under_test  # noqa: E402

GIT = str(ROOT / ".cache" / "commons-lang.git")
TRUTH = {r["case_id"]: r["bug_inducing_commit"] for r in csv.DictReader(open(ROOT / "benchmark/cases.csv"))}

for path in sys.argv[1:]:
    for line in open(path):
        d = json.loads(line)
        r = d["record"].get("result") or {}
        if r.get("previous_state") != "NOCOMPILE":
            continue
        new, _ = born_or_moved(GIT, r["previous_commit"], r["answer"], class_under_test(r["test"]))
        truth = TRUTH.get(d["case_id"])
        verdict = "control (any confident answer is false)" if truth is None else \
            ("correct" if r["answer"] == truth else "wrong")
        print(f"{Path(path).name:28} {d['case_id']:28} {r['confidence']:6} -> {new:6} {verdict}")
