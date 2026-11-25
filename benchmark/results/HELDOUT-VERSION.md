# Version under test for the held-out run

Frozen 2026-11-25 before the held-out run. No change to the prompt, app, runner or scoring
between this commit and the end of the run; any later change is reported as a new run.

- Git commit: the commit tagged `heldout-run-1` (this file is part of it)
- Forge app: Bug Origin (ari:cloud:ecosystem::app/39f05cbd-b619-4ff6-8832-a6666e5c7b32),
  environment development, deployed version see forge deploy list
- Runner image: europe-west2-docker.pkg.dev/life-after-code-2026/codegeist/lang-runner:1d10425
- Bisection workers: 4 (Cloud Run, 4 vCPU)
- Cases: the 18 held-out cases in `split.csv`; controls: all 9 in `controls_heldout.csv`
- Trigger: Automation rule "Bug Origin on new bug" on project CLANG of the demo site; no human touch
