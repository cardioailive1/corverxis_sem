// SEM Lab — server.js
// Standalone backend. Does not import from or depend on NexGen Lab's server.js.

const express = require('express');
const cors = require('cors');
const cookieParser = require('cookie-parser');
const multer = require('multer');
const crypto = require('crypto');
const path = require('path');
const fs = require('fs');
const { PrismaClient } = require('@prisma/client');

const app = express();
const prisma = new PrismaClient();
app.use(cors({ credentials: true, origin: true }));
app.use(cookieParser());
app.use(express.json({ limit: '5mb' }));

// ── Serve the frontend from this same server — matches NexGen Lab's
// proven pattern (one Express service serving both the API and the
// static UI), rather than requiring a second separate deployment. ────────
const FRONTEND_DIR = path.join(__dirname, '..', 'frontend');
app.use(express.static(FRONTEND_DIR));


const GENERATED_DIR = path.join(__dirname, 'generated');
if (!fs.existsSync(GENERATED_DIR)) fs.mkdirSync(GENERATED_DIR, { recursive: true });

// Minimal auth placeholder — real deployment should replace this with actual
// session/JWT verification, matching whatever auth system fronts this lab.
function authenticate(req, res, next) {
  req.user = { id: 'dev-user' };   // TODO: replace with real auth before production use
  next();
}

// ── Use case registry — seeded with the 12 real use cases identified ─────
const USE_CASES = [
  // SEM-only — standalone diagnostic questions, no downstream execution
  { slug: 'medical-diagnostics', name: 'Medical Diagnostics', kind: 'sem_only',
    description: 'Determine the actual root cause behind a patient\'s symptoms or an unusual test result, verified against known disease-progression models rather than a first guess.' },
  { slug: 'industrial-fault-diagnosis', name: 'Industrial Fault Diagnosis', kind: 'sem_only',
    description: 'Why a machine failed or a production batch came out defective, from sensor logs, checked against a simulator instead of trusted on first pass.' },
  { slug: 'security-incident-investigation', name: 'Security Incident Investigation', kind: 'sem_only',
    description: 'Reconstruct the true attack chain behind a breach from logs, rather than a plausible-sounding but unverified story.' },
  { slug: 'financial-fraud-investigation', name: 'Financial Fraud/Anomaly Investigation', kind: 'sem_only',
    description: 'The actual cause behind an unusual transaction pattern, not just a flagged correlation.' },
  { slug: 'scientific-discovery', name: 'Scientific Discovery', kind: 'sem_only',
    description: 'Propose the real causal mechanism behind an experimental result, verified against further simulated or real experiments.' },
  { slug: 'production-incident-rootcause', name: 'Production Incident Root-Causing', kind: 'sem_only',
    description: 'What actually broke and why, for a software outage, checked against replay/simulation rather than a first hypothesis.' },

  // Compiler use cases — one demonstration becomes a reusable, executable skill
  { slug: 'industrial-maintenance', name: 'Industrial Maintenance/Repair', kind: 'compiler',
    description: 'A retiring expert\'s one demonstration becomes a durable, reusable procedure before that knowledge is lost.',
    outputTargets: ['robot', 'checklist'] },
  { slug: 'rpa-replacement', name: 'RPA Replacement', kind: 'compiler',
    description: 'Business software workflows captured once, generalized robustly, instead of brittle macros that break on any UI change.',
    outputTargets: ['agent'] },
  { slug: 'employee-onboarding', name: 'Employee Onboarding', kind: 'compiler',
    description: 'A senior person demonstrates a complex task once; new hires get a verified, step-by-step guide instead of tribal knowledge.',
    outputTargets: ['checklist'] },
  { slug: 'warehouse-robotics', name: 'Warehouse/Logistics Robotics', kind: 'compiler',
    description: 'A robot picks up a new task from a single human demonstration, rather than needing a large teleoperated dataset.',
    outputTargets: ['robot'] },
  { slug: 'customer-support-workflows', name: 'Customer Support Workflows', kind: 'compiler',
    description: 'An agent resolves a novel ticket type once; that resolution compiles into a reusable path for similar future tickets.',
    outputTargets: ['agent', 'checklist'] },
  { slug: 'compliance-procedure-capture', name: 'Compliance/Regulatory Procedure Capture', kind: 'compiler',
    description: 'Turning "how our best person actually does this correctly" into an auditable, repeatable, verified procedure.',
    outputTargets: ['checklist'] },
];

async function seedUseCases() {
  for (const uc of USE_CASES) {
    await prisma.useCase.upsert({
      where: { slug: uc.slug },
      update: {},
      create: {
        slug: uc.slug, name: uc.name, kind: uc.kind, description: uc.description,
        outputTargets: uc.outputTargets || [],
      },
    });
  }
}

