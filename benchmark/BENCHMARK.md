# Pre-registered benchmark

Written 2026-11-24. Nothing has been run against these cases. The case list, the split and the
expected outcomes become binding with the first commit that contains this file (the "freeze
commit"). Any later change to cases, split or scoring must be a new, dated commit that says why.

## What the agent claims to do
Given an Apache Jira bug report (title, description and comments as they stood before the fix),
the agent:
1. writes a test that fails on the buggy commit and passes on the fixed commit, and
2. finds the bug-inducing commit (BIC) by bisecting the history with that test.

## Cases: `cases.csv` (27 cases, Apache Commons Lang, 27 distinct LANG Jira issues)
Ground truth is taken from published research, not produced by us:
- **Bug-inducing commits:** Fonte (An et al., ICSE 2023), `data/Defects4J/BIC_dataset/combined.csv`
  in https://github.com/coinse/fonte. It merges Wen et al. 2019 (InduceBenchmark, BICs found by
  running tests) with BICs the Fonte authors identified by hand, and drops Wen points that failed
  their soundness check.
- **Buggy / fixed commits and Jira IDs:** Defects4J, `framework/projects/Lang/active-bugs.csv` in
  https://github.com/rjust/defects4j.
- **Repository:** https://github.com/apache/commons-lang. The buggy and fixed commits are in its
  history as published. The BIC hashes in Fonte come from a different git conversion of the
  same SVN history, so each was mapped to the Apache commit with the same author timestamp and
  subject (23 cases) or the unique commit at that exact author timestamp (4 cases, subjects
  checked by eye). Column `bic_original_hash` keeps the published hash. Every mapped BIC was
  checked to be an ancestor of its buggy commit (27 of 27).
- **Excluded:** `excluded.csv` (Defects4J-deprecated bugs, one Fonte exclusion, and all Commons Math
  cases because their BIC hashes cannot be mapped to any available repository).

## Split: `split.csv`
`split.py` orders Jira issues by sha256 of a fixed seed plus the issue key and puts the first 9 in
the dev set and the other 18 in the held-out set. We may read and tune on dev cases. Held-out
cases are run once, at the end, and published as they come out.

## Metrics (fixed now)
- **Test validity:** the generated test fails on the buggy commit and passes on the fixed commit.
- **BIC exact match:** the reported commit equals `bug_inducing_commit`.
- **Abstention:** the agent may answer "not confident". An abstention counts as a miss for exact
  match and is also reported on its own (precision when the agent does answer).
- Results are reported per case, misses included, not only as totals.

## Protocol for each run
Record: the Jira text given to the agent, the generated test, the bisect log, the chosen commit,
wall time, model calls and cost, and every human touch (target: zero).

## Controls: `controls.csv` (added 2026-11-24, before any run)
Nine cases whose only correct outcome is an abstention. A confident answer on any of them is a
failure and is reported as a false positive.
- **Not a bug (6):** LANG bugs that Apache resolved as "Not A Problem" or "Invalid" (created
  2008-2014), chosen by sha256 order with seed `codegeist-2026-controls` from all 26 such issues,
  no hand-picking. Revision = last first-parent commit on `master` before the report was created.
  One of them (LANG-861) is a misfiled, unrelated report; it stays in because the rule picked it.
- **Planted wrong fix (3):** dev cases whose "fixed" commit is replaced by another case's fix that
  does not contain the real fix (same seed rule). A correct test still fails on the claimed fix,
  so the agent must report that it cannot show test validity instead of claiming success.

Extra metric: **false-confidence rate** = confident answers on controls / 9.

## Amendment 2026-11-25: planted-wrong-fix controls were badly designed
The three `CTRL-WRONGFIX-*` controls replaced the fixed commit with another case's fix that does
not contain the real fix. Two of those commits (and possibly all three) are *older than the
bug-inducing commit*, so the bug is absent there and the test passes or cannot compile: they do
not test what they claim to. Their first results are kept unchanged in
`results/dev-runs/dev-2026-11-25.jsonl` (one high-confidence answer, two abstentions that are not
evidence) and are excluded from the false-confidence rate.
Replacement: `CTRL-WRONGFIX2-*` (same three dev cases). The claimed fix is the middle commit of the
first-parent history strictly between the BIC and the buggy commit, where the bug is present, so
a correct test fails on it and the only correct outcome is an abstention. This rule was written
after seeing the first results; it is reported as an amendment, not as part of the original freeze.

## Held-out controls: `controls_heldout.csv` (added 2026-11-25, before any run on them)
The dev controls have been used to tune the abstain decision, so the held-out evaluation uses a
fresh set, never run before this commit: 6 not-a-bug controls drawn by sha256 order with seed
`codegeist-2026-controls-heldout` from the 20 "Not A Problem"/"Invalid" LANG bugs (2008-2014) not
used as dev controls, and 3 planted-wrong-fix controls on held-out cases chosen with the same seed,
using the corrected rule (claimed fix strictly between the BIC and the buggy commit).
