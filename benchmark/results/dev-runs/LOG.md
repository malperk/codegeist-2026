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

## 2026-11-25 run 3: LANG-D4J-19 (LANG-710), mirror CLANG-2 — miss (medium), zero touch
- Started by the Automation rule "Bug Origin on new bug" one second after the issue was
  created (audit log 852f6bcf-8567-4e74-9b4f-39bfcd27b1f1). No human touch.
- Agent test: `StringEscapeUtilsBugOriginTest`, calls `StringEscapeUtils.unescapeHtml4("&#03")`.
- Answer `0714795b6fd2` (medium); expected `c404121979002`. 14 test runs, 87 s.
- Cause: `unescapeHtml4` is a later name of `unescapeHtml`. Before the rename the test cannot
  compile, and the search read NOCOMPILE as "the code did not exist yet".
- Fix (dev tuning): "medium" now requires that the class under test did not exist on the
  previous commit; otherwise the answer is "low" (counted as an abstention). Re-checked on the
  oracle dev runs: the 5 correct medium answers stay medium, the LANG-552 miss becomes low, and
  this run becomes low. Oracle dev: 6/9 exact, 0 confident wrong.

## 2026-11-25 dev batch (zero human touch): `dev-2026-11-25.jsonl`
Each case: driver creates the mirror issue -> Automation rule starts the agent -> result.

| Case | Jira | Outcome | Confidence | Note |
|---|---|---|---|---|
| LANG-D4J-19 | LANG-710 | not confident | low | test uses the later name `unescapeHtml4` |
| LANG-D4J-22 | LANG-662 | **exact** | high | |
| LANG-D4J-26 | LANG-645 | **exact** | medium | |
| LANG-D4J-28 | LANG-617 | abstain | - | agent test fails on the fixed commit too (invalid test) |
| LANG-D4J-39 | LANG-552 | not confident | low | test uses a newer API |
| LANG-D4J-52 | LANG-363 | abstain | - | agent test fails on the fixed commit too (invalid test) |
| LANG-D4J-55 | LANG-315 | **exact** | medium | |
| LANG-D4J-57 | LANG-304 | abstain | - | 106 commits do not build on JDK 8 (same as oracle) |
| LANG-D4J-61 | LANG-294 | abstain | - | 106 commits do not build on JDK 8 (same as oracle) |

Exact match 3/9, confident wrong 0/9, valid tests 7/9. Oracle ceiling on the same cases 6/9.
Bisection with 4 parallel workers: 53-89 s (was 412 s sequential).

## 2026-11-25 controls: `controls-2026-11-25.jsonl`
- Corrected planted-wrong-fix controls (`CTRL-WRONGFIX2-*`, 3): 3/3 abstained.
- Not-a-bug controls (6): 5/6 no confident answer (4 agent declined to start a job, 1 low).
  **LANG-885 is a false positive**: the report is a question ("Am I missing anything?") and a
  maintainer comment says the methods are not documented to throw. The agent still wrote a test
  for the reporter's expectation; that behaviour really did change at `c404121` (2009 rewrite),
  so the search named it with high confidence. The commit is where the behaviour began, but the
  report is not a bug.
- False-confidence rate on valid controls: **1/9**. The three original `CTRL-WRONGFIX-*` results
  are excluded (badly designed, see BENCHMARK.md amendment).

## Consequence for the held-out evaluation
These 9 controls have now been seen and will be used for tuning the abstain decision, so they can
no longer measure it fairly. Before the held-out run, a fresh set of not-a-bug controls will be
drawn by the same seed rule from the 20 remaining "Not A Problem"/"Invalid" LANG issues and
committed before it is run.

## 2026-11-25 dev round 2 (new triage and assertion rules): `dev2-2026-11-25.jsonl`
- Dev cases: the same 3/9 exact (LANG-662 high, LANG-645 medium, LANG-315 medium), 0 confident
  wrong. The stricter not-a-bug triage did not make the agent drop any real bug.
- Controls: 9/9 no confident answer (3 corrected wrong-fix abstained in validation; 6 not-a-bug:
  the agent declined to start a job, each with a written reason on the issue, e.g. LANG-885:
  "ABSTAIN: A project member's comment indicates the behavior is not documented to throw
  exceptions"). These controls were used for tuning, so this 0/9 is not a fair measure; the
  held-out controls (`controls_heldout.csv`, frozen in a458ce4) are.
- LANG-363 again sent `"<https://script>"` instead of `"<\/script>"`, with `<redacted URL>` in the
  assertion message: Rovo appears to redact URL-like text in action inputs. Mitigation: the
  prompt now asks for slash sequences to be built by concatenation.

## 2026-11-25 dev run: LANG-D4J-52 (LANG-363) after the URL rule — abstain
String literals now arrive intact (built by concatenation). The test still fails on the fixed
commit: it expects no escaping of single quotes, while escapeJavaScript does escape them. The
validity check rejected it: abstention, not a wrong answer. Tuning stops here.
