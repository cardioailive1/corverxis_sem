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

### Explicit integration points, not yet real implementations
Two places in the backend are deliberately left as clear placeholders
rather than faked:

1. **`processCompilerJob`** in `server.js` — cycles through the 6 pipeline
   stages with a timeout in place of real processing. Each stage (ingestion
   parsing, calling SEM for extraction, perturbation-testing verification,
   abstraction, target-specific compilation) is substantial work in its own
   right — see the design document from earlier in this project for what
   each stage actually needs to do. Wiring a real stage in means replacing
   the `setTimeout` placeholder with a call to that stage's actual logic.

This is now the **only** remaining scaffolded integration point — all 6
`sem_only` use cases have real, tested simulators as of the latest update
(see below).

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