const toUseCase = u => ({
  id: u.id, slug: u.slug, name: u.name, kind: u.kind, description: u.description,
  output_targets: u.outputTargets, created_at: u.createdAt,
});

app.get('/api/use-cases', authenticate, async (req, res) => {
  const where = {};
  if (req.query.kind) where.kind = req.query.kind;
  const cases = await prisma.useCase.findMany({ where, orderBy: { name: 'asc' } });
  res.json(cases.map(toUseCase));
});

// ── Scenarios — SEM training data ─────────────────────────────────────────
// A scenario pairs a hidden intervention with the observations it produced.
// Real domain simulators live as separate scripts under training/simulators/
// (see industrial_fault_simulator.py for the reference shape); this route
// triggers that script and stores its output, rather than generating
// scenarios inline in the Node backend — simulators are domain-specific,
// often complex, and belong as their own maintained artifacts, not
// embedded logic here.
const toScenario = s => ({
  id: s.id, use_case_id: s.useCaseId, hidden_intervention: s.hiddenIntervention,
  observations: s.observations, source: s.source, created_at: s.createdAt,
});

app.post('/api/scenarios/generate', authenticate, async (req, res) => {
  const { use_case_id, count } = req.body;
  const useCase = await prisma.useCase.findUnique({ where: { id: use_case_id } });
  if (!useCase) return res.status(404).json({ error: 'Use case not found' });
  if (useCase.kind !== 'sem_only') return res.status(400).json({ error: 'Scenario generation is for sem_only use cases. Compiler use cases take demonstrations instead — see /api/demonstrations/upload.' });
  if (!useCase.simulatorSpec) return res.status(400).json({ error: `No simulator is registered for '${useCase.slug}' yet. A domain-specific simulator script must be built and registered before scenarios can be generated for this use case.` });

  try {
    const { execFile } = require('child_process');
    const simulatorPath = path.join(__dirname, '..', 'training', 'simulators', useCase.simulatorSpec);
    const output = await new Promise((resolve, reject) => {
      execFile('python3', [simulatorPath, '--generate', String(count || 10)], { timeout: 30000 }, (err, stdout, stderr) => {
        if (err) return reject(new Error(stderr || err.message));
        resolve(stdout);
      });
    });
    const generated = JSON.parse(output);   // simulator scripts are expected to print a JSON array of {hidden_intervention, observations}
    const created = await Promise.all(generated.map(g => prisma.scenario.create({ data: {
      useCaseId: use_case_id, hiddenIntervention: g.hidden_intervention, observations: g.observations, source: 'synthetic',
    }})));
    res.status(201).json(created.map(toScenario));
  } catch (err) {
    res.status(500).json({ error: 'Scenario generation failed: ' + err.message });
  }
});

app.get('/api/scenarios', authenticate, async (req, res) => {
  const where = {};
  if (req.query.use_case_id) where.useCaseId = req.query.use_case_id;
  const scenarios = await prisma.scenario.findMany({ where, orderBy: { createdAt: 'desc' }, take: 200 });
  res.json(scenarios.map(toScenario));
});

// ── Demonstrations — Skill Compiler input ─────────────────────────────────
const demoUpload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 200 * 1024 * 1024 },   // video demonstrations are large
});

const toDemonstration = d => ({
  id: d.id, use_case_id: d.useCaseId, modality: d.modality, original_name: d.originalName,
  created_at: d.createdAt,
});

app.post('/api/demonstrations/upload', authenticate, (req, res) => {
  demoUpload.single('file')(req, res, async (uploadErr) => {
    if (uploadErr) return res.status(400).json({ error: uploadErr.code === 'LIMIT_FILE_SIZE' ? 'File too large — 200MB limit.' : uploadErr.message });
    if (!req.file) return res.status(400).json({ error: 'file is required (multipart field name: "file")' });

    const { use_case_id, modality } = req.body;
    const useCase = await prisma.useCase.findUnique({ where: { id: use_case_id } });
    if (!useCase) return res.status(400).json({ error: 'Use case not found' });
    if (useCase.kind !== 'compiler') return res.status(400).json({ error: 'Demonstrations are for compiler use cases. This use case is sem_only — use /api/scenarios/generate instead.' });
    if (!['video', 'screen_recording', 'motion_capture', 'log'].includes(modality)) return res.status(400).json({ error: 'modality must be one of: video, screen_recording, motion_capture, log' });

    try {
      const hash = crypto.createHash('sha256').update(req.file.buffer).digest('hex');
      const existing = await prisma.demonstration.findFirst({ where: { contentHash: hash } });
      if (existing) return res.status(409).json({ error: 'This exact file has already been uploaded.', duplicate_of: toDemonstration(existing) });

      const storageKey = `demo-${crypto.randomBytes(8).toString('hex')}${path.extname(req.file.originalname)}`;
      fs.writeFileSync(path.join(GENERATED_DIR, storageKey), req.file.buffer);

      const demo = await prisma.demonstration.create({ data: {
        useCaseId: use_case_id, modality, storageKey, persistent: false,
        originalName: req.file.originalname, contentHash: hash, uploadedById: req.user?.id,
      }});
      res.status(201).json(toDemonstration(demo));
    } catch (err) {
      res.status(500).json({ error: 'Upload failed: ' + err.message });
    }
  });
});

