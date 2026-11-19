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
  call, confirmed against all 32 domains with three real cases each
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

There are now 32 domains with 12 to 15 possible causes each (defined once in
`training/simulators/domains_spec.json`, authored in `build_spec.py`). With that many causes, use
`--n-per-domain 500` as the starting scale: 16,000 total examples (500 x 32 domains = 16,000). The earlier
`200` figure was sized for 4 to 5 causes per domain. Expect to tune this upward based on how training
actually progresses.

To change a domain, edit `build_spec.py`, run `python3 build_spec.py` (it rewrites both copies of the
spec) and then `python3 simulators/test_spec.py`. The probabilities in the spec are hand-set and
illustrative, not estimated from real data. That matters most for the cardiology and safety domains.

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
`mean_reward` is intentionally left null at registration — it comes from the held-out evaluation
below (`eval_sem.py --register-checkpoint-id`), not from training reward.

## Evaluating a checkpoint (`eval_sem.py`)

Training reward does not tell you the model improved. These simulators are
Bernoulli models, so exact accuracy is capped by a Bayes ceiling (about 73% on the iid
suite with the 10-domain spec, 57% to 76% depending on the domain, and 50% on the noisy suite, not 100%; random
guessing is about 7%). The signal space is now 2^13 to 2^18 patterns per domain, so overlap with training is
lower than it used to be (about 67% of eval patterns also appeared in a 5,000-example training set), which
makes the memorisation probe's unseen subset reasonably large. The
harness reports results against that ceiling and probes for memorisation.

```bash
# 1. Train (writes <output-dir>/train_manifest.json; --seed defaults to 1234)
python3 train_grpo.py --n-per-domain 200 --output-dir ./sem-checkpoint-v1 --register-checkpoint ...

# 2. Evaluate the UNTRAINED base model and the trained adapter on the identical item set
python3 eval_sem.py --backend hf --model Qwen/Qwen3.8-27B --out eval_out/base
python3 eval_sem.py --backend hf --model Qwen/Qwen3.8-27B --adapter ./sem-checkpoint-v1 \
    --train-manifest ./sem-checkpoint-v1/train_manifest.json --out eval_out/sem-v1 \
    --register-checkpoint-id <checkpoint id> --backend-url https://<sem-backend>

# 3. Paired comparison
python3 eval_sem.py compare eval_out/base/items.jsonl eval_out/sem-v1/items.jsonl
```

Reports (`report.md`, `report.json`, per-item `items.jsonl`) cover accuracy with 95% CIs,
verifier reward, format-valid rate, per domain and per suite (`iid`, `reordered`,
`paraphrase`, `noisy`), random and Bayes reference scores, and a normalized score
(0 = chance, 1 = ceiling). `--backend bayes|random|first` give reference rows with no GPU;
`--backend predictions` scores completions produced elsewhere; `--dump-set` exports the items.

How to read it:
- A gain over the base model that the paired comparison calls significant is the real signal.
- Normalized score near 1 on `iid` but a large drop on `reordered`, `paraphrase` or `noisy`
  means the model learned the surface form, not the task.
- In the memorisation probe, "unseen" accuracy well below "seen" means memorisation. Unseen
  patterns are rare ones, so that subset is small. Check its `n` before trusting it.
- Mean reward includes partial credit for wrong answers (random guessing scores about 0.35),
  so judge progress by accuracy and the normalized score.

Not verified: the `hf` and `endpoint` backends need a GPU or a served model and have not been
run. Everything else was tested with the reference baselines and synthetic models (a
memoriser and a format-brittle model) to confirm the metrics separate them.
