import api, { route, invokeRemote } from '@forge/api';
import { Queue } from '@forge/events';
import { kvs } from '@forge/kvs';

const queue = new Queue({ key: 'bisect-jobs' });
const SHA = /^[0-9a-f]{7,40}$/;
const POLL_MS = 15000;
const MAX_WAIT_MS = 13 * 60 * 1000; // consumer timeout is 15 minutes
const MAX_CHECKS = 3; // test attempts per issue, enforced here rather than in the prompt

/** Short, stable fingerprint of a test source, to tie a bisection to a checked test. */
function fingerprint(source) {
  const text = source.replace(/\s+/g, ''); // the agent may re-indent the test between calls
  let h = 2166136261;
  for (let i = 0; i < text.length; i += 1) h = Math.imul(h ^ text.charCodeAt(i), 16777619) >>> 0;
  return h.toString(16);
}

/** Revision the bug was reported against: issue property first, then "Revision: <sha>" text. */
async function revisionOf(issueKey) {
  const prop = await api.asApp().requestJira(route`/rest/api/3/issue/${issueKey}/properties/bug-origin`);
  if (prop.ok) {
    const { value } = await prop.json();
    if (value && SHA.test(value.revision || '')) return value.revision;
  }
  const res = await api.asApp().requestJira(route`/rest/api/2/issue/${issueKey}?fields=description`);
  if (!res.ok) throw new Error(`cannot read ${issueKey}: ${res.status}`);
  const { fields } = await res.json();
  const m = /Revision:\s*([0-9a-f]{7,40})/i.exec(fields.description || '');
  return m ? m[1] : null;
}

async function comment(issueKey, paragraphs) {
  const body = {
    type: 'doc', version: 1,
    content: paragraphs.map((p) => ({ type: 'paragraph', content: [{ type: 'text', text: p }] })),
  };
  const res = await api.asApp().requestJira(route`/rest/api/3/issue/${issueKey}/comment`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ body }),
  });
  if (!res.ok) console.error(`comment on ${issueKey} failed: ${res.status} ${await res.text()}`);
}

/** Rovo action: the full text of the bug report, so the agent never works from the title alone. */
export async function getBugReport(payload) {
  const issueKey = payload.issueKey || payload.context?.jira?.issueKey;
  if (!issueKey) return 'No issue key: open the agent from a Jira issue or pass issueKey.';
  const res = await api.asApp().requestJira(
    route`/rest/api/2/issue/${issueKey}?fields=summary,description,comment,issuetype`);
  if (!res.ok) return `Could not read ${issueKey}: ${res.status}`;
  const { fields } = await res.json();
  const kept = (fields.comment?.comments || []).filter((c) => !/^Bug Origin/.test(c.body || ''));
  const roles = {};
  for (const c of kept) {
    const id = c.author?.accountId;
    if (id && !(id in roles)) roles[id] = await isProjectMember(issueKey, id);
  }
  const comments = kept.map((c) => {
    const role = roles[c.author?.accountId] ? 'project member' : 'not a project member';
    return `Comment by ${c.author?.displayName} [${role}] (${c.created?.slice(0, 10)}):\n${c.body}`;
  });
  return [`Issue ${issueKey} (${fields.issuetype?.name})`, `Summary: ${fields.summary}`,
    `Description:\n${fields.description || '(none)'}`, ...comments].join('\n\n');
}

/** A project member here is someone who may resolve issues in the project. */
async function isProjectMember(issueKey, accountId) {
  const res = await api.asApp().requestJira(
    route`/rest/api/3/user/permission/search?permissions=RESOLVE_ISSUES&issueKey=${issueKey}&accountId=${accountId}`);
  if (!res.ok) return false;
  const users = await res.json();
  return Array.isArray(users) && users.some((u) => u.accountId === accountId);
}

function validTest({ testClass, testMethod, testSource }) {
  if (!/^[\w.$]+$/.test(testClass || '') || !/^test\w*$/.test(testMethod || '')) {
    return 'testClass must be a Java class name and testMethod must start with "test".';
  }
  if (!testSource || testSource.length > 100000) return 'testSource is missing or too large.';
  return null;
}

/**
 * Rovo action: run the test once on the reported revision and return what happened, so the
 * agent can repair a test that does not compile or does not fail before asking for a bisection.
 * Only the reported revision is used: a real user has no fixed commit to check against.
 */
