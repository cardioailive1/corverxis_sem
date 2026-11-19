const test = require('node:test'), assert = require('node:assert/strict');
const express = require('express');
const { createCollectRouter, readiness, recordUserFeedback } = require('./collectApi.js');
const { SPEC } = require('../simulators/specSimulator.js');

// Minimal in-memory stand-in for the two Prisma models the router uses.
function fakePrisma() {
  let n = 0; const contributors = [], cases = [];
  const match = (row, where = {}) => Object.entries(where).every(([k, v]) => row[k] === v);
  const dup = () => Object.assign(new Error('dup'), { code: 'P2002' });
  return {
    caseContributor: {
      create: async ({ data }) => { if (contributors.some(c => c.email === data.email || c.keyHash === data.keyHash)) throw dup(); const c = { id: 'u' + ++n, status: 'qualified', createdAt: new Date(), ...data }; contributors.push(c); return c; },
      findUnique: async ({ where }) => contributors.find(c => match(c, where)) || null,
      findMany: async () => contributors.slice(),
      update: async ({ where, data }) => { const c = contributors.find(x => match(x, where)); if (!c) throw new Error('nf'); Object.assign(c, data); return c; },
    },
    realCase: {
      create: async ({ data }) => { if (cases.some(c => c.caseHash === data.caseHash)) throw dup(); const c = { id: 'c' + ++n, reviewStatus: 'needs_review', reviewNotes: null, reviewedBy: null, screen: null, screenedAt: null, origin: 'manual', createdAt: new Date(), ...data }; cases.push(c); return c; },
      findUnique: async ({ where }) => cases.find(c => match(c, where)) || null,
      findMany: async ({ where } = {}) => cases.filter(c => match(c, where)),
      update: async ({ where, data }) => { const c = cases.find(x => match(x, where)); Object.assign(c, data); return c; },
    },
    _cases: cases,
  };
}
async function setup(env = {}, anthropic = null) {
  const prisma = fakePrisma(), app = express(); app.use(express.json());
  const router = createCollectRouter({ prisma, anthropic, env: { SEM_COLLECT_ADMIN_KEYS: 'ann=adminkey', SEM_COLLECT_INGEST_KEYS: 'tickets=ingestkey', ...env } });
  app.use('/api/collect', router);
  const srv = await new Promise(r => { const s = app.listen(0, () => r(s)); });
  const base = `http://127.0.0.1:${srv.address().port}/api/collect`;
  const call = (method, path, key, body) => fetch(base + path, { method, headers: { 'content-type': 'application/json', ...(key ? { 'x-api-key': key } : {}) }, body: body ? JSON.stringify(body) : undefined });
  return { srv, prisma, call, router, close: () => srv.close() };
}
const SLUG = 'cardiology-ecg-review', D = SPEC[SLUG];
const goodCase = (o = {}) => ({ domain: SLUG, signals: [D.signals[0], D.signals[1]], trueCause: D.causes[0], evidenceKind: 'confirmed_outcome',
  evidence: 'Confirmed by angiography after admission; cause matched the final report.', source: 'Registry A', occurredOn: '2025-03', checkedAllSignals: true, deidentified: true, ...o });
async function mkContributor(t, name, domains = [SLUG]) {
  const r = await t.call('POST', '/contributors', 'adminkey', { name, email: name + '@example.org', domains });
  assert.equal(r.status, 201); return r.json();
}

test('auth: missing/invalid key rejected; production without admin keys is 503', async () => {
  const t = await setup();
  assert.equal((await t.call('GET', '/domains')).status, 401);
  assert.equal((await t.call('GET', '/domains', 'nope')).status, 401);
  assert.equal((await t.call('GET', '/domains', 'adminkey')).status, 200);
  t.close();
  const p = await setup({ SEM_COLLECT_ADMIN_KEYS: '', NODE_ENV: 'production' });
  assert.equal((await p.call('GET', '/domains', 'x')).status, 503); p.close();
});

