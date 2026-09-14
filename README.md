# SEM+OSC

A standalone lab (SEM+OSC — Structural Extraction Model + One-Shot Compiler) for developing, training, and deploying SEM (Structural
Extraction Model) and the One-Shot Skill Compiler. **Shares no code with
NexGen Lab** — separate backend, separate frontend, separate database.

## What's genuinely real and tested here, vs. what's a scaffolded integration point

Being direct about this distinction matters, so it's worth stating plainly
rather than letting the code's confidence-inspiring structure imply more
than what's actually been proven:

### Real, tested, runs correctly right now
- **`training/simulators/industrial_fault_simulator.py`** — a real, working
  toy simulator. Actually generates scenarios, actually verifies proposed
  structures against hidden ground truth, with a genuinely sensible reward
  spread (correct = 1.0, wrong guesses = 0.05-0.3, never conflated). Run its
  self-test directly: `python3 industrial_fault_simulator.py`
- **`training/training_loop.py`** — the real propose/verify/reward loop,
  runnable end to end right now with `python3 training_loop.py --n_scenarios 15`.
  Uses a heuristic offline proposer by default (no API key needed to test
  the mechanism); pass `--use_api` to route proposals through Claude instead.
- **`training/run_single_scenario.py`** — the CLI wrapper the backend job
  system actually calls; tested directly from the command line, confirmed
  working.
- **Backend routes** — all 13 routes are real, working Express/Prisma code,
  syntax-validated. The use case registry is seeded with the actual 12 real
  use cases, correctly split 6 sem_only / 6 compiler.
- **Frontend** — genuinely functional, all 6 modules render correctly,
  tested against realistic mocked data matching the backend's actual
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

2. **Domain simulators beyond the one industrial-fault-diagnosis example** —
   the other 5 sem_only use cases (medical diagnostics, security incident
   investigation, financial fraud, scientific discovery, production
   incidents) each need their own simulator, built the same way as the
   reference one. This is real, domain-specific engineering work — a
   security-incident simulator and a medical-diagnostics simulator share
   almost nothing in actual implementation, only the same *shape* (hidden
   intervention → generate observations → verify proposals against
   perturbation).

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
Open `frontend/index.html` directly, or serve it — it talks to
`http://localhost:4001` by default (see the `API` constant near the top of
the `<script>` block).

**Training:**
```
cd training
python3 training_loop.py --n_scenarios 20
```

## Building the second simulator, as a template for the rest

`industrial_fault_simulator.py` is the reference shape every other
simulator should follow: `sample_intervention()`, `generate_observations()`,
`verify_proposed_structure()`. Building out medical diagnostics next would
mean writing this same three-function shape against a real (even if
simplified) model of symptom-to-condition relationships, then registering
it via the `UseCase.simulatorSpec` field so `/api/scenarios/generate` can
call it.
