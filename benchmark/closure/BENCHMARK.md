# Pre-registered benchmark 2: Google Closure Compiler (second, unrelated codebase)

Committed 2026-11-27 before any Bug Origin run on Closure. Commons Lang is a Java utility library;
Closure Compiler is a JavaScript optimizer, from another organisation (Google), with a different
build (Ant + jarjar, dependencies checked into `lib/`), a different issue tracker (Google Code)
and different bug reports (JavaScript input and expected compiler output).

## Cases: `cases.csv` (36)
- **Selection:** every Closure bug in Fonte's `combined.csv` (ICSE'23; bug-inducing commits from
  Wen et al. 2019 or manual labelling) that is active in Defects4J. No hand-picking.
- **Commits:**
  - Buggy and fixed commits come from Defects4J `active-bugs.csv`.
  - The bug-inducing commit comes from Fonte.
- **Hash checks (unlike Commons Lang):** all hashes are native git hashes of
  github.com/google/closure-compiler, so no mapping is needed. Before this commit, a local clone
  confirmed that every commit exists and that every bug-inducing commit is an ancestor of its
  buggy commit.
- **Bug reports:** the reports come from the Google Code archive (`report_url`).
- **Mirror text:** the driver mirrors the summary and the comments made before the fix was
  committed, as for Commons Lang.
- **No author roles:** the archive anonymises comment authors, so Closure comments carry **no
  author role labels**. This is a known handicap for the not-a-bug decision.
- **Known structural misses:** two held-out cases (CLOSURE-D4J-65 and CLOSURE-D4J-74) have the
  repository's initial import as their bug-inducing commit. Bug Origin abstains when a test
  fails at the first commit, so these count as misses, and they stay in.

## Split: `split.csv`
- 12 dev cases and 24 held-out cases.
- The order is sha256 of the seed `codegeist-2026-closure-split` plus the case id.
- Only the dev cases may be looked at while adapting the harness and the prompt to Closure.

## Controls: `controls.csv` (9)
- **Not a bug (6):** Google Code reports labelled `Type-Defect` and closed as Invalid,
  WorkingAsIntended or WontFix. They are taken in sha256 order with the seed
  `codegeist-2026-closure-controls` from a pool of 280. The revision is the last first-parent
  commit before the report.
- **Planted wrong fix (3):** held-out cases in the same seed order. The claimed fix is the middle
  first-parent commit strictly between the bug-inducing commit and the buggy commit, so the bug
  is still present there.

## Build (measured before freezing)
Two build routes, tried in order:
1. **Direct javac:** compiles `src`, `gen` and the Rhino sources in `lib/rhino` against
   `lib/*.jar`, without the XMLBeans-only Rhino parts.
2. **Ant fallback:** the repository's own Ant `compile` target, needed once Rhino is repackaged
   with jarjar.

The Ant build file's version-stamp step (`propertyfile`) needs an Ant jar that is not bundled.
It is removed before building; it does not touch any class.

On 40 evenly spaced commits up to the end of 2013, every commit built except the empty
"Create root directories" commit.

## Metrics and protocol
- **Metrics:** the same as for Commons Lang: exact bug-inducing commit, precision when confident,
  confident wrong answers, test validity and false confidence on controls. Each is reported with
  a 95% Wilson interval.
- **Adapting to Closure:** happens on the 12 dev cases only, recorded in `dev-runs/`.
- **Freezing:** a git tag freezes the version before the held-out run.
- **Held-out run:** one zero-touch run on the 24 held-out cases and the 9 controls. All results
  are published, misses included.
