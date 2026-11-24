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

## Controls (to be added before any held-out run, in a dated commit)
Misleading reports and planted wrong "fixes" whose correct outcome is an abstention, not a
confident wrong commit.