test('contributors: key shown once, only hash stored, scoped to their domains, suspension works', async () => {
  const t = await setup();
  const a = await mkContributor(t, 'alice');
  assert.match(a.access_key, /^sc_[0-9a-f]{48}$/);
  assert.ok(!JSON.stringify(await (await t.call('GET', '/contributors', 'adminkey')).json()).includes(a.access_key));
  assert.equal((await t.call('GET', '/contributors', a.access_key)).status, 403);
  const me = await (await t.call('GET', '/me', a.access_key)).json(); assert.equal(me.role, 'contributor'); assert.deepEqual(me.domains, [SLUG]);
  const doms = await (await t.call('GET', '/domains', a.access_key)).json(); assert.equal(doms.length, 1);
  assert.equal((await t.call('POST', '/contributors', 'adminkey', { name: 'x', email: 'alice@example.org', domains: [SLUG] })).status, 409);
  assert.equal((await t.call('POST', '/contributors', 'adminkey', { name: 'x', email: 'x@y.org', domains: ['nope'] })).status, 400);
  await t.call('POST', `/contributors/${a.id}/status`, 'adminkey', { status: 'suspended' });
  assert.equal((await t.call('GET', '/me', a.access_key)).status, 401);
  t.close();
});

test('submit: validation, attestations, identifier screen, dedupe, domain scope', async () => {
  const t = await setup(); const a = await mkContributor(t, 'alice'); const k = a.access_key;
  const post = (o) => t.call('POST', '/cases', k, goodCase(o));
  assert.equal((await post({})).status, 201);
  assert.equal((await post({})).status, 409);                                       // same case twice
  assert.equal((await post({ signals: ['bogus'] })).status, 400);
  assert.equal((await post({ trueCause: 'made_up', occurredOn: '2025-04' })).status, 400);
  assert.equal((await post({ evidence: 'short', occurredOn: '2025-05' })).status, 400);
  assert.equal((await post({ checkedAllSignals: false, occurredOn: '2025-06' })).status, 400);
  assert.equal((await post({ deidentified: false, occurredOn: '2025-07' })).status, 400);
  assert.equal((await post({ evidence: 'Confirmed; contact jane.doe@hospital.org for the record.', occurredOn: '2025-08' })).status, 400);
  assert.equal((await post({ evidence: 'Confirmed after test, MRN: 4481920 on file here.', occurredOn: '2025-09' })).status, 400);
  assert.equal((await post({ occurredOn: 'last week' })).status, 400);
  assert.equal((await post({ trueCause: 'other_not_listed', occurredOn: '2025-10' })).status, 400);                        // needs description
  assert.equal((await post({ trueCause: 'other_not_listed', otherCause: 'a rare channelopathy', occurredOn: '2025-10' })).status, 201);
  assert.equal((await t.call('POST', '/cases', k, goodCase({ domain: 'forex-trading' }))).status, 403);                    // not qualified
  assert.equal((await t.call('POST', '/cases', 'adminkey', goodCase({ occurredOn: '2025-11' }))).status, 403);              // admins do not author cases
  t.close();
});

test('review: second person only, domain-scoped, notes required to reject, export excludes unapproved and other', async () => {
  const t = await setup(); const a = await mkContributor(t, 'alice'), b = await mkContributor(t, 'bob'), c = await mkContributor(t, 'carol', ['forex-trading']);
  const id = (await (await t.call('POST', '/cases', a.access_key, goodCase())).json()).id;
  const id2 = (await (await t.call('POST', '/cases', a.access_key, goodCase({ occurredOn: '2025-04', trueCause: D.causes[1] }))).json()).id;
  const id3 = (await (await t.call('POST', '/cases', a.access_key, goodCase({ occurredOn: '2025-05', trueCause: 'other_not_listed', otherCause: 'something rare' }))).json()).id;
  assert.equal((await (await t.call('GET', '/review/queue', a.access_key)).json()).length, 0);          // not your own
  assert.equal((await (await t.call('GET', '/review/queue', c.access_key)).json()).length, 0);          // wrong domain
  assert.equal((await (await t.call('GET', '/review/queue', b.access_key)).json()).length, 3);
  assert.equal((await t.call('POST', `/cases/${id}/review`, a.access_key, { decision: 'approved' })).status, 403);
  assert.equal((await t.call('POST', `/cases/${id}/review`, c.access_key, { decision: 'approved' })).status, 403);
  assert.equal((await t.call('POST', `/cases/${id2}/review`, b.access_key, { decision: 'rejected' })).status, 400);
  assert.equal((await t.call('POST', `/cases/${id}/review`, b.access_key, { decision: 'approved' })).status, 200);
  assert.equal((await t.call('POST', `/cases/${id3}/review`, b.access_key, { decision: 'approved' })).status, 200);
  assert.equal((await t.call('POST', `/cases/${id2}/review`, b.access_key, { decision: 'needs_revision', notes: 'Which test confirmed it?' })).status, 200);
  assert.equal((await t.call('POST', `/cases/${id}/review`, b.access_key, { decision: 'rejected', notes: 'x' })).status, 409);   // approved is final
  const mine = await (await t.call('GET', '/cases/mine', a.access_key)).json();
  assert.equal(mine.find(x => x.id === id2).review_status, 'needs_revision');
  const csv = await (await t.call('GET', `/export/${SLUG}.csv`, 'adminkey')).text();
  const lines = csv.trim().split('\n'); assert.equal(lines[0], 'cause,signals,case_id'); assert.equal(lines.length, 2);
  assert.ok(lines[1].startsWith(D.causes[0] + ',' + D.signals[0] + ';' + D.signals[1] + ','));
  assert.equal((await t.call('GET', `/export/${SLUG}.csv`, b.access_key)).status, 403);                // export is admin only
  const prog = (await (await t.call('GET', '/progress', 'adminkey')).json()).find(x => x.slug === SLUG);
  assert.equal(prog.approved, 1); assert.equal(prog.other_not_listed, 1); assert.equal(prog.ready_to_calibrate, false);
  t.close();
});