export async function checkTest(payload) {
  const issueKey = payload.issueKey || payload.context?.jira?.issueKey;
  if (!issueKey) return 'No issue key: open the agent from a Jira issue or pass issueKey.';
  const bad = validTest(payload);
  if (bad) return bad;
  const { testClass, testMethod, testSource } = payload;
  const revision = await revisionOf(issueKey);
  if (!revision) return `No revision on ${issueKey}: add a line "Revision: <commit sha>" to the description.`;
  const checks = (await kvs.get(`checks:${issueKey}`)) || [];
  if (checks.length >= MAX_CHECKS) {
    return `Check limit reached (${MAX_CHECKS} attempts). Do not call find-bug-origin; tell the user `
      + 'that no test reproducing the bug could be written, and why.';
  }
  let r;
  try {
    r = await remote('/check', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ commit: revision, test: `${testClass}::${testMethod}`, source: testSource }),
    });
  } catch (e) {
    r = { result: 'ERROR', output: String(e).slice(0, 300) };
  }
  checks.push({ at: new Date().toISOString(), fp: fingerprint(testSource), result: r.result,
    seconds: r.seconds, testClass, testMethod, testSource, output: (r.output || '').slice(-1500) });
  await kvs.set(`checks:${issueKey}`, checks);
  const left = MAX_CHECKS - checks.length;
  const head = {
    FAIL: 'FAIL: the test fails on the reported revision. Read the output: if it fails because of the '
      + 'wrong behaviour the report describes, call find-bug-origin with exactly this test source. If it '
      + 'fails for another reason (a mistake in the test itself), fix the test and check again.',
    PASS: 'PASS: the test passes on the reported revision, so it does NOT reproduce the bug. Re-read the '
      + 'report: use its exact inputs and the exact method it names, and assert what it says is wrong.',
    NOCOMPILE: 'NOCOMPILE: the test does not compile on the reported revision. Use only the API that '
      + 'exists there (listed below) and fix the errors shown.',
    ERROR: 'ERROR: the runner could not build or run this revision.',
  }[r.result] || `Unexpected result ${r.result}.`;
  return [head, `Attempts left: ${left}.`, `Output:\n${r.output || ''}`,
    ...(r.api ? [`Public API of the class under test at ${revision.slice(0, 10)}:\n${r.api.join('\n')}`] : [])]
    .join('\n\n');
}

/** Rovo action: validate the request, queue the job, return at once (actions have 55 s). */
export async function startBisect(payload) {
  const issueKey = payload.issueKey || payload.context?.jira?.issueKey;
  const { testClass, testMethod, testSource } = payload;
  if (!issueKey) return 'No issue key: open the agent from a Jira issue or pass issueKey.';
  const bad = validTest(payload);
  if (bad) return bad;
  // Only a test that was checked and failed on the reported revision may be bisected
  // (or one whose check could not run at all: the bisection validates it again anyway).
  const checks = (await kvs.get(`checks:${issueKey}`)) || [];
  const ok = checks.some((c) => c.fp === fingerprint(testSource) && ['FAIL', 'ERROR'].includes(c.result));
  if (!ok) {
    return 'Refused: call check-test with this exact test source first; only a test that fails on the '
      + 'reported revision can be bisected.';
  }
  const revision = await revisionOf(issueKey);
  if (!revision) {
    return `I could not find the revision the bug was reported against on ${issueKey}. `
      + 'Add a line "Revision: <commit sha>" to the description and ask again.';
  }
  const startedAt = new Date().toISOString();
  await kvs.set(`job:${issueKey}`, { status: 'queued', startedAt, testClass, testMethod, revision });
  await queue.push({ body: { issueKey, revision, testClass, testMethod, testSource, startedAt } });
  return `Started. Bug Origin will run the test on ${revision.slice(0, 10)} and bisect the history; `
    + `the result will be posted as a comment on ${issueKey} in a few minutes.`;
}

async function remote(path, init) {
  const res = await invokeRemote('runner', { path, ...init });
  const text = await res.text();
  if (!res.ok) throw new Error(`runner ${path} -> ${res.status} ${text.slice(0, 200)}`);
  return JSON.parse(text);
}

