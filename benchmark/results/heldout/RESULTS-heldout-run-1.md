# Held-out run 1 (2026-11-25): results, misses included

Version under test: git tag `heldout-run-1` (see `../HELDOUT-VERSION.md`). Nothing was changed
during the run. Every case ran end to end with **zero human touches**: the driver created the
mirror issue on the demo site, the Automation rule started the Rovo agent, the agent wrote a test,
the runner bisected on Cloud Run, the result was posted on the issue. Raw records:
`heldout-run-1.jsonl` (one line per case: issue key, agent test, evidence, timings).

## Headline (95% Wilson intervals; samples are small)

| Metric | Result |
|---|---|
| Exact bug-inducing commit, real cases | **6/18 = 33%** (16-56%) |
| Precision when confident, real cases | **6/6 = 100%** (61-100%) |
| Confident wrong answer, real cases | **0/18** |
| Agent test valid (fails on buggy, passes on fixed) | 11/18 = 61% (39-80%) |
| False confidence on fresh controls | **2/9 = 22%** (6-55%) |
| Precision over all confident answers (cases + controls) | 6/8 = 75% (41-93%) |
| Bisection time when a test was valid | 74-140 s (one build-gap case: 661 s) |

## Real cases (18)

| Case | Jira | Outcome | Confidence | Why |
|---|---|---|---|---|
| LANG-D4J-6 | LANG-857 | **exact** | high | |
| LANG-D4J-13 | LANG-788 | **exact** | high | |
| LANG-D4J-46 | LANG-421 | **exact** | high | |
| LANG-D4J-51 | LANG-365 | **exact** | high | |
| LANG-D4J-53 | LANG-346 | **exact** | high | BIC is "Niall's fix for LANG-59": a fix that caused the next bug |
| LANG-D4J-64 | LANG-259 | **exact** | medium | class under test was new in the BIC |
| LANG-D4J-14 | LANG-786 | not confident | low | answer was in fact correct (see below) |
| LANG-D4J-21 | LANG-677 | not confident | low | answer was in fact correct |
| LANG-D4J-31 | LANG-607 | not confident | low | answer was in fact correct |
| LANG-D4J-40 | LANG-432 | not confident | low | answer was in fact correct |
| LANG-D4J-54 | LANG-328 | abstain | - | 106 commits do not build on JDK 8 |
| LANG-D4J-4, 43, 44, 45, 47, 49, 60 | LANG-882, LANG-477, LANG-457, LANG-419, LANG-412, LANG-380, LANG-295 | abstain | - | agent test invalid (7 cases) |


## Controls (9, frozen in a458ce4 before this run)

| Control | Outcome | Note |
|---|---|---|
| HCTRL-NAB-LANG-394, 770, 820, 988 | abstain | agent declined, reason written on the issue |
| **HCTRL-NAB-LANG-815** | **high (false)** | a committer commented "I don't believe this is a bug"; the agent wrote the reporter's test anyway |
| **HCTRL-NAB-LANG-1039** | **medium (false)** | a committer commented "this behaviour seems correct to me"; ignored |
| HCTRL-WRONGFIX-LANG-D4J-6 | abstain | genuine: the test fails on the buggy commit and on the planted fix |
| HCTRL-WRONGFIX-LANG-D4J-4, 44 | abstain | not evidence: the agent's test was already invalid for these cases |

## What we learned

1. **When Bug Origin is confident on a real bug, it was right every time (6/6).** It never named a
   wrong commit for a real bug in 18 held-out cases.
2. **The main loss is test writing, not search:** 7/18 tests did not reproduce the bug.
3. **The "low" rule is too cautious.** On held-out all 4 "low" answers were the correct commit; on
   the dev set the 2 "low" answers were wrong. Counting "low" as an answer would have given 10/18
   exact here, but that decision is made after seeing the results, so it is not claimed.
4. **The not-a-bug decision misses member comments.** Both false positives had a committer saying
   the behaviour is fine; the report text the agent reads does not say who is a committer.

## Next (run 2, with a new freeze and new controls)
- Mark comment authors with their project role in `get-bug-report` so "a project member says it is
  fine" becomes visible to the agent.
- Second-chance test writing: when validation fails, give the agent the runner's evidence (passes
  on buggy, fails on fixed, compile error) and allow one rewrite. A fixed commit exists only in the
  benchmark; in real use the second chance would use the "passes on the reported revision" signal.
- Re-examine "low": require a second, independent test before downgrading.