test('readiness: 22 approved per cause and 20 x causes overall are required', async () => {
  const fake = [];
  D.causes.forEach(c => { for (let i = 0; i < 22; i++) fake.push({ trueCause: c }); });
  assert.equal(readiness(SLUG, fake).ready_to_calibrate, true);
  assert.equal(readiness(SLUG, fake.slice(1)).ready_to_calibrate, false);   // one cause at 21
  assert.equal(readiness(SLUG, fake.slice(0, 20 * D.causes.length)).ready_to_calibrate, false);
});

const row = (o = {}) => ({ domain: SLUG, signals: [D.signals[2]], trueCause: D.causes[2], evidenceKind: 'test_or_inspection', evidence: 'Inspection report confirmed this cause after the event.', occurredOn: '2025-02', source: 'Ticketing', ...o });
const envelope = (cases, o = {}) => ({ attest_deidentified: true, signals_complete: true, cases, ...o });

test('ingest: ingest key only reaches /ingest; attestations required; per-row errors; dedupe; still needs human review', async () => {
  const t = await setup();
  const ing = (body, key = 'ingestkey') => t.call('POST', '/ingest', key, body);
  assert.equal((await ing(envelope([row()]), 'nope')).status, 401);
  assert.equal((await ing({ cases: [row()] })).status, 400);                                        // no attestation
  assert.equal((await ing(envelope([]))).status, 400);
  assert.equal((await ing(envelope(Array(201).fill(row())))).status, 400);                          // cap
  const r = await (await ing(envelope([row(), row(), row({ occurredOn: '2025-03', signals: ['bogus'] }), row({ occurredOn: '2025-04', evidence: 'Mail bob@corp.com about it, confirmed by test.' }), row({ occurredOn: '2025-05' })]))).json();
  assert.equal(r.created, 2); assert.equal(r.duplicates, 1); assert.equal(r.rejected.length, 2); assert.deepEqual(r.rejected.map(x => x.index), [2, 3]);
  const stored = t.prisma._cases; assert.equal(stored.length, 2);
  assert.ok(stored.every(c => c.origin === 'ingest' && c.ingestSource === 'tickets' && c.contributorId === null && c.reviewStatus === 'needs_review'));
  // an ingest key cannot read, review, export or administer
  for (const [m, path] of [['GET', '/domains'], ['GET', '/progress'], ['GET', `/export/${SLUG}.csv`], ['GET', '/contributors'], ['POST', '/screen']]) {
    const x = await t.call(m, path, 'ingestkey', m === 'POST' ? {} : undefined);
    assert.ok([200, 403].includes(x.status) && !(path === '/domains' && (await x.json()).length), path);
  }
  assert.equal((await t.call('POST', `/cases/${stored[0].id}/review`, 'ingestkey', { decision: 'approved' })).status, 403);
  // a contributor can review it, and only then does it count
  const a = await mkContributor(t, 'alice');
  const q = await (await t.call('GET', '/review/queue', a.access_key)).json(); assert.equal(q.length, 2); assert.equal(q[0].origin, 'ingest');
  assert.equal((await t.call('POST', `/cases/${q[0].id}/review`, a.access_key, { decision: 'approved' })).status, 200);
  assert.equal((await (await t.call('GET', '/progress', 'adminkey')).json()).find(x => x.slug === SLUG).approved, 1);
  assert.equal((await t.call('POST', '/ingest', a.access_key, envelope([row({ occurredOn: '2025-06' })]))).status, 403);   // contributors use the form
  t.close();
});

