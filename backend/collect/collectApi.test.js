const test = require('node:test'), assert = require('node:assert/strict');
const express = require('express');
const { createCollectRouter, readiness } = require('./collectApi.js');
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
      create: async ({ data }) => { if (cases.some(c => c.caseHash === data.caseHash)) throw dup(); const c = { id: 'c' + ++n, reviewStatus: 'needs_review', reviewNotes: null, reviewedBy: null, createdAt: new Date(), ...data }; cases.push(c); return c; },
      findUnique: async ({ where }) => cases.find(c => match(c, where)) || null,
      findMany: async ({ where } = {}) => cases.filter(c => match(c, where)),
      update: async ({ where, data }) => { const c = cases.find(x => match(x, where)); Object.assign(c, data); return c; },
    },
    _cases: cases,
  };
}
async function setup(env = {}) {
  const prisma = fakePrisma(), app = express(); app.use(express.json());
  app.use('/api/collect', createCollectRouter({ prisma, env: { SEM_COLLECT_ADMIN_KEYS: 'ann=adminkey', ...env } }));
  const srv = await new Promise(r => { const s = app.listen(0, () => r(s)); });
  const base = `http://127.0.0.1:${srv.address().port}/api/collect`;
  const call = (method, path, key, body) => fetch(base + path, { method, headers: { 'content-type': 'application/json', ...(key ? { 'x-api-key': key } : {}) }, body: body ? JSON.stringify(body) : undefined });
  return { srv, prisma, call, close: () => srv.close() };
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
