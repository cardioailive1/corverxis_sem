# SEM Diagnose — product UI

The customer-facing app for the trained SEM model. It is separate from the Lab UI (`../frontend/`, used to
build, train and evaluate). It is a static site with no build step and only ever calls `/api/product/*`.

## What users do
1. Sign in with an access key.
2. Pick a domain (industrial fault, medical, security, fraud, scientific, production incident).
3. Tick the signals they observe and press Diagnose.
4. See the model's most likely cause, which model answered, and reference probabilities for context.

## Deploy
1. Backend env: `SEM_PRODUCT_API_KEYS` (comma separated, one per customer) and `SEM_INFERENCE_URL`
   (plus `SEM_INFERENCE_KIND` = `openai` | `hf` | `runpod`, and the matching key).
2. Serve the trained adapter. `openai` kind expects an OpenAI-compatible `/v1/completions` server (for example
   vLLM with the LoRA adapter). Use the base model name in `SEM_INFERENCE_MODEL` if your server needs it.
3. In the Lab UI, Checkpoints tab, **Activate** the checkpoint. The product shows its version and held-out
   score (`mean_reward` set by `training/grpo/eval_sem.py`).
4. Edit `config.js` so `SEM_API_BASE` is the backend URL, then deploy `product/` as a static site (`render.yaml`
   defines `sem-product-ui`).

## Behaviour to know
- The model is only used when a checkpoint is active AND `SEM_INFERENCE_URL` is set. Otherwise the product
  falls back to a general Claude model and labels the answer "Fallback: general model, not SEM". Set
  `SEM_PRODUCT_ALLOW_FALLBACK=false` to return an error instead.
- The served model is one endpoint. Activating a different checkpoint in the Lab changes the label shown, not
  the weights being served. Redeploy or swap the adapter on the endpoint to match.
- Reference probabilities come from the simulators' own model with equal priors. They are context, not the
  model's confidence.
- The task is the narrow one SEM was trained on: choose one cause from a fixed list given observed signals.
  It does not analyse free-form logs or recordings.
- Access keys are shared secrets, rate limited to 30 requests/min per key. There are no user accounts yet.

## Tests
`node --test product/productApi.test.js` from `backend/`. The prompt text is checked against
`training/grpo/dataset.py` for all 896 signal combinations across the six domains.
