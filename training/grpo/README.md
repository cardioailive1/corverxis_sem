# SEM GRPO Training — Setup and Usage

Real GRPO training for SEM, targeting Qwen3.8-27B via QLoRA, using
HuggingFace's `trl` library. See `sem-training-architecture.md` (the
design document) for the full reasoning behind every choice here.

## What's genuinely tested here vs. what isn't

Being direct about this, same as everywhere else in this project:

**Genuinely tested, runnable right now, no GPU needed:**
- `dataset.py` — generates real training examples from all 6 domain
  simulators, confirmed to produce a valid HuggingFace `Dataset` with the
  correct `prompt` column trl requires. Run directly: `python3 dataset.py`
- `reward_functions.py` — the actual reward function GRPOTrainer would
  call, confirmed against all 6 domains with three real cases each
  (correct JSON, malformed garbage, JSON wrapped in extra text). Run
  directly: `python3 reward_functions.py`
- **A real bug was caught and fixed while building this**: HuggingFace's
  `Dataset.from_list()` silently unifies differently-shaped dicts across
  domains into one schema, padding missing keys with `None`. Fixed by
  storing `hidden_intervention` as a JSON string instead of a raw dict —
  confirmed via a regression test built directly into `dataset.py`'s
  self-test.

**Written using trl's real, current, verified API — but not run end to
end**, since that needs an actual GPU this environment doesn't have:
- `train_grpo.py`'s `GRPOTrainer`/`GRPOConfig` wiring — every parameter
  name and the reward-function calling convention were checked against
  trl's own current documentation, not guessed from memory. What's
  **not** verified is whether the full training loop actually runs
  correctly against a real 27B model on real hardware — that's the one
  piece that genuinely needs a GPU pod to confirm.

## Docker build — note the build context

```bash
# From the repo root (sem-lab/), NOT from inside training/grpo/:
docker build -f training/grpo/Dockerfile -t sem-grpo-training .
```

The Dockerfile's `COPY` paths assume the repo root as build context —
building from inside `training/grpo/` itself will fail to find the files.

## Running a real training job

This is meant for a dedicated, continuously-running GPU pod (a RunPod Pod,
SSH'd into directly — the same pattern already proven reliable earlier in
this project), not Serverless. GRPO generates multiple live completions
per training step, which doesn't fit a cold-start-per-request model.

```bash
# On the pod, after cloning the repo and building/running the container:
python3 train_grpo.py \
  --n-per-domain 200 \
  --output-dir ./sem-checkpoint-v1 \
  --num-generations 8 \
  --register-checkpoint \
  --backend-url https://your-sem-osc-backend.onrender.com
```

`--n-per-domain 200` means 1,200 total training examples (200 × 6
domains) — a real starting scale, not the toy `--n_scenarios 15` used to
validate the mechanism earlier. Expect to tune this upward based on how
training actually progresses.

## Hardware sizing

Qwen3.8-27B needs ~56GB in bf16 (confirmed when this base model was first
selected for NexGen Pro elsewhere in this project). QLoRA's 4-bit
quantization (the default here, disable with `--no-4bit` only if you have
substantially more VRAM) brings this down meaningfully, but budget for a
single 80GB-class GPU as the realistic minimum — GRPO's multi-sample
generation (`--num-generations 8` by default) adds real activation memory
on top of the base model's footprint, more than plain inference would.

## After training

`train_grpo.py --register-checkpoint` calls the SEM+OSC backend's
`POST /api/checkpoints` route (added specifically to support this — it
didn't exist before) to register the result. Note the registered
`mean_reward` is intentionally left null — it should come from evaluating
the trained model against a held-out scenario set, not training-set
reward, and that evaluation harness doesn't exist yet. Treat that as the
next real piece of work once a checkpoint actually exists to evaluate.
