# Bug Origin demo video: script and shot list

Target length: about 3:15 (rules: under 5 minutes, YouTube). Narration: Kokoro `af_heart`, one
audio file per scene; each scene lasts as long as its narration plus a short pause. Captions are
burned in. No music, or royalty-free only.

Every number and screen comes from a recorded run in this repository. The "Source" line under each
scene names the file a judge can check. Figures marked **(update)** change if a later run replaces
them (the second codebase is not run yet).

---

### 1. The bug (0:00-0:25)
**Screen:** Apache Jira issue LANG-788, as filed in February 2012. Zoom on the summary, then on the
four-line test in the description.
**Narration:**
> February 2012. A developer clones an object with Apache Commons Lang, and it crashes. The object
> only holds int dot class. The report even includes the test that fails. The maintainer can fix
> it. But every maintainer also wants to know: which change broke this, and when?

**Source:** https://issues.apache.org/jira/browse/LANG-788

### 2. The question nobody has time for (0:25-0:45)
**Screen:** Bisection scene title card: "3,274 commits. Which one broke it?" over a history line.
**Narration:**
> By then the project had more than three thousand commits. Finding the culprit by hand means
> building old versions, one by one, and running a test on each. So usually nobody does it, and
> the same kind of mistake comes back.

**Source:** `benchmark/results/run2/run-2.jsonl` (LANG-D4J-13, total commits on the history).

### 3. Bug Origin in Jira (0:45-1:20)
**Screen:** Live recording on the demo site. A new bug is created; the Automation rule starts the
Rovo agent; the agent's reply comment appears; then the result comment. Zoom on each comment.
**Narration:**
> Bug Origin is a Rovo agent that lives in Jira. When a bug is filed, an Automation rule wakes it
> up. Nobody touches anything from here. The agent reads the whole report, including who said
> what, and decides whether it is a bug at all. Then it writes a small test that reproduces it,
> and runs it once on the reported version, to make sure the test really fails there.

**Source:** issue CLANG-75 on the demo site (run 2), Automation rule "Bug Origin on new bug".

### 4. The test repairs itself (1:20-1:40)
**Screen:** Animated card sequence from a real check log: first attempt "does not compile" with
the compiler line, the API list, second attempt "fails as reported".
**Narration:**
> If the test does not compile, the agent sees the error and the real API of that version, and
> fixes it. It gets three tries, enforced in code. A test that never failed is never trusted.

**Source:** `run-2.jsonl`, LANG-D4J-45 checks: NOCOMPILE, NOCOMPILE, FAIL.

### 5. The search (1:40-2:05)
**Screen:** The bisection animation (prototype scene), replayed from the recorded run: 5 rounds,
4 builds in parallel, ending on commit b82ab99.
**Narration:**
> Then the runner on Google Cloud searches the history with that test. Four old versions at a
> time, built and tested in parallel. Pass, fail, pass. Five rounds, twenty-two test runs, a
> hundred seconds. The test passes on the commit before, and fails from this one on.

**Source:** `video/src/data/bisect-lang-788.json`, replayed by `harness/bisect_bic.py pick()`.

### 6. The answer, and the twist (2:05-2:25)
**Screen:** The result comment on the Jira issue; zoom on the commit link; GitHub commit page title.
**Narration:**
> The answer: a patch from August 2011, six months before the report. It was itself a fix, for
> another user's class loading problem. One fix quietly caused the next bug. Now the team knows
> where it came from, and which kind of change to review harder.

**Source:** commit b82ab9934 (2011-08-02), "Applying Sven Ludwig's patch from LANG-626".

### 7. How often is it right? (2:25-2:55)
**Screen:** Animated scoreboard built from the result files: run 1 vs run 2, the misses listed.
**Narration:**
> We measured it before we believed it: real Commons Lang bugs whose origins are known, and
> reports that are not bugs at all, fixed in advance. The first run found the exact commit for
> six bugs out of eighteen. We published every miss, fixed the causes, and ran again: twelve out
> of eighteen. When it was confident, it was right twelve times out of thirteen. It abstained
> when it could not be sure, and fooled itself once, on a renamed method, which we now know how
> to catch.

**Source:** `benchmark/results/run2/RESULTS-run-2.md` **(update)**.

### 8. Close (2:55-3:15)
**Screen:** Closing card: Bug Origin, "Rovo agent · Forge · Jira Automation · Cloud Run", repo URL,
"every claim has a link: CLAIMS.md".
**Narration:**
> Bug Origin. File a bug, and get its origin, with the evidence attached. Every number in this
> video links to the run that produced it.

---

## Production plan
- **Scenes 2, 4, 5 and 7** are Remotion animations generated from the JSON files named above.
- **Scenes 1, 3 and 6** are real pages:
  - Playwright records them at 1920x1080 with the browser zoomed to 150%.
  - It also saves the bounding box of each element we talk about.
  - Remotion uses those boxes to zoom on exactly that element, the same way on every render.
- **Scene 3** is a fresh live run, recorded while it happens. The wait times are cut, and a
  timer on screen shows the real elapsed time.
- **Narration:** Kokoro `af_heart`, one file per scene; scene lengths come from the audio
  durations.
- **Output:** 1920x1080 H.264 for YouTube; an AV1 copy if an upload must stay under 10 MB.
