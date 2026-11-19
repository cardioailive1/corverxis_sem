const test = require('node:test'), assert = require('node:assert/strict');
const http = require('http');
const express = require('express');
const P = require('./productApi.js');
const { createVision, parseMedia, sanitize } = require('./vision.js');

// Only the leading bytes are inspected by the server, so small fake bodies with real magic numbers are enough here.
const pad = Buffer.alloc(40, 7);
const durl = (head, type) => `data:${type};base64,${Buffer.concat([head, pad]).toString('base64')}`;
const JPG = durl(Buffer.from([0xff, 0xd8, 0xff, 0xe0]), 'image/jpeg'), PNG = durl(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a]), 'image/png');
const WEBP = durl(Buffer.concat([Buffer.from('RIFF'), Buffer.from([1, 2, 3, 4]), Buffer.from('WEBP')]), 'image/webp');
const answer = o => JSON.stringify(o);
const GOOD = answer({ domain: 'agriculture-crop-health', signals: [{ name: 'leaf_spots', evidence: 'brown circular spots' }, { name: 'leaf_yellowing', evidence: 'yellow halos' }, { name: 'made_up_signal' }, { name: 'leaf_spots' }, { name: 'ed_boarding_hours_rising' }], description: 'A leaf with brown spots.', image_quality: 'good' });

test('parseMedia: accepts real JPEG/PNG/WebP, rejects wrong type, spoofed bytes, too many, too large', () => {
  assert.equal(parseMedia([JPG, PNG, WEBP]).images.length, 3);
  assert.ok(parseMedia([]).error); assert.ok(parseMedia('x').error);
  assert.ok(parseMedia(['data:image/gif;base64,AAAA']).error);
  assert.ok(parseMedia(['data:text/html;base64,PGI+']).error);
  assert.ok(parseMedia([`data:image/jpeg;base64,${Buffer.from('this is not a jpeg at all').toString('base64')}`]).error);   // bytes do not match
  assert.ok(parseMedia(Array(9).fill(JPG)).error);
  assert.ok(parseMedia([`data:image/jpeg;base64,/9j/${'A'.repeat(2_200_000)}`]).error);
});

test('sanitize: only the domain\'s own signals, deduped, no cause leaks through', () => {
  const o = sanitize(JSON.parse(GOOD), 'agriculture-crop-health');
  assert.deepEqual(o.signals.map(s => s.name), ['leaf_spots', 'leaf_yellowing']);
  assert.equal(sanitize({ domain: 'nope', signals: [{ name: 'leaf_spots' }] }, null).signals.length, 0);
  assert.equal(sanitize({ domain: 'agriculture-crop-health', signals: [{ name: 'leaf_spots' }], cause: 'fungal_leaf_spot' }, null).cause, undefined);
  assert.equal(sanitize('junk'), null);
});

test('server provider: OpenAI-style image_url parts, labelled sem-vision, auth header, domain fixed', async () => {
  let seen = null, auth = null;
  const srv = await new Promise(r => { const s = http.createServer((req, res) => { let b = ''; req.on('data', d => b += d); req.on('end', () => { seen = JSON.parse(b); auth = req.headers.authorization; res.setHeader('content-type', 'application/json'); res.end(JSON.stringify({ choices: [{ message: { content: GOOD } }] })); }); }).listen(0, () => r(s)); });
  const v = createVision({ anthropic: null, env: { SEM_VISION_URL: `http://127.0.0.1:${srv.address().port}`, SEM_VISION_API_KEY: 'sek', SEM_VISION_MODEL: 'Qwen/Qwen3.8-27B' } });
  const r = await v.analyze({ domain: 'agriculture-crop-health', media: [JPG, PNG], note: 'tomato leaf', source: 'video' });
  assert.equal(r.status, 200); assert.equal(r.body.provider, 'sem-vision'); assert.equal(r.body.source, 'video'); assert.equal(r.body.images_used, 2);
  assert.deepEqual(r.body.signals.map(s => s.name), ['leaf_spots', 'leaf_yellowing']); assert.equal(r.body.cause, undefined);
  assert.equal(auth, 'Bearer sek'); assert.equal(seen.model, 'Qwen/Qwen3.8-27B');
  const parts = seen.messages[1].content; assert.equal(parts.filter(p => p.type === 'image_url').length, 2);
  assert.match(seen.messages[0].content, /frames sampled in order from a video/);
  assert.ok(!seen.messages[0].content.includes('ed_boarding_hours_rising'));              // fixed domain: other domains' signals not offered
  srv.close();
});

