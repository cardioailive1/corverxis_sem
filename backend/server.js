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
const Anthropic = require('@anthropic-ai/sdk');
const logPipeline = require('./compiler/logPipeline.js');

const app = express();
const prisma = new PrismaClient();
const anthropic = process.env.ANTHROPIC_API_KEY ? new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY }) : null;

// ── S3-backed durable storage for demonstration files ─────────────────────
// Render's local disk does NOT survive redeploys — every code push wipes
// anything previously written to it. Without this, an uploaded
// demonstration becomes permanently unreadable (a real ENOENT) the moment
// any other change gets deployed, even though its database row looks
// completely fine. Optional: without S3 env vars set, this cleanly falls
// back to local disk with the exact same limitation as before, just with
// a clear error instead of a raw stack trace when a file goes missing.
function isS3Configured() {
  return !!(process.env.S3_BUCKET && process.env.AWS_ACCESS_KEY_ID && process.env.AWS_SECRET_ACCESS_KEY);
}
let _s3Client = null;
function getS3Client() {
  if (!_s3Client) {
    const { S3Client } = require('@aws-sdk/client-s3');
    _s3Client = new S3Client({ region: process.env.AWS_REGION || 'us-east-1' });
  }
  return _s3Client;
}
async function storeDemonstrationFile(localPath, filename) {
  if (isS3Configured()) {
    const { PutObjectCommand } = require('@aws-sdk/client-s3');
    const buffer = fs.readFileSync(localPath);
    await getS3Client().send(new PutObjectCommand({ Bucket: process.env.S3_BUCKET, Key: `demonstrations/${filename}`, Body: buffer }));
    fs.unlinkSync(localPath);   // don't keep a local copy once it's durably stored — avoids relying on ephemeral disk even briefly
    return { storageKey: `demonstrations/${filename}`, persistent: true };
  }
  return { storageKey: filename, persistent: false };   // unchanged fallback — same limitation as before, S3 not configured
}
async function readDemonstrationBuffer(demonstration) {
  if (demonstration.persistent && isS3Configured()) {
    const { GetObjectCommand } = require('@aws-sdk/client-s3');
    const obj = await getS3Client().send(new GetObjectCommand({ Bucket: process.env.S3_BUCKET, Key: demonstration.storageKey }));
    const chunks = [];
    for await (const chunk of obj.Body) chunks.push(chunk);
    return Buffer.concat(chunks);
  }
  const localPath = path.join(GENERATED_DIR, demonstration.storageKey);
  if (!fs.existsSync(localPath)) {
    // The actual, specific fix for the reported bug: a clear, actionable
    // error instead of a raw ENOENT stack trace surfacing straight to the
    // user. Explains WHY, not just THAT it failed.
    throw new Error(
      `Demonstration file "${demonstration.originalName}" is no longer available. ` +
      (isS3Configured()
        ? 'This file was uploaded before S3 storage was configured, so it only ever existed on local disk, which does not survive a redeploy. Please re-upload it.'
        : 'This server has no durable file storage configured (S3), and local disk does not survive a redeploy — every code push wipes previously uploaded files. Please re-upload, and consider configuring S3 (see README) so this stops happening.')
    );
  }
  return fs.readFileSync(localPath);
}
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
    description: 'Determine the actual root cause behind a patient\'s symptoms or an unusual test result, verified against known disease-progression models rather than a first guess.',
    simulatorSpec: 'medical_diagnostics_simulator.py' },
  { slug: 'industrial-fault-diagnosis', name: 'Industrial Fault Diagnosis', kind: 'sem_only',
    description: 'Why a machine failed or a production batch came out defective, from sensor logs, checked against a simulator instead of trusted on first pass.',
    simulatorSpec: 'industrial_fault_simulator.py' },
  { slug: 'security-incident-investigation', name: 'Security Incident Investigation', kind: 'sem_only',
    description: 'Reconstruct the true attack chain behind a breach from logs, rather than a plausible-sounding but unverified story.',
    simulatorSpec: 'security_incident_simulator.py' },
  { slug: 'financial-fraud-investigation', name: 'Financial Fraud/Anomaly Investigation', kind: 'sem_only',
    description: 'The actual cause behind an unusual transaction pattern, not just a flagged correlation.',
    simulatorSpec: 'financial_fraud_simulator.py' },
  { slug: 'scientific-discovery', name: 'Scientific Discovery', kind: 'sem_only',
    description: 'Propose the real causal mechanism behind an experimental result, verified against further simulated or real experiments.',
    simulatorSpec: 'scientific_discovery_simulator.py' },
  { slug: 'production-incident-rootcause', name: 'Production Incident Root-Causing', kind: 'sem_only',
    description: 'What actually broke and why, for a software outage, checked against replay/simulation rather than a first hypothesis.',
    simulatorSpec: 'production_incident_simulator.py' },

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
      update: { simulatorSpec: uc.simulatorSpec || null, outputTargets: uc.outputTargets || [] },
      create: {
        slug: uc.slug, name: uc.name, kind: uc.kind, description: uc.description,
        outputTargets: uc.outputTargets || [], simulatorSpec: uc.simulatorSpec || null,
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

// ── Simulator registry — maps a use case slug to its JS simulator module.
// Simulators run in-process now (see backend/simulators/), not shelled out
// to python3 — Render's Node-native runtime doesn't provide a Python
// interpreter, and native runtimes are isolated per language. The
// training/simulators/*.py files remain as the canonical, independently
// testable reference implementation for local experimentation; this
// registry is what actually runs in production.
const JS_SIMULATORS = {
  'industrial-fault-diagnosis': require('./simulators/industrialFaultSimulator.js'),
  'medical-diagnostics': require('./simulators/medicalDiagnosticsSimulator.js'),
  'security-incident-investigation': require('./simulators/securityIncidentSimulator.js'),
  'financial-fraud-investigation': require('./simulators/financialFraudSimulator.js'),
  'scientific-discovery': require('./simulators/scientificDiscoverySimulator.js'),
  'production-incident-rootcause': require('./simulators/productionIncidentSimulator.js'),
};

app.post('/api/scenarios/generate', authenticate, async (req, res) => {
  const { use_case_id, count } = req.body;
  const useCase = await prisma.useCase.findUnique({ where: { id: use_case_id } });
  if (!useCase) return res.status(404).json({ error: 'Use case not found' });
  if (useCase.kind !== 'sem_only') return res.status(400).json({ error: 'Scenario generation is for sem_only use cases. Compiler use cases take demonstrations instead — see /api/demonstrations/upload.' });
  const simulator = JS_SIMULATORS[useCase.slug];
  if (!simulator) return res.status(400).json({ error: `No simulator is registered for '${useCase.slug}' yet. A domain-specific simulator module must be built and added to JS_SIMULATORS before scenarios can be generated for this use case.` });

  try {
    const generated = simulator.generateScenarios(count || 10);
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

      const filename = `demo-${crypto.randomBytes(8).toString('hex')}${path.extname(req.file.originalname)}`;
      const localPath = path.join(GENERATED_DIR, filename);
      fs.writeFileSync(localPath, req.file.buffer);   // always written locally first; storeDemonstrationFile promotes it to S3 and removes the local copy when S3 is configured
      const { storageKey, persistent } = await storeDemonstrationFile(localPath, filename);

      const demo = await prisma.demonstration.create({ data: {
        useCaseId: use_case_id, modality, storageKey, persistent,
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
  id: t.id, use_case_ids: t.useCaseIds, run_type: t.runType, status: t.status,
  total_scenarios: t.totalScenarios, completed_scenarios: t.completedScenarios,
  mean_reward: t.meanReward, config: t.config, created_at: t.createdAt, completed_at: t.completedAt,
});

async function processTrainingRun(runId) {
  const run = await prisma.trainingRun.findUnique({ where: { id: runId } });
  if (!run) return;
  await prisma.trainingRun.update({ where: { id: runId }, data: { status: 'running' } });

  try {
    const where = run.useCaseIds.length > 0 ? { useCaseId: { in: run.useCaseIds } } : {};
    const scenarios = await prisma.scenario.findMany({ where, include: { useCase: true } });
    await prisma.trainingRun.update({ where: { id: runId }, data: { totalScenarios: scenarios.length } });

    let totalReward = 0;
    for (const scenario of scenarios) {
      // Runs in-process via the JS simulator registry — see the comment on
      // JS_SIMULATORS above for why this isn't shelled out to python3.
      const simulator = JS_SIMULATORS[scenario.useCase.slug];
      const result = simulator
        ? simulator.runSingleScenario(scenario.observations, scenario.hiddenIntervention)
        : { proposed: null, reward: 0 };

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
  const { use_case_ids, config, run_type } = req.body;
  const runType = run_type === 'grpo' ? 'grpo' : 'reference';
  const run = await prisma.trainingRun.create({ data: {
    useCaseIds: use_case_ids || [], config: config || {}, runType, createdById: req.user?.id,
  }});
  // A 'grpo' run is real training happening externally on a GPU pod
  // (train_grpo.py) — nothing to run in-process here. It reports its own
  // progress via PATCH /api/training-runs/:id/progress below. Only the
  // 'reference' type runs the fast, in-process heuristic loop, useful for
  // quickly checking a simulator/reward mechanism without touching a GPU.
  if (runType === 'reference') {
    processTrainingRun(run.id).catch(err => console.error('Training run error:', err.message));   // fire-and-forget, status polled via GET
  }
  res.status(202).json(toTrainingRun(run));
});

// PATCH /api/training-runs/:id/progress — called externally by
// train_grpo.py while a real GRPO job is actually running on a GPU pod,
// since that process — not this backend — is the one doing the training
// and is the only thing that knows real progress as it happens.
app.patch('/api/training-runs/:id/progress', authenticate, async (req, res) => {
  const { completed_scenarios, total_scenarios, mean_reward, status } = req.body;
  const data = {};
  if (completed_scenarios !== undefined) data.completedScenarios = completed_scenarios;
  if (total_scenarios !== undefined) data.totalScenarios = total_scenarios;
  if (mean_reward !== undefined) data.meanReward = mean_reward;
  if (status !== undefined) {
    data.status = status;
    if (status === 'completed' || status === 'failed') data.completedAt = new Date();
  }
  try {
    const updated = await prisma.trainingRun.update({ where: { id: req.params.id }, data });
    res.json(toTrainingRun(updated));
  } catch (err) {
    if (err.code === 'P2025') return res.status(404).json({ error: 'Training run not found' });
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/training-runs/:id', authenticate, async (req, res) => {
  const run = await prisma.trainingRun.findUnique({ where: { id: req.params.id } });
  if (!run) return res.status(404).json({ error: 'Training run not found' });
  res.json(toTrainingRun(run));
});

// GET /api/training-runs/:id/results — per-scenario propose/verify/reward
// records for a run, for the detail view (what did it actually propose,
// scenario by scenario, and what reward did each one get).
app.get('/api/training-runs/:id/results', authenticate, async (req, res) => {
  const results = await prisma.scenarioResult.findMany({
    where: { trainingRunId: req.params.id },
    include: { scenario: true },
    orderBy: { createdAt: 'asc' },
  });
  res.json(results.map(r => ({
    id: r.id, scenario_id: r.scenarioId,
    hidden_intervention: r.scenario.hiddenIntervention, observations: r.scenario.observations,
    proposed_structure: r.proposedStructure, reward: r.reward, created_at: r.createdAt,
  })));
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
  const job = await prisma.compilerJob.findUnique({ where: { id: jobId } });
  if (!job) return;
  const demonstration = await prisma.demonstration.findUnique({ where: { id: job.demonstrationId } });

  // Only `log` modality has a real, implemented pipeline (see
  // backend/compiler/logPipeline.js and its README note on why this is
  // the first fully-supported modality). Other modalities fall back to
  // the same honest placeholder as before — parsing raw video/screen
  // recordings is a separate, harder computer-vision problem, not solved
  // here.
  if (!demonstration || demonstration.modality !== 'log') {
    try {
      const stages = ['ingestion', 'extraction', 'verification', 'abstraction', 'compilation'];
      for (const stage of stages) {
        await prisma.compilerJob.update({ where: { id: jobId }, data: { stage } });
        await new Promise(r => setTimeout(r, 500));
      }
      await prisma.compilerJob.update({ where: { id: jobId }, data: {
        stage: 'completed', completedAt: new Date(),
        confidenceNotes: `No real pipeline exists yet for "${demonstration?.modality || 'unknown'}" modality — only "log" demonstrations are fully processed. This is a placeholder result.`,
      }});
    } catch (err) {
      await prisma.compilerJob.update({ where: { id: jobId }, data: { stage: 'failed', errorMessage: err.message } });
    }
    return;
  }

  if (!anthropic) {
    await prisma.compilerJob.update({ where: { id: jobId }, data: {
      stage: 'failed', errorMessage: 'ANTHROPIC_API_KEY is not configured on this server — the real log-modality pipeline needs it for stages 2-4.',
    }});
    return;
  }

  try {
    // ── Stage 1: Ingestion — real, deterministic, no LLM call ─────────────
    await prisma.compilerJob.update({ where: { id: jobId }, data: { stage: 'ingestion' } });
    const fileBuffer = await readDemonstrationBuffer(demonstration);
    const observationSequence = logPipeline.ingestLogDemonstration(fileBuffer);
    await prisma.compilerJob.update({ where: { id: jobId }, data: { observationSeq: observationSequence } });

    // ── Stage 2: Causal Extraction ─────────────────────────────────────────
    await prisma.compilerJob.update({ where: { id: jobId }, data: { stage: 'extraction' } });
    const extraction = await logPipeline.extractCausalStructure(anthropic, observationSequence);
    await prisma.compilerJob.update({ where: { id: jobId }, data: { causalStructure: extraction } });

    // ── Stage 3: Verification ──────────────────────────────────────────────
    await prisma.compilerJob.update({ where: { id: jobId }, data: { stage: 'verification' } });
    const verified = await logPipeline.verifyStructure(anthropic, observationSequence, extraction);
    await prisma.compilerJob.update({ where: { id: jobId }, data: {
      verifiedStructure: verified, confidenceNotes: verified.confidence_notes,
    }});

    // ── Stage 4: Abstraction ───────────────────────────────────────────────
    await prisma.compilerJob.update({ where: { id: jobId }, data: { stage: 'abstraction' } });
    const abstracted = await logPipeline.abstractProcedure(anthropic, observationSequence, verified);
    await prisma.compilerJob.update({ where: { id: jobId }, data: { abstractedProcedure: abstracted } });

    // ── Stage 5: Compilation — real, deterministic, no LLM call ───────────
    await prisma.compilerJob.update({ where: { id: jobId }, data: { stage: 'compilation' } });
    const compiled = logPipeline.compileToTarget(abstracted, job.targetOutput);
    await prisma.compilerJob.update({ where: { id: jobId }, data: {
      compiledOutput: compiled, stage: 'completed', completedAt: new Date(),
    }});
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

// POST /api/checkpoints — registers a real training run's output. The
// actual GRPO training script (training/grpo/train_grpo.py) calls this
// directly when a training run finishes, using its API key — this is
// the piece that was missing before: checkpoints could be listed and
// activated, but never actually created.
app.post('/api/checkpoints', authenticate, async (req, res) => {
  const { version, base_model, training_run_id, mean_reward, storage_key } = req.body;
  if (!version || !base_model) return res.status(400).json({ error: 'version and base_model are required' });
  const checkpoint = await prisma.semCheckpoint.create({ data: {
    version, baseModel: base_model, trainingRunId: training_run_id || null,
    meanReward: mean_reward ?? null, storageKey: storage_key || '', isActive: false,
  }});
  res.status(201).json(toCheckpoint(checkpoint));
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

