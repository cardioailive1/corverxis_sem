# SEM+OSC

A standalone lab (SEM+OSC — Structural Extraction Model + One-Shot Compiler) for developing, training, and deploying SEM (Structural
Extraction Model) and the One-Shot Skill Compiler. **Shares no code with
NexGen Lab** — separate backend, separate frontend, separate database.

## Architecture note — simulators run in-process (JS), not shelled out to Python

Earlier versions of this backend called `training/simulators/*.py` via
`execFile('python3', ...)`. That was removed — Render's `runtime: node`
service is a native, language-isolated environment and does not provide a
Python interpreter, so those calls failed in production even though they
worked fine locally. The `industrial_fault_simulator.py` logic has been
ported to `backend/simulators/industrialFaultSimulator.js`, registered in
`JS_SIMULATORS` in `server.js`, and confirmed to produce identical reward
behavior to the Python version (same 1.0-for-correct, 0.05-0.3-for-wrong
spread, verified pairwise).

The Python files under `training/` remain as the canonical, independently
testable reference for local experimentation (`training_loop.py` still
runs standalone, no server needed) — they're just no longer what actually
executes when a real request comes in. **Any new simulator needs both**:
the Python reference version (for local testing, matching the existing
pattern) and a JS port registered in `JS_SIMULATORS` (for it to actually
work once deployed).

## What's genuinely real and tested here, vs. what's a scaffolded integration point

Being direct about this distinction matters, so it's worth stating plainly
rather than letting the code's confidence-inspiring structure imply more
than what's actually been proven:

### Real, tested, runs correctly right now
- **All 6 `sem_only` domain simulators** — every one has both a real,
  in-process JS version (`backend/simulators/`) and a Python reference
  version (`training/simulators/`), each individually tested for correct
  reward behavior (correct match = 1.0, wrong guesses meaningfully lower,
  verified pairwise across every combination for every domain):
  - `industrialFaultSimulator.js` / `industrial_fault_simulator.py`
  - `medicalDiagnosticsSimulator.js` / `medical_diagnostics_simulator.py`
  - `securityIncidentSimulator.js` / `security_incident_simulator.py`
  - `financialFraudSimulator.js` / `financial_fraud_simulator.py` (includes
    a genuine "not fraud" class, not just fraud-type classification)
  - `scientificDiscoverySimulator.js` / `scientific_discovery_simulator.py`
  - `productionIncidentSimulator.js` / `production_incident_simulator.py`

  All are registered in `JS_SIMULATORS` in `server.js` and confirmed
  reachable through the real registry, not just individually.
- **`training/training_loop.py`** — the real propose/verify/reward loop,
  runnable end to end right now with `python3 training_loop.py --n_scenarios 15`.
  Uses a heuristic offline proposer by default (no API key needed to test
  the mechanism); pass `--use_api` to route proposals through Claude instead.
- **Backend routes** — all 14 routes are real, working Express/Prisma code,
  syntax-validated. The use case registry is seeded with the actual 12 real
  use cases, correctly split 6 sem_only / 6 compiler.
- **Frontend** — genuinely functional and interactive: live polling on
  Scenarios/Demonstrations/Training/Compiler Jobs, real dependency-free SVG
  charts, expandable detail views, filtering, a working Compile action on
  each Demonstration, and Checkpoints wired to the real backend route.
  Every feature individually verified against realistic mocked data
  matching the backend's actual
  response shapes.

### The Skill Compiler pipeline — real for `log` and `screen_recording`, placeholder for the rest

`processCompilerJob` runs a genuinely real, shared pipeline for `log` and
`screen_recording` demonstrations. The key architectural point: **only
Stage 1 (ingestion) differs by modality** — `logPipeline.js` parses a
structured JSON action sequence, `videoPipeline.js` extracts frames from
a real video and infers the action between each consecutive pair via
Claude's vision API. Both produce the exact same observation-sequence
shape (`[{index, action, target, value, raw}, ...]`), so Stages 2-5
(extraction, verification, abstraction, compilation) run completely
unchanged regardless of which modality a demonstration came from —
confirmed directly: fed a simulated video-derived observation sequence
through `logPipeline.js`'s existing, already-tested Stage 5 and it
compiled correctly with zero modification needed.

- **`log` — Stage 1 (ingestion) and Stage 5 (compilation)** are pure,
  deterministic logic — no LLM call, fully tested directly, including
  real error-handling for malformed logs.
- **`screen_recording` — frame extraction** uses `ffmpeg-static`, a
  self-contained npm binary (no `apt-get` needed — the same lesson
  learned the hard way with `poppler-utils` and `python3` elsewhere in
  this project). Genuinely, fully tested end to end: generated a real
  synthetic test video, extracted real frames, confirmed valid JPEG
  output, confirmed a clean error for corrupted input, and confirmed the
  frame-count downsampling logic (caps at 40 frames per video, evenly
  sampled across the whole recording rather than just its start) with no
  duplicate or out-of-range indices.
