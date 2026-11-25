# Dev runs of the shipped agent (Rovo agent "Bug Origin" on the demo site)

Each entry is one end-to-end run: mirror issue -> Rovo agent writes a test -> Forge queue ->
Cloud Run bisection -> comment on the issue. Dev cases only; we tune on these.

## 2026-11-25 run 1: LANG-D4J-22 (LANG-662), mirror CLANG-1 — wrong test, correct abstention
- Agent test: `StringUtilsBugOriginTest.testSubstringBetween`, about `StringUtils.substringBetween`.
  The report is about `Fraction.getReducedFraction(Integer.MIN_VALUE, 2)`. The agent did not read
  the description and copied the class named in the prompt's example.
- The test passed on the reported revision, so no bisection ran: outcome **abstain** (1 test run,
  9 s). No confident wrong answer.
- Fix (dev tuning): new action `get-bug-report` that returns the full report and must be called
  first; the prompt no longer names any concrete class.

## 2026-11-25 run 2: LANG-D4J-22 (LANG-662), mirror CLANG-1 — exact match, high confidence
- Agent called `get-bug-report`, then wrote `org.apache.commons.lang3.math.FractionBugOriginTest`
  based on the snippet in the report (`Fraction.getReducedFraction(Integer.MIN_VALUE, 2)`).
- Bisection: answer `deae2ba23824` = published BIC; previous commit PASS -> confidence **high**.
  66 test runs, 412 s on Cloud Run (the same bisection took 87 s on a laptop: to optimise).
- Human touches: one chat message ("Find where this bug came from").
