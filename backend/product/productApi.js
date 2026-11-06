// SI-SEM Product API — the customer-facing surface, deliberately separate from the Lab API.
//
// Mounted at /api/product by server.js. The Lab UI never calls these routes and the
// product UI never calls the Lab's routes. What it does:
//   * lists the diagnostic domains the SI-SEM model was trained on
//   * POST /diagnose builds the EXACT prompt format used in GRPO training
//     (training/grpo/dataset.py build_prompt), sends it to the model that is
//     currently served, and returns the answer plus context
//
// Auth: access keys in SEM_PRODUCT_API_KEYS (comma separated), sent as `x-api-key` or
// `Authorization: Bearer`. If the variable is unset the API refuses to serve in production.
const crypto = require('crypto');
const express = require('express');

const sim = {
  'industrial-fault-diagnosis': require('../simulators/industrialFaultSimulator.js'),
  'medical-diagnostics': require('../simulators/medicalDiagnosticsSimulator.js'),
  'security-incident-investigation': require('../simulators/securityIncidentSimulator.js'),
  'financial-fraud-investigation': require('../simulators/financialFraudSimulator.js'),
  'scientific-discovery': require('../simulators/scientificDiscoverySimulator.js'),
  'production-incident-rootcause': require('../simulators/productionIncidentSimulator.js'),
};

// label and key MUST match training/grpo/dataset.py DOMAIN_INSTRUCTIONS exactly.
const DOMAIN_META = {
  'industrial-fault-diagnosis':     { name: 'Industrial Fault Diagnosis',          label: 'industrial fault diagnosis',      key: 'failed_component', options: s => s.COMPONENTS,     def: 0.05, caution: null },
  'medical-diagnostics':            { name: 'Medical Diagnostics',                 label: 'medical diagnostics',             key: 'condition',        options: s => s.CONDITIONS,     def: 0.03, caution: 'Decision support only. This is not a medical diagnosis. Consult a qualified clinician.' },
  'security-incident-investigation':{ name: 'Security Incident Investigation',     label: 'security incident investigation', key: 'attack_vector',    options: s => s.ATTACK_VECTORS, def: 0.03, caution: null },
  'financial-fraud-investigation':  { name: 'Financial Fraud Investigation',       label: 'financial fraud investigation',   key: 'cause',            options: s => s.CAUSES,         def: 0.02, caution: null },
  'scientific-discovery':           { name: 'Scientific Discovery',                label: 'scientific discovery',            key: 'mechanism',        options: s => s.MECHANISMS,     def: 0.05, caution: null },
  'production-incident-rootcause':  { name: 'Production Incident Root-Causing',    label: 'production incident root-causing',key: 'root_cause',       options: s => s.ROOT_CAUSES,    def: 0.03, caution: null },
};

function domainInfo(slug) {
  const m = DOMAIN_META[slug], s = sim[slug];
  return {
    slug, name: m.name, label: m.label, key: m.key, caution: m.caution, defaultP: m.def,
    options: m.options(s),
    signals: s.ALL_SYMPTOMS || s.ALL_SIGNALS,
    profiles: s.SYMPTOM_PROFILES || s.SIGNAL_PROFILES,
  };
}

// Byte-for-byte the same text as dataset.py build_prompt. Signals are emitted in the
// simulator's canonical order, as they are during training.
function buildPrompt(slug, presentSignals) {
  const d = domainInfo(slug);
  const present = d.signals.filter(s => presentSignals.includes(s));
  const text = present.length ? present.join(', ') : 'no significant signals — all readings normal';
  return `You are performing ${d.label}. Possible causes: ${d.options.join(', ')}. Observed signals: ${text}. ` +
    `Propose the single most likely cause. Respond with ONLY a JSON object in the form {"${d.key}": "<your answer>"}, nothing else.`;
}

// Reference probabilities from the simulator's own model (uniform prior). Context for the
// user, NOT the model's confidence.
function referencePosterior(slug, presentSignals) {
  const d = domainInfo(slug);
  const lls = d.options.map(c => d.signals.reduce((ll, s) => {
    const p = d.profiles[c][s] ?? d.defaultP;
    return ll + Math.log(presentSignals.includes(s) ? p : 1 - p);
  }, 0));
  const max = Math.max(...lls), exps = lls.map(l => Math.exp(l - max)), tot = exps.reduce((a, b) => a + b, 0);
  return d.options.map((c, i) => ({ cause: c, probability: +(exps[i] / tot).toFixed(4) })).sort((a, b) => b.probability - a.probability);
}

