# SI-SEM Diagnose — product UI

The customer-facing app for the trained SI-SEM (Super Intelligence-SEM) model. It is separate from the Lab UI (`../frontend/`, used to
build, train and evaluate). It is a static site with no build step and only ever calls `/api/product/*`.

## What users do
Either describe the problem in plain language (chat) or use the manual form below it:
- **Chat.** The user types something like "the pump is grinding and shaking". A general language model (Claude,
  needs `ANTHROPIC_API_KEY` on the backend) picks out the domain and signals, SI-SEM gives the cause, and the
  language model words the reply. The page shows exactly what was understood, and the picker below is filled in so
  the user can correct it and press Diagnose. The cause always comes from SI-SEM (or the labelled fallback), never
  from the language model's own judgement. Each chat message costs 2 language-model calls (3 when SI-SEM is not live).
- **Form.** The steps below.

1. Sign in with an access key.
2. Pick a domain: industrial fault, medical, security, fraud, scientific, production incident, cardiology and ECG, network outage, supply chain, or energy/mining/aviation safety. Each has 13 to 14 possible causes.
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
  falls back to a general Claude model and labels the answer "Fallback: general model, not SI-SEM". Set
  `SEM_PRODUCT_ALLOW_FALLBACK=false` to return an error instead.
- The served model is one endpoint. Activating a different checkpoint in the Lab changes the label shown, not
  the weights being served. Redeploy or swap the adapter on the endpoint to match.
- Reference probabilities come from the simulators' own model with equal priors. They are context, not the
  model's confidence.
- Domains, causes and signals are read from the same `domains_spec.json` the training uses. The cardiology and safety domains are illustrative simulators with hand-set probabilities, not clinical or regulatory tools.
- The task is the narrow one SI-SEM was trained on: choose one cause from a fixed list given observed signals.
  It does not analyse free-form logs or recordings.
- Chat limits: 1,500 characters per message. Signals or domains the language model invents are discarded. If
  `ANTHROPIC_API_KEY` is missing, chat returns an error and the form still works.
- Access keys are shared secrets, rate limited to 30 requests/min per key. There are no user accounts yet.

## Tests
`node --test product/productApi.test.js` from `backend/`. The prompt text is checked against
`training/grpo/dataset.py` for a sample of 3,173 signal combinations across all 40 domains (`python3 training/simulators/test_spec.py parity.json`).

## Photos and videos

The page can read a photo or a short video: the user attaches it, and a vision-language model reports which of the
domain's signals are visibly present, plus a short description of what it sees. Those become pre-selected observations
that the user confirms or edits before diagnosing. The vision model never names the cause. SI-SEM does that, from the
confirmed signals, exactly as before.

- Photos: up to 8, resized in the browser to JPEG (1024 px longest side).
- Video: 6 frames are sampled evenly across the clip in the browser, so the model sees the frames, not the motion or sound.
  (The Qwen3.8 model card also describes native `video_url` input on vLLM; wiring that in is a possible later step.)
- Text goes with it: the chat and the manual signal list work alongside the image.
- Nothing is stored. Media is held in memory, sent to the vision model, and dropped.
- Serving: set `SEM_VISION_URL` to an OpenAI-compatible server hosting a vision-language model (the model card for
  Qwen/Qwen3.8-27B says `vllm serve Qwen/Qwen3.8-27B` accepts `image_url` parts). `SEM_VISION_MODEL` and `SEM_VISION_API_KEY`
  are optional. Without `SEM_VISION_URL`, a labelled Claude fallback is used if `ANTHROPIC_API_KEY` is set. With neither,
  the photo card is hidden.

What this is not: SI-SEM itself was trained on text observations only. Reading images is done by the vision model in
front of it. Many signals (a sound, a reading, a trend) cannot be seen in a photo, so the user adds those. Detection quality
has not been measured on real photos. See `collect/` for how labelled real cases are gathered.
