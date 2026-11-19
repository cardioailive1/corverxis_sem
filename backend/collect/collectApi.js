// Real-case collection API for SI-SEM validation. Mounted at /api/collect by server.js.
//
// Modelled on Frontier Lab Phase 1 (qualified experts submit work, a second person reviews it), but the unit of
// work is one REAL case: which signals were present, and what the cause was confirmed to be. Approved cases
// feed training/simulators/calibrate.py, which checks and re-estimates a domain's probabilities before training.
//
// Roles
//   admin        keys in SEM_COLLECT_ADMIN_KEYS ("label=key,label2=key2"). Creates contributors, sees progress, exports.
//   contributor  a person an admin has qualified for specific domains. Submits cases; may review OTHER people's cases
//                in the domains they are qualified for. Nobody can review their own case.
//
// Privacy: cases must be de-identified. Free text is screened for obvious identifiers and the submitter must attest.
// Export is admin only. Production refuses to serve without admin keys.
const crypto = require('crypto');
const express = require('express');
const { SPEC } = require('../simulators/specSimulator.js');

const OTHER = 'other_not_listed';
const KINDS = ['confirmed_outcome', 'test_or_inspection', 'post_mortem', 'expert_judgement'];
const DECISIONS = ['approved', 'rejected', 'needs_revision'];
const sha = s => crypto.createHash('sha256').update(s).digest('hex');
const eq = (a, b) => { const A = Buffer.from(a), B = Buffer.from(b); return A.length === B.length && crypto.timingSafeEqual(A, B); };