function parseAnswer(text, key, options) {
  let obj = null;
  const t = (text || '').trim();
  try { obj = JSON.parse(t); } catch { const m = t.match(/\{[^{}]*\}/); if (m) { try { obj = JSON.parse(m[0]); } catch { /* fall through */ } } }
  const v = obj && typeof obj === 'object' ? obj[key] : undefined;
  return options.includes(v) ? v : null;
}

// ── Model serving ─────────────────────────────────────────────────────────
// SEM_INFERENCE_KIND: openai (default, vLLM etc: POST {url}/v1/completions, raw prompt, as in
// training) | hf (HF Inference Endpoint) | runpod (Serverless: /runsync then /status polling).
// The openai kind is the best fit. hf and runpod worker response shapes vary, so they parse defensively.
async function callServedModel(prompt, env = process.env) {
  const url = (env.SEM_INFERENCE_URL || '').replace(/\/$/, '');
  if (!url) return null;
  const kind = (env.SEM_INFERENCE_KIND || 'openai').toLowerCase();
  const timeout = Number(env.SEM_INFERENCE_TIMEOUT_MS || 60000);
  const post = (u, body, key) => fetch(u, { method: 'POST', signal: AbortSignal.timeout(timeout),
    headers: { 'content-type': 'application/json', ...(key ? { authorization: `Bearer ${key}` } : {}) }, body: JSON.stringify(body) });
  const must = async r => { if (!r.ok) throw new Error(`inference endpoint HTTP ${r.status}`); return r.json(); };

  if (kind === 'hf') {
    const j = await must(await post(url, { inputs: prompt, parameters: { max_new_tokens: 64, temperature: 0.01, return_full_text: false } }, env.HF_API_TOKEN));
    return (Array.isArray(j) ? j[0]?.generated_text : j.generated_text) || '';
  }
  if (kind === 'runpod') {
    const key = env.RUNPOD_API_KEY;
    let j = await must(await post(`${url}/runsync`, { input: { prompt, max_tokens: 64, temperature: 0, sampling_params: { max_tokens: 64, temperature: 0 } } }, key));
    for (let i = 0; i < 30 && ['IN_QUEUE', 'IN_PROGRESS'].includes(j.status); i++) {
      await new Promise(r => setTimeout(r, 2000));
      j = await must(await fetch(`${url}/status/${j.id}`, { headers: { authorization: `Bearer ${key}` }, signal: AbortSignal.timeout(timeout) }));
    }
    if (j.status && j.status !== 'COMPLETED') throw new Error(`runpod job ${j.status}`);
    const o = j.output;
    if (typeof o === 'string') return o;
    const first = Array.isArray(o) ? o[0] : o;
    return first?.choices?.[0]?.text ?? first?.choices?.[0]?.tokens?.join('') ?? first?.text ?? first?.generated_text ?? '';
  }
  const j = await must(await post(`${url}/v1/completions`, { model: env.SEM_INFERENCE_MODEL || 'default', prompt, max_tokens: 64, temperature: 0 }, env.SEM_INFERENCE_API_KEY));
  return j.choices?.[0]?.text ?? '';
}

// ── Auth and rate limiting ────────────────────────────────────────────────
function createAuth(env = process.env) {
  const hits = new Map();
  const limit = Number(env.SEM_PRODUCT_RATE_LIMIT_PER_MIN || 30);
  const eq = (a, b) => { const A = Buffer.from(a), B = Buffer.from(b); return A.length === B.length && crypto.timingSafeEqual(A, B); };
  return (req, res, next) => {
    const keys = (env.SEM_PRODUCT_API_KEYS || '').split(',').map(s => s.trim()).filter(Boolean);
    if (!keys.length) {
      if (env.NODE_ENV === 'production') return res.status(503).json({ error: 'Product API is not configured (SEM_PRODUCT_API_KEYS is unset).' });
      req.productKeyId = 'dev'; return next();
    }
    const given = req.get('x-api-key') || (req.get('authorization') || '').replace(/^Bearer\s+/i, '');
    const match = given && keys.find(k => eq(k, given));
    if (!match) return res.status(401).json({ error: 'Invalid or missing access key.' });
    const id = crypto.createHash('sha256').update(match).digest('hex').slice(0, 8);
    const now = Date.now(), recent = (hits.get(id) || []).filter(t => now - t < 60000);
    if (recent.length >= limit) { res.set('retry-after', '30'); return res.status(429).json({ error: 'Rate limit reached. Try again shortly.' }); }
    recent.push(now); hits.set(id, recent); req.productKeyId = id; next();
  };
}

