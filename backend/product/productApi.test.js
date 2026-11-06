// Run: node --test product/productApi.test.js   (from backend/)
const test = require('node:test'), assert = require('node:assert/strict');
const http = require('http'), express = require('express');
const P = require('./productApi.js');

const listen = app => new Promise(r => { const s = app.listen(0, () => r(s)); });
const jpost = (base, path, body, key) => fetch(base + path, { method: 'POST', headers: { 'content-type': 'application/json', ...(key ? { 'x-api-key': key } : {}) }, body: JSON.stringify(body) });

async function setup({ env = {}, checkpoint = null, anthropic = null } = {}) {
  const prisma = { semCheckpoint: { findFirst: async () => checkpoint } };
  const app = express(); app.use(express.json());
  app.use('/api/product', P.createProductRouter({ prisma, anthropic, env: { SEM_PRODUCT_API_KEYS: 'k1,k2', ...env } }));
  const srv = await listen(app);
  return { srv, base: `http://127.0.0.1:${srv.address().port}/api/product` };
}
// a fake OpenAI-compatible model server; `reply(prompt)` returns the text
async function fakeModel(reply) {
  const prompts = [];
  const app = express(); app.use(express.json());
  app.post('/v1/completions', (req, res) => { prompts.push(req.body.prompt); res.json({ choices: [{ text: reply(req.body.prompt) }] }); });
  const srv = await listen(app);
  return { srv, prompts, url: `http://127.0.0.1:${srv.address().port}` };
}
const CK = { id: 'c1', version: 'sem-v1', baseModel: 'Qwen/Qwen3.8-27B', meanReward: 0.71 };

test('auth: missing, wrong and valid keys', async () => {
  const { srv, base } = await setup();
  assert.equal((await fetch(base + '/domains')).status, 401);
  assert.equal((await fetch(base + '/domains', { headers: { 'x-api-key': 'nope' } })).status, 401);
  const ok = await fetch(base + '/domains', { headers: { authorization: 'Bearer k2' } });
  assert.equal(ok.status, 200);
  const d = await ok.json(); assert.equal(d.length, 6);
  assert.ok(d.every(x => x.options.length >= 4 && x.signals.length >= 5 && !x.profiles));
  srv.close();
});

test('production refuses to serve without configured keys; dev is open', async () => {
  let s = await setup({ env: { SEM_PRODUCT_API_KEYS: '', NODE_ENV: 'production' } });
  assert.equal((await fetch(s.base + '/domains')).status, 503); s.srv.close();
  s = await setup({ env: { SEM_PRODUCT_API_KEYS: '' } });
  assert.equal((await fetch(s.base + '/domains')).status, 200); s.srv.close();
});

test('rate limit returns 429', async () => {
  const { srv, base } = await setup({ env: { SEM_PRODUCT_RATE_LIMIT_PER_MIN: '3' } });
  const codes = []; for (let i = 0; i < 5; i++) codes.push((await fetch(base + '/domains', { headers: { 'x-api-key': 'k1' } })).status);
  assert.deepEqual(codes, [200, 200, 200, 429, 429]); srv.close();
});

test('diagnose: served by the active SEM checkpoint with the training-format prompt', async () => {
  const m = await fakeModel(() => '{"condition": "influenza"}');
  const { srv, base } = await setup({ checkpoint: CK, env: { SEM_INFERENCE_URL: m.url } });
  const r = await (await jpost(base, '/diagnose', { domain: 'medical-diagnostics', signals: ['body_aches', 'fever_high', 'fatigue'] }, 'k1')).json();
  assert.equal(r.answer, 'influenza'); assert.equal(r.served_by, 'sem-checkpoint');
  assert.equal(r.checkpoint.version, 'sem-v1'); assert.equal(r.checkpoint.held_out_mean_reward, 0.71);
  assert.equal(r.agrees_with_reference, true); assert.ok(r.caution);
  assert.equal(m.prompts[0], P.buildPrompt('medical-diagnostics', ['fever_high', 'body_aches', 'fatigue']));
  assert.ok(m.prompts[0].includes('Observed signals: fever_high, body_aches, fatigue.'));   // canonical order, not click order
  assert.ok(Math.abs(r.reference_probabilities.reduce((a, x) => a + x.probability, 0) - 1) < 1e-3);
  srv.close(); m.srv.close();
});