test('screen: flags weak cases, never approves or rejects, tolerates failures, only unscreened waiting cases', async () => {
  let calls = 0, fail = false;
  const anthropic = { messages: { create: async req => { calls++; if (fail) throw new Error('down');
    return { content: [{ text: /Stated cause: .*\n/.test(req.messages[0].content) && /wrong/.test(req.messages[0].content) ? '{"consistent":0.2,"flagged":true,"reasons":["Evidence describes a different cause."]}' : '{"consistent":0.9,"flagged":false,"reasons":[]}' }] }; } } };
  const t = await setup({}, anthropic);
  const longEv = 'Inspection report and a follow-up test both confirmed this cause after the event, and the fix removed the problem.';
  await t.call('POST', '/ingest', 'ingestkey', envelope([row({ evidence: longEv }), row({ occurredOn: '2025-03', evidence: longEv + ' This is the wrong explanation entirely, nothing matches.' }), row({ occurredOn: '2025-04', evidenceKind: 'expert_judgement', evidence: longEv })]));
  await new Promise(r => setTimeout(r, 50));                                              // ingest kicks a background screen
  const cs = t.prisma._cases; assert.equal(cs.length, 3);
  assert.ok(cs.every(c => c.screenedAt && c.reviewStatus === 'needs_review'));            // screened, still waiting for a human
  assert.equal(cs[0].screen.flagged, false); assert.equal(cs[1].screen.flagged, true); assert.equal(cs[2].screen.flagged, true);
  assert.match(cs[2].screen.reasons[0], /Expert judgement/);
  const before = calls; assert.deepEqual(await t.router.runScreening(), { screened: 0, flagged: 0 }); assert.equal(calls, before);   // nothing new to screen
  const a = await mkContributor(t, 'alice'); const q = await (await t.call('GET', '/review/queue', a.access_key)).json();
  assert.equal(q[0].screen.flagged, true);                                                // flagged cases come first
  await t.call('POST', '/ingest', 'ingestkey', envelope([row({ occurredOn: '2025-05', evidence: longEv })])); await new Promise(r => setTimeout(r, 20));
  fail = true; await t.call('POST', '/ingest', 'ingestkey', envelope([row({ occurredOn: '2025-07' })])); await new Promise(r => setTimeout(r, 20));
  assert.equal(cs[cs.length - 1].screenedAt, null);                                       // failure leaves it for the next pass
  assert.equal((await t.call('POST', '/screen', a.access_key, {})).status, 403);
  t.close();
  const none = await setup(); assert.equal((await none.call('POST', '/screen', 'adminkey', {})).status, 503); none.close();
});

test('feedback: stored unverified, excluded from review, export and readiness; gives an agreement rate', async () => {
  const t = await setup(); const p = t.prisma;
  assert.deepEqual(await recordUserFeedback(p, { domain: SLUG, signals: [D.signals[0]], answer: D.causes[0], outcome: 'correct' }), { stored: true });
  assert.deepEqual(await recordUserFeedback(p, { domain: SLUG, signals: [D.signals[0]], answer: D.causes[0], outcome: 'incorrect', actualCause: D.causes[1] }), { stored: true });
  assert.deepEqual(await recordUserFeedback(p, { domain: SLUG, signals: [], answer: D.causes[0], outcome: 'unsure' }), { stored: false });
  assert.ok((await recordUserFeedback(p, { domain: SLUG, signals: [], answer: D.causes[0], outcome: 'incorrect' })).error);        // needs actual cause
  assert.ok((await recordUserFeedback(p, { domain: SLUG, signals: ['bogus'], answer: D.causes[0], outcome: 'correct' })).error);
  assert.equal(p._cases.length, 2); assert.ok(p._cases.every(c => c.reviewStatus === 'unverified' && c.origin === 'product_feedback'));
  const a = await mkContributor(t, 'alice');
  assert.equal((await (await t.call('GET', '/review/queue', a.access_key)).json()).length, 0);
  const csv = await (await t.call('GET', `/export/${SLUG}.csv`, 'adminkey')).text(); assert.equal(csv.trim().split('\n').length, 1);
  const prog = (await (await t.call('GET', '/progress', 'adminkey')).json()).find(x => x.slug === SLUG);
  assert.equal(prog.approved, 0); assert.equal(prog.user_reports, 2); assert.equal(prog.user_report_agreement, 0.5);
  t.close();
});