function createProductRouter({ prisma, anthropic, env = process.env }) {
  const router = express.Router();
  const auth = createAuth(env);

  router.get('/health', (req, res) => res.json({ ok: true, configured: !!(env.SEM_PRODUCT_API_KEYS || '').trim() }));

  router.get('/domains', auth, (req, res) => res.json(Object.keys(DOMAIN_META).map(slug => {
    const { slug: sl, name, label, key, caution, options, signals } = domainInfo(slug);
    return { slug: sl, name, label, key, caution, options, signals };
  })));

  async function activeCheckpoint() {
    try { return await prisma.semCheckpoint.findFirst({ where: { isActive: true } }); } catch { return null; }
  }
  const ckInfo = c => c && { id: c.id, version: c.version, base_model: c.baseModel, held_out_mean_reward: c.meanReward };

  router.get('/model', auth, async (req, res) => {
    const c = await activeCheckpoint();
    res.json({ checkpoint: ckInfo(c), inference_configured: !!env.SEM_INFERENCE_URL,
      fallback_enabled: env.SEM_PRODUCT_ALLOW_FALLBACK !== 'false' && !!anthropic });
  });

  router.post('/diagnose', auth, async (req, res) => {
    const { domain, signals } = req.body || {};
    if (!DOMAIN_META[domain]) return res.status(400).json({ error: 'Unknown domain.' });
    const d = domainInfo(domain);
    if (!Array.isArray(signals) || signals.some(s => typeof s !== 'string')) return res.status(400).json({ error: 'signals must be an array of strings.' });
    const bad = signals.filter(s => !d.signals.includes(s));
    if (bad.length) return res.status(400).json({ error: `Unknown signal(s) for this domain: ${bad.slice(0, 5).join(', ')}` });
    const present = [...new Set(signals)];
    const prompt = buildPrompt(domain, present);
    const reference = referencePosterior(domain, present);
    const ck = await activeCheckpoint();
    const started = Date.now();
    let served_by = null, raw = null, note = null;

    // 1) The SEM model, only if a checkpoint is active AND a serving endpoint is configured.
    if (ck && env.SEM_INFERENCE_URL) {
      try { raw = await callServedModel(prompt, env); served_by = 'sem-checkpoint'; }
      catch (e) { note = `SI-SEM model endpoint failed (${e.message}).`; }
    } else {
      note = !ck ? 'No SI-SEM checkpoint is active.' : 'No SI-SEM serving endpoint is configured.';
    }
    // 2) Clearly labelled fallback so the product keeps working. Never presented as SI-SEM.
    if (served_by === null && anthropic && env.SEM_PRODUCT_ALLOW_FALLBACK !== 'false') {
      try {
        const m = await anthropic.messages.create({ model: 'claude-sonnet-4-6', max_tokens: 64, messages: [{ role: 'user', content: prompt }] });
        raw = m.content?.[0]?.text || ''; served_by = 'claude-fallback';
      } catch (e) { note = `${note || ''} Fallback failed (${e.message}).`.trim(); }
    }
    if (served_by === null) return res.status(503).json({ error: 'No model is available right now.', detail: note });

    const answer = parseAnswer(raw, d.key, d.options);
    res.json({
      domain, answer, valid: answer !== null,
      error: answer === null ? 'The model returned an answer outside the allowed list. Try again.' : undefined,
      served_by, checkpoint: served_by === 'sem-checkpoint' ? ckInfo(ck) : null, note,
      reference_probabilities: reference,
      agrees_with_reference: answer !== null ? answer === reference[0].cause : null,
      latency_ms: Date.now() - started, caution: d.caution,
    });
  });

  return router;
}

module.exports = { createProductRouter, buildPrompt, referencePosterior, parseAnswer, callServedModel, DOMAIN_META, domainInfo };