function describe(result, url) {
  const ev = Object.entries(result.evidence || {}).map(([c, s]) => `${c} ${s}`).join(', ');
  if (result.confidence === 'abstain') {
    return [`Bug Origin abstains: ${result.reason}.`, `Evidence (${result.runs} test runs): ${ev}`];
  }
  if (result.confidence === 'low') {
    return [
      `Bug Origin is not confident. The test first runs at commit ${result.answer.slice(0, 12)}, but ${result.reason}.`,
      'Treat this as a lower bound, not as the origin of the bug.',
      `Test: ${result.test}. ${result.runs} test runs in ${result.seconds} s. Evidence: ${ev}`,
    ];
  }
  const why = result.confidence === 'high'
    ? `The test passes on the commit before it (${result.previous_commit.slice(0, 12)}) and fails from this commit on.`
    : `The code under test did not exist before this commit (the test cannot compile on ${result.previous_commit.slice(0, 12)}), so the bug was born with it.`;
  return [
    `Bug Origin: the bug was most likely introduced by commit ${result.answer.slice(0, 12)} (confidence: ${result.confidence}).`,
    url + result.answer,
    why,
    `Test: ${result.test}. ${result.runs} test runs in ${result.seconds} s. Evidence: ${ev}`,
  ];
}

/** Queue consumer: hand the job to the runner, wait for it, post the outcome on the issue. */
export async function runJob(event) {
  const { issueKey, revision, testClass, testMethod, testSource, startedAt } = event.body;
  const bench = await kvs.get(`bench:${issueKey}`); // benchmark only: never shown to the agent
  try {
    const { id } = await remote('/jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        buggy: revision, fixed: bench?.fixed || '', test: `${testClass}::${testMethod}`, source: testSource,
      }),
    });
    const deadline = Date.now() + MAX_WAIT_MS;
    let job;
    do {
      await new Promise((r) => setTimeout(r, POLL_MS));
      job = await remote(`/jobs/${id}`, { method: 'GET' });
    } while (job.status === 'running' && Date.now() < deadline);
    const result = job.status === 'done' ? job.result
      : { confidence: 'abstain', reason: job.status === 'running' ? 'the bisection did not finish in time' : job.result?.error, evidence: {} };
    await kvs.set(`job:${issueKey}`, {
      status: 'done', startedAt, finishedAt: new Date().toISOString(), runnerJob: id,
      testClass, testMethod, testSource, revision, result,
    });
    await comment(issueKey, describe(result, 'https://github.com/apache/commons-lang/commit/'));
  } catch (e) {
    await kvs.set(`job:${issueKey}`, { status: 'error', startedAt, error: String(e), testClass, testMethod, testSource, revision });
    await comment(issueKey, [`Bug Origin could not finish: ${String(e).slice(0, 300)}`]);
  }
}

function reply(statusCode, body) {
  return { statusCode, headers: { 'Content-Type': ['application/json'] }, body: JSON.stringify(body) };
}

/**
 * Web trigger for the benchmark driver only. Requires header x-bench-token == BENCH_TOKEN.
 *   POST {op:"create", projectKey, summary, description, revision, fixed, caseId} -> {issueKey}
 *   POST {op:"result", issueKey} -> stored job record
 */
export async function benchmark(req) {
  const token = (req.headers['x-bench-token'] || [])[0];
  if (!process.env.BENCH_TOKEN || token !== process.env.BENCH_TOKEN) return reply(401, { error: 'unauthorised' });
  const body = JSON.parse(req.body || '{}');
  if (body.op === 'create') {
    if (!SHA.test(body.revision || '')) return reply(400, { error: 'revision' });
    const res = await api.asApp().requestJira(route`/rest/api/2/issue`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        fields: {
          project: { key: body.projectKey }, issuetype: { name: body.issueType || 'Bug' },
          summary: body.summary, description: body.description, labels: ['bug-origin-benchmark'],
        },
      }),
    });
    const created = await res.json();
    if (!res.ok) return reply(res.status, created);
    await api.asApp().requestJira(route`/rest/api/3/issue/${created.key}/properties/bug-origin`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ revision: body.revision, caseId: body.caseId }),
    });
    await kvs.set(`bench:${created.key}`, { caseId: body.caseId, fixed: body.fixed || '' });
    return reply(200, { issueKey: created.key });
  }
  if (body.op === 'result') {
    const job = (await kvs.get(`job:${body.issueKey}`)) || { status: 'none' };
    job.checks = (await kvs.get(`checks:${body.issueKey}`)) || [];
    // The Automation rule comments the agent's own reply; an agent that abstains starts no job,
    // so this comment is the only record of its decision.
    const res = await api.asApp().requestJira(
      route`/rest/api/2/issue/${body.issueKey}/comment?orderBy=created&maxResults=100`);
    if (res.ok) {
      const { comments } = await res.json();
      const r = (comments || []).find((c) => (c.body || '').startsWith('Bug Origin agent reply:'));
      if (r) job.agentReply = { created: r.created, text: r.body.slice(0, 4000) };
    }
    return reply(200, job);
  }
  return reply(400, { error: 'unknown op' });
}
