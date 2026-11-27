"""Generate the video's data files from the benchmark results, so every number on screen is traceable.

  python3 build_data.py
writes src/data/checks.json (scene 4) and src/data/scoreboard.json (scene 7).
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "src" / "data"


def load(path: str) -> list[dict]:
    return [json.loads(l) for l in open(ROOT / path)]


def board(rows: list[dict]) -> dict:
    cases = [r for r in rows if r["score"]["kind"] == "case"]
    ctr = [r for r in rows if r["score"]["kind"] != "case"]
    return {"cases": len(cases), "exact": sum(r["score"]["exact_match"] for r in cases),
            "confident": sum(r["score"]["confident"] for r in cases),
            "confidentWrong": sum(r["score"]["confident_wrong"] for r in cases),
            "controls": len(ctr), "falseConfidence": sum(r["score"]["false_confidence"] for r in ctr)}


run2 = load("benchmark/results/run2/run-2.jsonl")
case = next(r for r in run2 if r["case_id"] == "LANG-D4J-45")
checks = [{"result": c["result"], "seconds": c["seconds"],
           "line": next((l.strip() for l in c["output"].splitlines() if "error:" in l or l.startswith("FAILURE")), ""),
           } for c in case["record"]["checks"]]
(OUT / "checks.json").write_text(json.dumps({"case": "LANG-D4J-45", "issue": case["issue"], "checks": checks,
                                             "source": "benchmark/results/run2/run-2.jsonl"}, indent=1))
sb = {"run1": board(load("benchmark/results/heldout/heldout-run-1.jsonl")), "run2": board(run2),
      "sources": ["benchmark/results/heldout/heldout-run-1.jsonl", "benchmark/results/run2/run-2.jsonl"]}
(OUT / "scoreboard.json").write_text(json.dumps(sb, indent=1))
print(json.dumps(checks, indent=1)); print(sb)