test('claude fallback: image blocks, labelled claude-fallback, auto-detects domain; failure and junk handled', async () => {
  let seen = null; let mode = 'ok';
  const anthropic = { messages: { create: async req => { seen = req; if (mode === 'throw') throw new Error('x'); return { content: [{ text: mode === 'junk' ? 'sorry I cannot' : GOOD }] }; } } };
  const v = createVision({ anthropic, env: {} });
  const r = await v.analyze({ media: [WEBP] });
  assert.equal(r.status, 200); assert.equal(r.body.provider, 'claude-fallback'); assert.equal(r.body.domain, 'agriculture-crop-health'); assert.equal(r.body.domain_name, 'Agriculture & Crop Health');
  assert.equal(seen.messages[0].content[0].type, 'image'); assert.equal(seen.messages[0].content[0].source.media_type, 'image/webp');
  assert.match(seen.system, /agriculture-crop-health/); assert.match(seen.system, /hospital-operations/);   // all domains offered when none chosen
  mode = 'junk'; assert.equal((await v.analyze({ media: [JPG] })).status, 502);
  mode = 'throw'; assert.equal((await v.analyze({ media: [JPG] })).status, 502);
  assert.equal((await createVision({ anthropic: null, env: {} }).analyze({ media: [JPG] })).status, 503);
  assert.equal((await v.analyze({ domain: 'nope', media: [JPG] })).status, 400);
  assert.equal((await v.analyze({ media: [JPG], note: 'x'.repeat(501) })).status, 400);
});

test('route /analyze-media: needs a key, validates, and /model reports vision_configured', async () => {
  const anthropic = { messages: { create: async () => ({ content: [{ text: GOOD }] }) } };
  const app = express(); app.use(express.json({ limit: '5mb' }));
  app.use('/api/product', P.createProductRouter({ prisma: { semCheckpoint: { findFirst: async () => null } }, anthropic, env: { SEM_PRODUCT_API_KEYS: 'k1' } }));
  const srv = await new Promise(r => { const s = app.listen(0, () => r(s)); }), base = `http://127.0.0.1:${srv.address().port}/api/product`;
  const post = (body, key) => fetch(base + '/analyze-media', { method: 'POST', headers: { 'content-type': 'application/json', ...(key ? { 'x-api-key': key } : {}) }, body: JSON.stringify(body) });
  assert.equal((await post({ media: [JPG] })).status, 401);
  assert.equal((await post({ media: [] }, 'k1')).status, 400);
  const ok = await post({ domain: 'agriculture-crop-health', media: [JPG] }, 'k1'); assert.equal(ok.status, 200);
  assert.equal((await ok.json()).signals.length, 2);
  assert.equal((await (await fetch(base + '/model', { headers: { 'x-api-key': 'k1' } })).json()).vision_configured, true);
  srv.close();
});

test('/diagnose-media: reads the image, then names the cause; refuses when the image gives too little', async () => {
  let visionAnswer = GOOD;
  const anthropic = { messages: { create: async req => {
    if (Array.isArray(req.messages[0].content)) return { content: [{ text: visionAnswer }] };                    // the vision call
    return { content: [{ text: '{"stress_cause": "fungal_leaf_spot"}' }] }; } } };                              // the SI-SEM fallback diagnosis
  const app = express(); app.use(express.json({ limit: '5mb' }));
  app.use('/api/product', P.createProductRouter({ prisma: { semCheckpoint: { findFirst: async () => null } }, anthropic, env: { SEM_PRODUCT_API_KEYS: 'k1' } }));
  const srv = await new Promise(r => { const s = app.listen(0, () => r(s)); }), base = `http://127.0.0.1:${srv.address().port}/api/product`;
  const post = (body, key = 'k1') => fetch(base + '/diagnose-media', { method: 'POST', headers: { 'content-type': 'application/json', 'x-api-key': key }, body: JSON.stringify(body) });
  assert.equal((await post({ media: [JPG] }, 'bad')).status, 401);
  const ok = await (await post({ media: [JPG, PNG], source: 'photo' })).json();
  assert.equal(ok.diagnosis.answer, 'fungal_leaf_spot'); assert.equal(ok.diagnosis.domain, 'agriculture-crop-health');
  assert.deepEqual(ok.diagnosis.signals, ['leaf_yellowing', 'leaf_spots'].sort((a, b) => ok.diagnosis.signals.indexOf(a) - ok.diagnosis.signals.indexOf(b)));
  assert.equal(ok.diagnosis.basis, 'image'); assert.match(ok.diagnosis.basis_note, /little to go on/);          // only 2 signs
  assert.ok(ok.diagnosis.actions && ok.diagnosis.reference_probabilities.length > 0); assert.equal(ok.read.signals.length, 2);
  visionAnswer = answer({ domain: 'agriculture-crop-health', signals: [], description: 'A blurry picture.', image_quality: 'unusable' });
  const bad = await (await post({ media: [JPG] })).json(); assert.equal(bad.diagnosis, null); assert.match(bad.reason, /too unclear/);
  visionAnswer = answer({ domain: 'agriculture-crop-health', signals: [{ name: 'not_a_signal' }], description: 'A leaf.', image_quality: 'good' });
  const none = await (await post({ media: [JPG] })).json(); assert.equal(none.diagnosis, null); assert.match(none.reason, /could not see any/);
  visionAnswer = answer({ domain: null, signals: [], description: 'A car.', image_quality: 'good' });
  assert.match((await (await post({ media: [JPG] })).json()).reason, /could not tell which area/);
  assert.equal((await post({ media: [] })).status, 400);
  srv.close();
});
