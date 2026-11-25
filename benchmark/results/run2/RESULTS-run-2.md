# Run 2 (2026-11-25): results, misses included

Version under test: git tag `run-2` (see `../RUN2-VERSION.md`). Nothing was changed during the
run. All 27 runs were end to end with **zero human touches**. Raw records: `run-2.jsonl` (one line per
case: issue key, every test the agent checked with its output, bisection evidence, timings).

**Read this first.** The 18 real cases are the same as in held-out run 1, and the changes were
designed after seeing run 1's misses (see BENCHMARK.md "Run 2"). This is a re-run after fixing
published misses, not a fresh held-out result. The 9 controls are fresh: drawn by seed and
committed before the run.

## Headline (95% Wilson intervals; samples are small)

| Metric | Run 1 | Run 2 |
|---|---|---|
| Exact bug-inducing commit, real cases | 6/18 = 33% (16-56%) | **12/18 = 67%** (44-84%) |
| Precision when confident, real cases | 6/6 | **12/13 = 92%** (67-99%) |
| Confident wrong answer, real cases | 0/18 | **1/18** (LANG-D4J-47) |
| Agent test valid (fails on buggy, passes on fixed) | 11/18 | **16/18** (67-97%) |
| False confidence on fresh controls | 2/9 | **1/9** (2-44%) |
| Precision over all confident answers | 6/8 | **12/14 = 86%** (60-96%) |
| Bisection time when confident | 74-140 s | 68-122 s |

## What the test check did
- The first test already failed on the reported revision in 15/18 cases. After at most 3 checks,
  18/18 did.
- The check repaired three tests:
  - **LANG-D4J-4:** NOCOMPILE, then FAIL. The answer was exact (high).
  - **LANG-D4J-45:** NOCOMPILE twice, then FAIL. The answer was exact (medium).
  - **LANG-D4J-49:** PASS, then FAIL. The bisection did not finish in time, so the outcome is
    an abstention.
- 34 checks in total across all 27 runs, each 4-9 s (the action limit is 25 s).
- What it cannot catch, as predicted: tests that fail on both the buggy and the fixed revision
  (LANG-D4J-43 and LANG-D4J-44).

## Real cases (18)

| Case | Outcome | Confidence | Note |
|---|---|---|---|
| LANG-D4J-4 | **exact** | high | run 1: test did not compile; repaired by the check |
| LANG-D4J-6, 13, 46, 51, 53 | **exact** | high | same as run 1 |
| LANG-D4J-14, 21, 31, 40 | **exact** | medium | run 1: same commit, called low; rule v2 counts code born in the commit |
| LANG-D4J-45 | **exact** | medium | run 1: test did not compile; repaired by the check |
| LANG-D4J-60 | **exact** | medium | run 1: test passed on the buggy revision; this time the agent's first test already failed (run-to-run variation, not the check) |
| **LANG-D4J-47** | **wrong** | medium | see "The confident miss" |
| LANG-D4J-64 | not confident | low | correct commit, but rule v2 sees the enum package copy as a move (predicted before the run) |
| LANG-D4J-43, 44 | abstain | - | test fails on buggy and on fixed |
| LANG-D4J-49 | abstain | - | test valid after the check; bisection exceeded the 13-minute wait |
| LANG-D4J-54 | abstain | - | 106 commits do not build on JDK 8 (as in run 1) |

### The confident miss: LANG-D4J-47 (LANG-412)
- **The test:** the agent's test calls `StrBuilder.appendFixedWidthPadRight`. It does not
  compile before commit 32e80fc5e8 ("New methods and testing of StrBuilder", 2005), so rule v2
  answered that commit with confidence medium.
- **What the commit really did:** it renamed `appendFixedLengthPad*` to `appendFixedWidthPad*`
  inside the same file. The bug was already present under the old name, from the 2004 commit
  that added StrBuilder, which is the real bug-inducing commit.
- **Why rule v2 missed it:** rule v2 recognises moves of whole files, not renames of methods
  inside a file.
- **Candidate fix, not applied:** treat the answer as low when the commit deletes a public
  method with the same parameter list as a method the test calls. This would not affect
  LANG-D4J-14, where the method name stayed and only the parameter types changed. It will be
  pre-registered before any run that uses it.

## Controls (9, fresh, frozen in b160856 before this run)

| Control | Outcome | Note |
|---|---|---|
| R2CTRL-NAB-LANG-639, 924, 654 | abstain | declined before writing a test; each reply cites a project member's comment |
| R2CTRL-NAB-LANG-911, 792 | abstain | no test failed for the reported reason within 3 checks |
| **R2CTRL-NAB-LANG-997** | **high (false)** | see below |
| R2CTRL-WRONGFIX-LANG-D4J-14, 13, 31 | abstain | **genuine**: the same tests gave exact answers on the real cases, and they fail on the planted fix |

**LANG-997:** the reporter showed that `NumberUtils.isNumber("0123456789")` changed from true
(3.2.1) to false (3.3.2). The bisection found that behaviour change with confidence high. The
committers disagreed in the comments: one wrote "+1 to considering this a regression", while
others said leading zeros mean octal on purpose. In the end it was closed as "Not A Problem".
By the pre-registered rule this is a false positive.
The finding is narrower than "wrong commit": Bug Origin correctly finds where the behaviour
changed. Whether that change is a bug is a judgement the maintainers made after a long
discussion.

## What we learned
1. **Where the 6 extra exact answers came from:**
   - 4 from rule v2 (D4J-14, 21, 31, 40);
   - 2 from tests the check repaired (D4J-4, 45);
   - 1 from run-to-run variation in the agent's test (D4J-60);
   - minus 1 lost to rule v2 (D4J-64).

   The check also repaired D4J-49, but its bisection timed out. The agent is not deterministic,
   so a single re-run cannot separate the check's effect from variation exactly.
2. **The confidence rule is now the weak point.** The one confident miss is a rename the rule
   cannot see. The cost of moving from v1 to v2 was predicted before the run (D4J-64 drops to
   low) and happened as predicted.
3. **The not-a-bug decision improved with author roles** (1/9 false versus 2/9). The remaining
   miss is a genuinely contested report.