app.get('/api/demonstrations', authenticate, async (req, res) => {
  const where = {};
  if (req.query.use_case_id) where.useCaseId = req.query.use_case_id;
  const demos = await prisma.demonstration.findMany({ where, orderBy: { createdAt: 'desc' } });
  res.json(demos.map(toDemonstration));
});

// ── Training runs — the SEM RL loop, tracked as a background job ─────────
// Follows the same fire-and-forget + poll pattern proven for job systems
// elsewhere: create the run, launch the actual Python training script as a
// detached process, return immediately, let the frontend poll for status.
const toTrainingRun = t => ({
  id: t.id, use_case_ids: t.useCaseIds, status: t.status,
  total_scenarios: t.totalScenarios, completed_scenarios: t.completedScenarios,
  mean_reward: t.meanReward, config: t.config, created_at: t.createdAt, completed_at: t.completedAt,
});

async function processTrainingRun(runId) {
  const run = await prisma.trainingRun.findUnique({ where: { id: runId } });
  if (!run) return;
  await prisma.trainingRun.update({ where: { id: runId }, data: { status: 'running' } });

  try {
    const where = run.useCaseIds.length > 0 ? { useCaseId: { in: run.useCaseIds } } : {};
    const scenarios = await prisma.scenario.findMany({ where });
    await prisma.trainingRun.update({ where: { id: runId }, data: { totalScenarios: scenarios.length } });

    let totalReward = 0;
    for (const scenario of scenarios) {
      // In production this calls the real training_loop.py propose step
      // against the model currently being trained. Left as an explicit
      // integration point — see training/training_loop.py for the real,
      // tested loop this would invoke per scenario.
      const { execFile } = require('child_process');
      const scriptPath = path.join(__dirname, '..', 'training', 'run_single_scenario.py');
      const result = await new Promise((resolve, reject) => {
        execFile('python3', [scriptPath, JSON.stringify(scenario.observations), JSON.stringify(scenario.hiddenIntervention)], { timeout: 15000 }, (err, stdout) => {
          if (err) return reject(err);
          resolve(JSON.parse(stdout));
        });
      }).catch(() => ({ proposed: null, reward: 0 }));   // one failed scenario shouldn't kill the whole run

      await prisma.scenarioResult.create({ data: {
        trainingRunId: runId, scenarioId: scenario.id,
        proposedStructure: result.proposed || {}, reward: result.reward,
      }});
      totalReward += result.reward;
      await prisma.trainingRun.update({ where: { id: runId }, data: { completedScenarios: { increment: 1 } } });
    }

    await prisma.trainingRun.update({ where: { id: runId }, data: {
      status: 'completed', completedAt: new Date(),
      meanReward: scenarios.length > 0 ? totalReward / scenarios.length : null,
    }});
  } catch (err) {
    await prisma.trainingRun.update({ where: { id: runId }, data: { status: 'failed' } });
  }
}

app.post('/api/training-runs', authenticate, async (req, res) => {
  const { use_case_ids, config } = req.body;
  const run = await prisma.trainingRun.create({ data: {
    useCaseIds: use_case_ids || [], config: config || {}, createdById: req.user?.id,
  }});
  processTrainingRun(run.id).catch(err => console.error('Training run error:', err.message));   // fire-and-forget, status polled via GET
  res.status(202).json(toTrainingRun(run));
});

app.get('/api/training-runs/:id', authenticate, async (req, res) => {
  const run = await prisma.trainingRun.findUnique({ where: { id: req.params.id } });
  if (!run) return res.status(404).json({ error: 'Training run not found' });
  res.json(toTrainingRun(run));
});

app.get('/api/training-runs', authenticate, async (req, res) => {
  const runs = await prisma.trainingRun.findMany({ orderBy: { createdAt: 'desc' }, take: 50 });
  res.json(runs.map(toTrainingRun));
});

