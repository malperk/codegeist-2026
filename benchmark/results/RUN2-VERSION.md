# Version under test for run 2

Frozen 2026-11-25 before run 2. No change to the prompt, app, runner or scoring between this
commit and the end of the run; any later change is reported as a new run.

- Git commit: the commit tagged `run-2` (this file is part of it)
- Forge app: Bug Origin, environment development, major version 3 (adds `check-test` and the
  `read:jira-user` scope)
- Runner image: europe-west2-docker.pkg.dev/life-after-code-2026/codegeist/lang-runner:2b2dc6a
  (built from commit 2b2dc6a; runner and harness code are unchanged since)
- Bisection workers: 4 (Cloud Run, 4 vCPU)
- Cases: the 18 held-out cases in `split.csv` (a re-run, see BENCHMARK.md "Run 2");
  controls: all 9 in `controls_run2.csv`
- Trigger: Automation rule "Bug Origin on new bug" on project CLANG of the demo site; no human touch
- Smoke test before the freeze, on two dev cases only: `dev-runs/smoke-run2-2026-11-25.jsonl`