// Obvious identifiers only. This is a safety net, not a guarantee; the attestation and review are the real control.
const PII = [/[\w.+-]+@[\w-]+\.[\w.-]+/, /\b\d{3}[-. ]\d{2}[-. ]\d{4}\b/, /(?:\+?\d[\s.-]?){10,}/, /\b(?:mrn|ssn|dob|patient id)\b\s*[:#]?\s*\w+/i];
const looksIdentifying = t => PII.some(r => r.test(t || ''));

const domainDetail = slug => { const d = SPEC[slug]; return { slug, name: d.name, label: d.label, category: d.category, signals: d.signals, causes: d.causes, caution: d.caution || null }; };

// What calibrate.py needs before it will write a calibration, per domain.
function readiness(slug, approved) {
  const d = SPEC[slug], counts = Object.fromEntries(d.causes.map(c => [c, 0]));
  for (const k of approved) if (k.trueCause in counts) counts[k.trueCause]++;
  const total = Object.values(counts).reduce((a, b) => a + b, 0), need = 20 * d.causes.length;
  const present = d.causes.filter(c => counts[c] > 0).length;
  // calibrate.py holds out 30% and needs >=15 fit cases per cause, so ask for ~22 per cause to be safe
  const thin = d.causes.filter(c => counts[c] < 22);
  return { slug, name: d.name, approved: total, needed_overall: need, causes_present: present, causes_total: d.causes.length,
    causes_below_22: thin.length, by_cause: counts, ready_to_calibrate: total >= need && thin.length === 0 };
}

function createCollectRouter({ prisma, env = process.env }) {
  const router = express.Router();
  const hits = new Map();
  const limit = Number(env.SEM_COLLECT_RATE_LIMIT_PER_MIN || 60);

  const adminKeys = () => (env.SEM_COLLECT_ADMIN_KEYS || '').split(',').map(s => s.trim()).filter(Boolean)
    .map(p => { const i = p.indexOf('='); return i > 0 ? { label: p.slice(0, i), key: p.slice(i + 1) } : { label: 'admin', key: p }; });

  async function who(req, res, next) {
    const keys = adminKeys();
    if (!keys.length && env.NODE_ENV === 'production') return res.status(503).json({ error: 'Collection is not configured (SEM_COLLECT_ADMIN_KEYS is unset).' });
    const given = req.get('x-api-key') || (req.get('authorization') || '').replace(/^Bearer\s+/i, '');
    if (!given) return res.status(401).json({ error: 'Missing access key.' });
    const admin = keys.find(k => eq(k.key, given));
    if (admin) req.actor = { role: 'admin', id: 'admin:' + admin.label, label: admin.label };
    else {
      const c = await prisma.caseContributor.findUnique({ where: { keyHash: sha(given) } });
      if (!c || c.status !== 'qualified') return res.status(401).json({ error: 'Invalid access key.' });
      req.actor = { role: 'contributor', id: c.id, label: c.name, domains: c.domains };
    }
    const id = sha(given).slice(0, 8), now = Date.now(), recent = (hits.get(id) || []).filter(t => now - t < 60000);
    if (recent.length >= limit) { res.set('retry-after', '30'); return res.status(429).json({ error: 'Rate limit reached. Try again shortly.' }); }
    recent.push(now); hits.set(id, recent); next();
  }
  const adminOnly = (req, res, next) => req.actor.role === 'admin' ? next() : res.status(403).json({ error: 'Admin only.' });
  const canWork = (actor, slug) => actor.role === 'admin' || actor.domains.includes(slug);

  router.get('/health', (req, res) => res.json({ ok: true, configured: adminKeys().length > 0 }));
  router.get('/me', who, (req, res) => res.json({ role: req.actor.role, name: req.actor.label, domains: req.actor.role === 'admin' ? Object.keys(SPEC) : req.actor.domains }));

  router.get('/domains', who, (req, res) => {
    const slugs = Object.keys(SPEC).filter(s => canWork(req.actor, s));
    res.json(slugs.map(domainDetail));
  });

  // ── Admin: contributors ─────────────────────────────────────────────────
  router.post('/contributors', who, adminOnly, async (req, res) => {
    const { name, email, domains, notes } = req.body || {};
    if (!name || !email || !/^\S+@\S+\.\S+$/.test(email)) return res.status(400).json({ error: 'name and a valid email are required.' });
    if (!Array.isArray(domains) || !domains.length || domains.some(s => !SPEC[s])) return res.status(400).json({ error: 'domains must be a non-empty list of valid domain slugs.' });
    const key = 'sc_' + crypto.randomBytes(24).toString('hex');
    try {
      const c = await prisma.caseContributor.create({ data: { name, email, keyHash: sha(key), domains: [...new Set(domains)], notes: notes || null } });
      // The key is shown exactly once. Only its hash is stored.
      res.status(201).json({ id: c.id, name: c.name, email: c.email, domains: c.domains, access_key: key, note: 'Copy this key now. It is not stored and cannot be shown again.' });
    } catch (e) { res.status(e.code === 'P2002' ? 409 : 500).json({ error: e.code === 'P2002' ? 'A contributor with this email already exists.' : 'Could not create contributor.' }); }
  });
  router.get('/contributors', who, adminOnly, async (req, res) => {
    const list = await prisma.caseContributor.findMany({ orderBy: { createdAt: 'desc' } });
    res.json(list.map(c => ({ id: c.id, name: c.name, email: c.email, status: c.status, domains: c.domains, notes: c.notes, created_at: c.createdAt })));
  });
  router.post('/contributors/:id/status', who, adminOnly, async (req, res) => {
    const { status } = req.body || {};
    if (!['qualified', 'suspended'].includes(status)) return res.status(400).json({ error: 'status must be qualified or suspended.' });
    try { const c = await prisma.caseContributor.update({ where: { id: req.params.id }, data: { status } }); res.json({ id: c.id, status: c.status }); }
    catch { res.status(404).json({ error: 'Contributor not found.' }); }
  });

  // ── Submit a case ───────────────────────────────────────────────────────
  router.post('/cases', who, async (req, res) => {
    const b = req.body || {}, slug = b.domain;
    if (!SPEC[slug]) return res.status(400).json({ error: 'Unknown domain.' });
    if (req.actor.role !== 'contributor') return res.status(403).json({ error: 'Cases are submitted by qualified contributors. Create a contributor key for the person who knows the case.' });
    if (!canWork(req.actor, slug)) return res.status(403).json({ error: 'You are not qualified for this domain.' });
    const d = SPEC[slug];
    if (!Array.isArray(b.signals) || b.signals.some(s => !d.signals.includes(s))) return res.status(400).json({ error: 'signals must be a list of this domain\'s signals.' });
    if (b.trueCause !== OTHER && !d.causes.includes(b.trueCause)) return res.status(400).json({ error: 'trueCause must be one of the domain\'s causes or ' + OTHER + '.' });
    if (b.trueCause === OTHER && !(typeof b.otherCause === 'string' && b.otherCause.trim().length >= 3)) return res.status(400).json({ error: 'Describe the cause in otherCause.' });
    if (!KINDS.includes(b.evidenceKind)) return res.status(400).json({ error: 'evidenceKind must be one of ' + KINDS.join(', ') + '.' });
    if (typeof b.evidence !== 'string' || b.evidence.trim().length < 20 || b.evidence.length > 2000) return res.status(400).json({ error: 'evidence must say how the cause was confirmed (20 to 2000 characters).' });
    if (b.checkedAllSignals !== true) return res.status(400).json({ error: 'Confirm that you checked every listed signal and that unticked ones were absent.' });
    if (b.deidentified !== true) return res.status(400).json({ error: 'Confirm that the case contains no personal or confidential identifiers.' });
    if (b.occurredOn != null && !/^\d{4}-\d{2}(-\d{2})?$/.test(b.occurredOn)) return res.status(400).json({ error: 'occurredOn must look like 2025-03 or 2025-03-14.' });
    for (const t of [b.evidence, b.source, b.otherCause]) if (looksIdentifying(t)) return res.status(400).json({ error: 'The text appears to contain an identifier (email, phone, ID number). Remove it and resubmit.' });
    const signals = d.signals.filter(s => b.signals.includes(s));
    const caseHash = sha([slug, b.trueCause, signals.join(','), b.occurredOn || '', (b.source || '').trim().toLowerCase()].join('|'));
    try {
      const c = await prisma.realCase.create({ data: { domainSlug: slug, contributorId: req.actor.id, signals, trueCause: b.trueCause,
        otherCause: b.trueCause === OTHER ? b.otherCause.trim() : null, evidenceKind: b.evidenceKind, evidence: b.evidence.trim(),
        source: b.source ? String(b.source).slice(0, 200) : null, occurredOn: b.occurredOn || null, caseHash } });
      res.status(201).json({ id: c.id, review_status: c.reviewStatus });
    } catch (e) { res.status(e.code === 'P2002' ? 409 : 500).json({ error: e.code === 'P2002' ? 'This case has already been submitted.' : 'Could not save the case.' }); }
  });

  const view = (c, withAuthor) => ({ id: c.id, domain: c.domainSlug, signals: c.signals, true_cause: c.trueCause, other_cause: c.otherCause,
    evidence_kind: c.evidenceKind, evidence: c.evidence, source: c.source, occurred_on: c.occurredOn, review_status: c.reviewStatus,
    review_notes: c.reviewNotes, created_at: c.createdAt, ...(withAuthor ? { contributor_id: c.contributorId, reviewed_by: c.reviewedBy } : {}) });

  router.get('/cases/mine', who, async (req, res) => {
    const list = await prisma.realCase.findMany({ where: { contributorId: req.actor.id }, orderBy: { createdAt: 'desc' } });
    res.json(list.slice(0, 200).map(c => view(c)));
  });

  // ── Review: a second person, in a domain they are qualified for ─────────────
  router.get('/review/queue', who, async (req, res) => {
    const where = { reviewStatus: 'needs_review' }; if (req.query.domain) where.domainSlug = req.query.domain;
    const list = (await prisma.realCase.findMany({ where, orderBy: { createdAt: 'asc' } }))
      .filter(c => canWork(req.actor, c.domainSlug) && c.contributorId !== req.actor.id);
    res.json(list.slice(0, 50).map(c => view(c)));
  });
  router.post('/cases/:id/review', who, async (req, res) => {
    const { decision, notes } = req.body || {};
    if (!DECISIONS.includes(decision)) return res.status(400).json({ error: 'decision must be approved, rejected or needs_revision.' });
    if (decision !== 'approved' && !(typeof notes === 'string' && notes.trim())) return res.status(400).json({ error: 'Say why in notes.' });
    const c = await prisma.realCase.findUnique({ where: { id: req.params.id } });
    if (!c) return res.status(404).json({ error: 'Case not found.' });
    if (!canWork(req.actor, c.domainSlug)) return res.status(403).json({ error: 'You are not qualified to review this domain.' });
    if (c.contributorId === req.actor.id) return res.status(403).json({ error: 'You cannot review your own case.' });
    if (c.reviewStatus === 'approved') return res.status(409).json({ error: 'Already approved.' });
    const u = await prisma.realCase.update({ where: { id: c.id }, data: { reviewStatus: decision, reviewNotes: notes ? String(notes).slice(0, 1000) : null, reviewedBy: req.actor.id, reviewedAt: new Date() } });
    res.json({ id: u.id, review_status: u.reviewStatus });
  });

  // ── Progress and export (admin) ────────────────────────────────────────────
  router.get('/progress', who, adminOnly, async (req, res) => {
    const all = await prisma.realCase.findMany({});
    res.json(Object.keys(SPEC).map(slug => {
      const mine = all.filter(c => c.domainSlug === slug);
      return { ...readiness(slug, mine.filter(c => c.reviewStatus === 'approved')),
        awaiting_review: mine.filter(c => c.reviewStatus === 'needs_review').length, other_not_listed: mine.filter(c => c.reviewStatus === 'approved' && c.trueCause === OTHER).length };
    }));
  });

  // CSV for training/simulators/calibrate.py: approved cases whose cause is in the list, one row per case.
  router.get('/export/:slug.csv', who, adminOnly, async (req, res) => {
    if (!SPEC[req.params.slug]) return res.status(404).json({ error: 'Unknown domain.' });
    const rows = (await prisma.realCase.findMany({ where: { domainSlug: req.params.slug, reviewStatus: 'approved' }, orderBy: { createdAt: 'asc' } })).filter(c => c.trueCause !== OTHER);
    const q = v => /[",\n]/.test(v) ? '"' + String(v).replace(/"/g, '""') + '"' : String(v);
    res.type('text/csv').send(['cause,signals,case_id', ...rows.map(c => [c.trueCause, c.signals.join(';'), c.id].map(q).join(','))].join('\n') + '\n');
  });

  return router;
}

module.exports = { createCollectRouter, readiness, looksIdentifying, OTHER };
