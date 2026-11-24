# Codegeist 2026: Build with context. Ship with confidence.

Atlassian hackathon on Devpost: https://codegeist2026.devpost.com/ (rules: /rules)

## Key facts (from the official rules, read 2026-11-24)

| Item | Value |
|---|---|
| Submission deadline | Tue 22 Dec 2026, 12:00 PT = **20:00 London (GMT)** |
| Judging | 5 Jan – 3 Feb 2027 |
| Winners announced | ~15 Feb 2027 |
| Eligibility | Individuals over age of majority, teams, organizations; UK eligible |
| Registrants at start | 5,185 (2026-11-24) |
| Required tech | Forge app integrating at least one of Jira, Confluence, JSM, Bitbucket, Teamwork Graph, Rovo |
| Testing | Judges install the app from a Forge installation link; full setup instructions required |
| Video | Under 5 minutes, public on YouTube, shows the app working end to end |

### Target category and prizes
- **Apps for Software Teams**: 1st $15,000 (+2 Team '27 tickets), 2nd $8,000, 3rd $5,000.
  Theme examples: smarter code reviews, deployment awareness, issue triage.
- Bonus (one per submission, stackable with a grand prize), $1,500 x 6 each:
  Best Rovo agents (`rovo:agent`, `rovo:skill`, `rovo:action`), Best app with Atlassian MCP
  (`rovo:mcp`), Best Teamwork Graph integration, Best Marketplace published app.
- Participation swag for the first 300 eligible submissions.

### Judging (stage 1 pass/fail on theme + required APIs; stage 2 equally weighted)
1. Technological Implementation: genuine, non-trivial, not a single hardcoded demo path.
2. Design: complete, coherent product experience.
3. Potential Impact: credible, specific case for a real problem for a real audience.
4. Innovation/Idea.
5. Presentation: video shows it working end to end; who it is for and why it matters.

Tie-break order follows the list above, so technical implementation matters most.

## Environment
- Free developer site (Jira, Confluence, JSM; Jira space `KAN`). Name kept out of the repo.
- Forge Developer Space: `Codegeist` (`965da06c-70d0-4f94-98dd-441c7b8a841b`).
- Forge CLI 16 needs Node 22 or 24; the system Node is 25. Prefix every Forge command with
  `PATH=/opt/homebrew/opt/node@24/bin:$PATH`.
- Spike app `spikes/hello-rovo` (Rovo agent + skill preset) is deployed to `development` and
  installed in Jira. The first `forge install` failed with a transient error; a retry worked.
- Rovo chat does not appear on the free developer site. Use the Forge demo site instead:
  `one-atlas-htsv.atlassian.net` (enterprise Jira/Confluence/JSM + Rovo, seeded data,
  expires 2027-02-22, after judging ends). Created with `forge site provision`.
- Verified 2026-11-24: in Rovo chat on the demo site, "Hello world agent" called the
  `rovo-agent-logger` action and `forge logs` showed `Logging message: codegeist spike ok`.
- The demo site already ships built-in agents named "Jira Triage Agent", "Release Notes
  Drafter" and "Ops Expert"; our idea must clearly differ from them (Innovation criterion).

## Plan (apply the lessons in ../CLAUDE.md from day one)
- [x] User: join the hackathon on Devpost and create a free Atlassian Cloud developer site.
- [x] Get Rovo working and chat with the spike agent (done on the demo site).
- [ ] Test the judge installation link (developer console sharing; confirm form with user first).
- [ ] Pick the real user and real problem first (lesson 1), on a well-known open-source codebase (lesson 2).
- [ ] Pre-register a benchmark with seeded cases and expected outcomes before running (lesson 3).
- [ ] Forge spike: hello-world app with a Rovo agent or `rovo:mcp` module, installed via sharing link.
- [ ] CLAIMS.md with one link per claim and per judging criterion (lesson 4).
- [ ] Multiple real runs with recorded evidence (lesson 8).
- [ ] Video with the human story first, real voice (lesson 10).
