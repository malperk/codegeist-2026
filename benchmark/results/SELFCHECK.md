# Harness self-check on the 9 dev cases (2026-11-24)

This checks the test runner and the ground truth, not the agent. For each dev case the
developer's own failing test (Defects4J trigger test, taken from the fixed commit and cut down
to that one method by `harness/minimal_test.py`) is run with `harness/run_test.py` on four commits.
Expected: buggy = FAIL, fixed = PASS, bug-inducing commit (BIC) = FAIL, BIC parent = PASS or
NOCOMPILE (the code under test did not exist yet). Raw output: `selfcheck-dev.json`.

| Case | Jira | buggy | fixed | BIC | BIC parent | Verdict |
|---|---|---|---|---|---|---|
| LANG-D4J-19 | LANG-710 | FAIL | PASS | FAIL | NOCOMPILE | as expected |
| LANG-D4J-22 | LANG-662 | FAIL | PASS | FAIL | PASS | as expected |
| LANG-D4J-26 | LANG-645 | FAIL | PASS | FAIL | NOCOMPILE | as expected |
| LANG-D4J-28 | LANG-617 | FAIL | PASS | FAIL | NOCOMPILE | as expected |
| LANG-D4J-39 | LANG-552 | FAIL | PASS | FAIL | **FAIL** | test fails before the labelled BIC |
| LANG-D4J-52 | LANG-363 | FAIL | PASS | FAIL | NOCOMPILE | as expected |
| LANG-D4J-55 | LANG-315 | FAIL | PASS | FAIL | NOCOMPILE | as expected |
| LANG-D4J-57 | LANG-304 | FAIL | PASS | **ERROR** | **ERROR** | main code at the BIC does not compile on JDK 8 |
| LANG-D4J-61 | LANG-294 | FAIL | PASS | **NOCOMPILE** | NOCOMPILE | developer test needs an API newer than the BIC |

## What this shows
- The runner reproduces every bug: 9 of 9 fail on the buggy commit and pass on the fixed one.
- For 6 of 9, the published BIC is confirmed by testing.
- In 6 of 9 the BIC is the commit that created the code under test (its parent cannot compile the
  test). Bisection must therefore treat NOCOMPILE as "feature absent", not as an error.
- Three cases cannot be confirmed by testing in this environment. They stay in the benchmark
  unchanged (the case list is frozen); they are reported here so nobody reads our later scores
  without knowing the ground truth itself is not test-verifiable for them.

## Changes to the runner while getting here
`git archive` export; JDK 8 in Docker without network; Lang 2 vs 3 source layouts; translating
`org.apache.commons.lang3` back to `org.apache.commons.lang` for older commits; `-source 1.4` when
the `enum` package exists; dependency jars (JUnit 4.12, Hamcrest 1.3, EasyMock 3.2, Commons IO
2.4, JCIP and JSR-305 annotations) on both compile class paths; NOCOMPILE as its own result.

# Method ceiling on the dev cases: bisection with the developer's test (2026-11-24)

`harness/bisect_bic.py` run with each dev case's developer test (`harness/oracle_dev.py`, raw
output `oracle-dev.json`). This is the best the agent can do if it writes a test as good as the
developer's; it is not an agent result.

| Case | Jira | Result | Confidence | Test runs | Time |
|---|---|---|---|---|---|
| LANG-D4J-19 | LANG-710 | match | medium | 14 | 33 s |
| LANG-D4J-22 | LANG-662 | match | high | 66 | 147 s |
| LANG-D4J-26 | LANG-645 | match | medium | 104 | 237 s |
| LANG-D4J-28 | LANG-617 | match | medium | 20 | 41 s |
| LANG-D4J-39 | LANG-552 | **miss** (earlier commit than the label) | medium | 13 | 28 s |
| LANG-D4J-52 | LANG-363 | match | medium | 12 | 24 s |
| LANG-D4J-55 | LANG-315 | match | medium | 13 | 27 s |
| LANG-D4J-57 | LANG-304 | abstain (106 unbuildable commits) | abstain | 113 | 239 s |
| LANG-D4J-61 | LANG-294 | abstain (106 unbuildable commits) | abstain | 112 | 236 s |

Exact match 6/9. The three misses are the three cases the self-check could not confirm; two of
them end in an abstention rather than a confident wrong answer. LANG-552 is a confident answer
that disagrees with the published label, and is the first case to investigate by hand.