test('diagnose: JSON wrapped in prose still parses; out-of-list answer is reported, not 500', async () => {
  let m = await fakeModel(() => 'Sure! {"condition": "covid19"} Hope that helps.');
  let s = await setup({ checkpoint: CK, env: { SEM_INFERENCE_URL: m.url } });
  assert.equal((await (await jpost(s.base, '/diagnose', { domain: 'medical-diagnostics', signals: [] }, 'k1')).json()).answer, 'covid19');
  s.srv.close(); m.srv.close();
  m = await fakeModel(() => '{"condition": "the plague"}');
  s = await setup({ checkpoint: CK, env: { SEM_INFERENCE_URL: m.url } });
  const resp = await jpost(s.base, '/diagnose', { domain: 'medical-diagnostics', signals: ['fever_high'] }, 'k1');
  const r = await resp.json(); assert.equal(resp.status, 200); assert.equal(r.valid, false); assert.equal(r.answer, null); assert.ok(r.error);
  s.srv.close(); m.srv.close();
});

test('fallback to Claude is labelled and never claims to be SEM', async () => {
  const anthropic = { messages: { create: async () => ({ content: [{ text: '{"failed_component": "bearing"}' }] }) } };
  const { srv, base } = await setup({ anthropic });   // no checkpoint, no endpoint
  const r = await (await jpost(base, '/diagnose', { domain: 'industrial-fault-diagnosis', signals: ['vibration_high', 'noise_abnormal'] }, 'k1')).json();
  assert.equal(r.served_by, 'claude-fallback'); assert.equal(r.checkpoint, null); assert.match(r.note, /No SI-SEM checkpoint/); assert.equal(r.answer, 'bearing');
  srv.close();
});

test('endpoint failure falls back; with fallback disabled returns 503', async () => {
  const anthropic = { messages: { create: async () => ({ content: [{ text: '{"cause": "account_takeover"}' }] }) } };
  let s = await setup({ checkpoint: CK, anthropic, env: { SEM_INFERENCE_URL: 'http://127.0.0.1:1' } });
  let r = await (await jpost(s.base, '/diagnose', { domain: 'financial-fraud-investigation', signals: ['geo_mismatch'] }, 'k1')).json();
  assert.equal(r.served_by, 'claude-fallback'); assert.match(r.note, /endpoint failed/); s.srv.close();
  s = await setup({ checkpoint: CK, anthropic, env: { SEM_INFERENCE_URL: 'http://127.0.0.1:1', SEM_PRODUCT_ALLOW_FALLBACK: 'false' } });
  assert.equal((await jpost(s.base, '/diagnose', { domain: 'financial-fraud-investigation', signals: [] }, 'k1')).status, 503); s.srv.close();
});

test('input validation', async () => {
  const { srv, base } = await setup();
  for (const body of [{ domain: 'nope', signals: [] }, { domain: 'medical-diagnostics', signals: 'fever_high' },
                      { domain: 'medical-diagnostics', signals: ['not_a_signal'] }, { domain: 'medical-diagnostics', signals: [3] }, {}]) {
    assert.equal((await jpost(base, '/diagnose', body, 'k1')).status, 400, JSON.stringify(body));
  }
  srv.close();
});

test('hf and runpod response shapes are parsed', async () => {
  const app = express(); app.use(express.json());
  app.post('/hf', (q, r) => r.json([{ generated_text: '{"cause":"synthetic_identity"}' }]));
  app.post('/rp/runsync', (q, r) => r.json({ status: 'COMPLETED', output: [{ choices: [{ text: '{"cause":"merchant_collusion"}' }] }] }));
  const srv = await listen(app), u = `http://127.0.0.1:${srv.address().port}`;
  assert.match(await P.callServedModel('p', { SEM_INFERENCE_URL: u + '/hf', SEM_INFERENCE_KIND: 'hf' }), /synthetic_identity/);
  assert.match(await P.callServedModel('p', { SEM_INFERENCE_URL: u + '/rp', SEM_INFERENCE_KIND: 'runpod', RUNPOD_API_KEY: 'x' }), /merchant_collusion/);
  srv.close();
});

test('print every domain prompt for cross-language parity check', () => {
  // consumed by training/grpo parity test; also asserts shape
  const out = {};
  for (const slug of Object.keys(P.DOMAIN_META)) {
    const d = P.domainInfo(slug), n = d.signals.length, list = [];
    for (let mask = 0; mask < (1 << n); mask++) {
      const present = d.signals.filter((_, i) => mask & (1 << i));
      list.push({ present, prompt: P.buildPrompt(slug, present) });
    }
    out[slug] = list;
  }
  if (process.env.PARITY_OUT) require('fs').writeFileSync(process.env.PARITY_OUT, JSON.stringify(out));
  assert.equal(Object.keys(out).length, 6);
});