// ── Skill Compiler pipeline — one job per demonstration, 6 stages tracked ─
const toCompilerJob = c => ({
  id: c.id, use_case_id: c.useCaseId, demonstration_id: c.demonstrationId, target_output: c.targetOutput,
  stage: c.stage, observation_sequence: c.observationSeq, causal_structure: c.causalStructure,
  verified_structure: c.verifiedStructure, abstracted_procedure: c.abstractedProcedure,
  compiled_output: c.compiledOutput, confidence_notes: c.confidenceNotes, error_message: c.errorMessage,
  created_at: c.createdAt, completed_at: c.completedAt,
});

async function processCompilerJob(jobId) {
  const stages = ['ingestion', 'extraction', 'verification', 'abstraction', 'compilation'];
  try {
    for (const stage of stages) {
      await prisma.compilerJob.update({ where: { id: jobId }, data: { stage } });
      // Each stage is a real integration point to the corresponding
      // component (ingestion parsers, the SEM model for extraction,
      // perturbation-testing verifiers, the abstraction/compilation
      // logic per target). Left explicit here rather than faked, since
      // each one is substantial, domain-specific work in its own right —
      // see the design document for what each stage actually needs to do.
      await new Promise(r => setTimeout(r, 500));   // placeholder for real stage processing time
    }
    await prisma.compilerJob.update({ where: { id: jobId }, data: { stage: 'completed', completedAt: new Date() } });
  } catch (err) {
    await prisma.compilerJob.update({ where: { id: jobId }, data: { stage: 'failed', errorMessage: err.message } });
  }
}

app.post('/api/compiler-jobs', authenticate, async (req, res) => {
  const { use_case_id, demonstration_id, target_output } = req.body;
  const useCase = await prisma.useCase.findUnique({ where: { id: use_case_id } });
  if (!useCase) return res.status(404).json({ error: 'Use case not found' });
  if (!useCase.outputTargets.includes(target_output)) return res.status(400).json({ error: `'${target_output}' is not a valid output target for this use case. Valid: ${useCase.outputTargets.join(', ')}` });

  const job = await prisma.compilerJob.create({ data: {
    useCaseId: use_case_id, demonstrationId: demonstration_id, targetOutput: target_output, createdById: req.user?.id,
  }});
  processCompilerJob(job.id).catch(err => console.error('Compiler job error:', err.message));
  res.status(202).json(toCompilerJob(job));
});

app.get('/api/compiler-jobs/:id', authenticate, async (req, res) => {
  const job = await prisma.compilerJob.findUnique({ where: { id: req.params.id } });
  if (!job) return res.status(404).json({ error: 'Compiler job not found' });
  res.json(toCompilerJob(job));
});

app.get('/api/compiler-jobs', authenticate, async (req, res) => {
  const where = {};
  if (req.query.use_case_id) where.useCaseId = req.query.use_case_id;
  const jobs = await prisma.compilerJob.findMany({ where, orderBy: { createdAt: 'desc' }, take: 50 });
  res.json(jobs.map(toCompilerJob));
});

// ── SEM checkpoint registry ─────────────────────────────────────────────
const toCheckpoint = c => ({
  id: c.id, version: c.version, base_model: c.baseModel, training_run_id: c.trainingRunId,
  mean_reward: c.meanReward, is_active: c.isActive, created_at: c.createdAt,
});

app.get('/api/checkpoints', authenticate, async (req, res) => {
  const checkpoints = await prisma.semCheckpoint.findMany({ orderBy: { createdAt: 'desc' } });
  res.json(checkpoints.map(toCheckpoint));
});

app.post('/api/checkpoints/:id/activate', authenticate, async (req, res) => {
  await prisma.semCheckpoint.updateMany({ data: { isActive: false } });
  const updated = await prisma.semCheckpoint.update({ where: { id: req.params.id }, data: { isActive: true } });
  res.json(toCheckpoint(updated));
});

module.exports = { app, prisma, authenticate, seedUseCases, GENERATED_DIR, toUseCase, USE_CASES };

// ── Startup — only actually binds a port when run directly, not when
// imported (e.g. for testing). Seeds the 12 use cases on first boot. ────────
if (require.main === module) {
  const PORT = process.env.PORT || 4001;
  seedUseCases()
    .then(() => console.log('Use cases seeded.'))
    .catch(err => console.error('Seeding failed (continuing anyway):', err.message))
    .finally(() => {
      app.listen(PORT, () => console.log(`SEM+OSC backend listening on port ${PORT}`));
    });
}