- **Stages 2-4 (extraction, verification, abstraction) and per-frame
  action inference** call Claude. Their prompt construction is tested
  directly, and the full log-pipeline orchestration was confirmed working
  end to end against a mocked Anthropic client, including deliberately
  fenced responses (```json ... ``` wrapping) — a real, confirmed failure
  mode caught in production and fixed with a shared fence-stripping
  parser used in both `logPipeline.js` and `videoPipeline.js`. What
  couldn't be verified in the environment this was built in: the actual
  LLM reasoning quality for real video frames, since no live API key was
  available there. Test this for real before trusting it in production.
- **`video` (general/physical-world footage) and `motion_capture`
  (robotics joint/pose data) still use the original placeholder** —
  genuinely different, harder problems from "a UI being interacted
  with," not solved here. A job for one of these modalities completes
  with an honest note explaining this, rather than silently producing a
  fake result.

Requires `ANTHROPIC_API_KEY` to be set — the log pipeline calls Claude
directly for three of its five stages.

### File storage — local disk vs. S3

Demonstration files are stored locally by default, which is **ephemeral
on Render** — every redeploy wipes anything previously written there,
while the database record survives fine, since it's in Postgres, not on
disk. This produces a real, confirmed bug: a demonstration uploaded
before any later redeploy becomes unreadable (`ENOENT`) the moment you
try to compile it, even though it still shows up fine in the UI.

Setting `S3_BUCKET`, `AWS_ACCESS_KEY_ID`, and `AWS_SECRET_ACCESS_KEY`
(see `render.yaml`) fixes this properly — new uploads go straight to S3
and survive redeploys. Without them, the app still works exactly as
before, just with the same underlying limitation — the only difference
is a clear, actionable error message instead of a raw stack trace when a
file goes missing.


## Deploying to Render

`render.yaml` at the repo root is a Render Blueprint — it defines the
backend web service and its Postgres database together. On Render:
**New → Blueprint**, point it at this repo, and it provisions both
automatically, running `prisma generate` and `prisma db push` as part of
the build.

Note the blueprint deliberately leaves `ANTHROPIC_API_KEY` commented out —
`server.js` doesn't call Anthropic anywhere yet (the extraction stage is
still a placeholder, see below). Uncomment that block once the extraction
stage is wired to something real.

## Two kinds of training run, shown side by side in the UI

The Training Runs tab now distinguishes two genuinely different things,
badged clearly so they're never confused:

- **Reference** — the original, fast, in-process heuristic loop. Useful
  for a quick mechanism sanity-check, not real model training. Started
  directly from a button in the UI.
- **GRPO** — real training, actually updating Qwen3.8-27B's weights via
  `training/grpo/train_grpo.py`, running on a dedicated GPU pod. Started
  from the command line on that pod (see `training/grpo/README.md`), not
  from a button here — but once started, it creates a real `TrainingRun`
  record and reports live progress back to this exact page automatically,
  via `PATCH /api/training-runs/:id/progress`. Confirmed with a real
  integration test: the script's requests were checked against an actual
  mock server, not just syntax-checked.

The Training Runs tab also now shows a real **data pipeline** view — live
scenario counts per domain, reused from data already loaded elsewhere in
the app, so it's clear what's actually available for training to draw
from before starting a real run.

## Setup — local development

**Backend:**
```
cd backend
npm install
npx prisma generate --schema=./schema.prisma
# set DATABASE_URL in your environment, then:
npx prisma db push --schema=./schema.prisma
npm start   # seeds the 12 use cases automatically on boot, then listens on PORT (default 4001)
```
Real authentication still needs to be added before running this anywhere
beyond local testing — the current `authenticate` middleware is a
development placeholder that accepts every request as a fixed dev user.

**Frontend:**
Served automatically by the backend at `http://localhost:4001/` once it's
running (`npm start` in `backend/`) — no separate step needed. The frontend
talks to whatever origin it's served from (`window.location.origin`), so
this works correctly both locally and once deployed to Render, where
frontend and backend share one origin. Don't open `frontend/index.html`
directly via `file://` — the API calls need a real HTTP origin to resolve.

**Training:**
```
cd training
python3 training_loop.py --n_scenarios 20
```

## Building a simulator for a new domain, if one gets added later

All 6 current `sem_only` use cases have real simulators now, but the shape
is worth documenting for whenever a 7th domain gets added.
`industrial_fault_simulator.py` / `industrialFaultSimulator.js` is the
reference pair every simulator here follows: `sample_intervention()`
/ `sampleIntervention()`, `generate_observations()` / `generateObservations()`,
`verify_proposed_structure()` / `verifyProposedStructure()`. A new domain
means writing this same shape twice — once in Python under
`training/simulators/` for local testing, once in JS under
`backend/simulators/` — then adding the JS module to the `JS_SIMULATORS`
registry in `server.js`, keyed by the use case's slug, so
`/api/scenarios/generate` and training runs can actually call it.
