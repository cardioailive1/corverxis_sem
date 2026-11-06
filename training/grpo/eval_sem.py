"""
Held-out evaluation harness for SEM.

Why this exists: training reward is not evidence the model got better. These
simulators are small Bernoulli models, so (a) the best possible exact accuracy
is capped by a computable Bayes ceiling, and (b) there are only a few hundred
distinct observation patterns per domain, so an in-distribution "held-out" set
overlaps heavily with training prompts. This harness therefore reports:

  * accuracy / verifier reward / format-valid rate, per domain and per suite
  * reference scores computed on the SAME items: random, first-option, and the
    Bayes-optimal classifier (the ceiling for exact accuracy)
  * a normalized score  (acc - random) / (bayes - random)  so 0 = chance, 1 = ceiling
  * a memorisation probe: accuracy on prompts seen in training vs unseen
  * robustness suites that change the surface form or the data, not the task:
      iid        same generator + template as training, fresh seed
      reordered  option list and signal list shuffled
      paraphrase different instruction wording (same JSON answer format)
      noisy      each observed signal flipped with prob NOISE_EPS (Bayes ceiling
                 is recomputed for the noisy channel)
  * bootstrap 95% CIs and a paired comparison between two models

Usage
  # reference baselines only (no GPU):
  python3 eval_sem.py --backend bayes --out eval_out/bayes
  # untrained base model, then the trained adapter, on the identical item set:
  python3 eval_sem.py --backend hf --model Qwen/Qwen3.8-27B --out eval_out/base
  python3 eval_sem.py --backend hf --model Qwen/Qwen3.8-27B --adapter ./sem-checkpoint-v1 \
        --train-manifest ./sem-checkpoint-v1/train_manifest.json --out eval_out/sem-v1 \
        --register-checkpoint-id <id> --backend-url https://<sem-backend>
  python3 eval_sem.py compare eval_out/base/items.jsonl eval_out/sem-v1/items.jsonl

  # score completions produced elsewhere (id + completion per line):
  python3 eval_sem.py --backend predictions --predictions preds.jsonl --out eval_out/x
  # export the item set for use elsewhere:  --dump-set only
"""
import argparse, hashlib, json, math, os, random, sys

sys.path.insert(0, os.path.dirname(__file__))
from dataset import DOMAIN_INSTRUCTIONS, build_prompt, DOMAIN_MODULES, pattern_id
from reward_functions import parse_completion_to_structure

SUITES = ["iid", "reordered", "paraphrase", "noisy"]
NOISE_EPS = 0.10
DEFAULT_EVAL_SEED = 99991
DEFAULT_P = {  # per-simulator fallback probability for signals missing from a profile
    "industrial-fault-diagnosis": 0.05, "medical-diagnostics": 0.03,
    "security-incident-investigation": 0.03, "financial-fraud-investigation": 0.02,
    "scientific-discovery": 0.05, "production-incident-rootcause": 0.03,
}
PARAPHRASES = [
    "Task: {label}. Candidate causes: {opts}. Signals that were observed: {sig}. "
    "Which single cause is most likely? Reply with ONLY a JSON object like {{\"{key}\": \"<answer>\"}} and nothing else.",
    "Diagnose this {label} case. Observed: {sig}. The cause must be one of: {opts}. "
    "Output exactly one JSON object, {{\"{key}\": \"<cause>\"}}, with no other text.",
    "Given these findings ({sig}) in a {label} scenario, choose the most probable cause from [{opts}]. "
    "Answer as JSON only: {{\"{key}\": \"<cause>\"}}.",
]


def sha(s): return hashlib.sha1(s.encode()).hexdigest()[:16]


def profile_of(domain):
    m = DOMAIN_MODULES[domain]
    prof = getattr(m, "SYMPTOM_PROFILES", None) or getattr(m, "SIGNAL_PROFILES")
    sigs = getattr(m, "ALL_SYMPTOMS", None) or getattr(m, "ALL_SIGNALS")
    return prof, sigs


def bayes_predict(domain, observations, eps=0.0):
    """MAP cause under uniform prior and the simulator's own Bernoulli profiles
    (optionally through a symmetric flip channel with prob eps)."""
    prof, sigs = profile_of(domain)
    default = DEFAULT_P[domain]
    best, best_ll = None, -1e18
    for cause in DOMAIN_INSTRUCTIONS[domain][2]:
        ll = 0.0
        for s in sigs:
            p = prof[cause].get(s, default)
            p = p * (1 - eps) + (1 - p) * eps
            ll += math.log(p if observations[s] else 1 - p)
        if ll > best_ll: best, best_ll = cause, ll
    return best


def render_prompt(suite, domain, obs, rng):
    label, key, options = DOMAIN_INSTRUCTIONS[domain]
    if suite in ("iid", "noisy"):
        return build_prompt(domain, obs)
    present = [k for k, v in obs.items() if v]
    if suite == "reordered":
        opts = list(options); rng.shuffle(opts); rng.shuffle(present)
        sig = ", ".join(present) if present else "no significant signals — all readings normal"
        return (f"You are performing {label}. Possible causes: {', '.join(opts)}. Observed signals: {sig}. "
                f"Propose the single most likely cause. "
                f'Respond with ONLY a JSON object in the form {{"{key}": "<your answer>"}}, nothing else.')
    if suite == "paraphrase":
        opts = list(options); rng.shuffle(opts)
        sig = ", ".join(present) if present else "none (all readings normal)"
        return rng.choice(PARAPHRASES).format(label=label, opts=", ".join(opts), sig=sig, key=key)
    raise ValueError(suite)


def build_eval_set(n_per_domain, seed, train_hashes=None):
    items = []
    for suite in SUITES:
        for domain, module in DOMAIN_MODULES.items():
            rng = random.Random(f"{seed}|{suite}|{domain}")
            key = DOMAIN_INSTRUCTIONS[domain][1]
            for i in range(n_per_domain):
                hidden = module.sample_intervention(rng)
                obs = module.generate_observations(hidden, rng)
                eps = NOISE_EPS if suite == "noisy" else 0.0
                if eps:
                    obs = {s: (not v) if rng.random() < eps else v for s, v in obs.items()}
                prompt = render_prompt(suite, domain, obs, rng)
                # signature of the underlying observation pattern, independent of surface wording
                pattern = pattern_id(domain, obs)
                items.append({
                    "id": f"{suite}:{domain}:{i}", "suite": suite, "domain": domain,
                    "prompt": prompt, "hidden": json.dumps(hidden), "key": key,
                    "obs": obs, "eps": eps, "pattern": pattern,
                    "seen_in_train": (pattern in train_hashes) if train_hashes is not None else None,
                })
    return items


def train_pattern_hashes(manifest_path):
    m = json.load(open(manifest_path))
    return set(m["patterns"])


# ---------------- backends: item -> completion text ----------------
def backend_fn(name, args):
    if name == "bayes":
        return lambda it: json.dumps({it["key"]: bayes_predict(it["domain"], it["obs"], it["eps"])})
    if name == "random":
        r = random.Random("rand|" + str(args.seed))
        return lambda it: json.dumps({it["key"]: r.choice(DOMAIN_INSTRUCTIONS[it["domain"]][2])})
    if name == "first":
        return lambda it: json.dumps({it["key"]: DOMAIN_INSTRUCTIONS[it["domain"]][2][0]})
    if name == "predictions":
        preds = {}
        for line in open(args.predictions):
            if line.strip():
                d = json.loads(line); preds[d["id"]] = d["completion"]
        return lambda it: preds.get(it["id"], "")
    raise ValueError(name)


def generate_hf(items, args):
    """Greedy decoding of the RAW prompt string, exactly as GRPOTrainer saw it during
    training (plain-string prompts get no chat template). Untested here: needs a GPU."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    tok = AutoTokenizer.from_pretrained(args.model, padding_side="left")
    if tok.pad_token is None: tok.pad_token = tok.eos_token
    q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                           bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True) if not args.no_4bit else None
    model = AutoModelForCausalLM.from_pretrained(args.model, quantization_config=q,
                                                 torch_dtype=torch.bfloat16, device_map="auto")
    if args.adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, args.adapter)
    model.eval()
    out = {}
    for i in range(0, len(items), args.batch_size):
        chunk = items[i:i + args.batch_size]
        enc = tok([c["prompt"] for c in chunk], return_tensors="pt", padding=True).to(model.device)
        with torch.no_grad():
            gen = model.generate(**enc, max_new_tokens=args.max_new_tokens, do_sample=False,
                                 pad_token_id=tok.pad_token_id)
        for c, g in zip(chunk, gen):
            out[c["id"]] = tok.decode(g[enc["input_ids"].shape[1]:], skip_special_tokens=True)
        print(f"  generated {min(i + args.batch_size, len(items))}/{len(items)}", flush=True)
    return out


def generate_endpoint(items, args):
    """OpenAI-compatible /v1/completions (raw prompt, temperature 0), e.g. vLLM serving the adapter."""
    import requests
    hdr = {"Authorization": f"Bearer {os.environ['EVAL_API_KEY']}"} if os.environ.get("EVAL_API_KEY") else {}
    out = {}
    for n, it in enumerate(items, 1):
        r = requests.post(args.endpoint.rstrip("/") + "/v1/completions", headers=hdr, timeout=120, json={
            "model": args.model or "default", "prompt": it["prompt"], "max_tokens": args.max_new_tokens, "temperature": 0})
        out[it["id"]] = r.json()["choices"][0]["text"] if r.ok else ""
        if n % 100 == 0: print(f"  {n}/{len(items)}", flush=True)
    return out


# ---------------- scoring ----------------
def score_item(it, completion):
    module = DOMAIN_MODULES[it["domain"]]
    hidden = json.loads(it["hidden"])
    options = DOMAIN_INSTRUCTIONS[it["domain"]][2]
    parsed = parse_completion_to_structure(completion or "")
    valid = isinstance(parsed, dict) and parsed.get(it["key"]) in options
    reward = 0.0
    if parsed is not None:
        reward = float(module.verify_proposed_structure(parsed, hidden, random.Random(it["id"])))
    correct = bool(valid and parsed[it["key"]] == hidden[it["key"]])
    return {"valid": bool(valid), "correct": correct, "reward": reward, "completion": (completion or "")[:300]}


def mean(xs): xs = list(xs); return sum(xs) / len(xs) if xs else float("nan")


def boot_ci(vals, n=1000, seed=0):
    if not vals: return (float("nan"), float("nan"))
    r = random.Random(seed); m = len(vals); means = []
    for _ in range(n):
        means.append(sum(vals[r.randrange(m)] for _ in range(m)) / m)
    means.sort(); return (means[int(0.025 * n)], means[int(0.975 * n) - 1])


def summarize(rows, refs):
    """rows: scored items (dicts with suite/domain/correct/reward/valid/seen_in_train).
    refs: {'bayes': {id: correct}} for the same ids."""
    rep = {"overall": {}, "by_suite": {}, "by_domain": {}, "by_suite_domain": {}, "memorisation_probe": {}}
    def agg(sub):
        acc = [1.0 if r["correct"] else 0.0 for r in sub]
        lo, hi = boot_ci(acc)
        K = mean(1.0 / len(DOMAIN_INSTRUCTIONS[r["domain"]][2]) for r in sub)
        bay = mean(1.0 if refs["bayes"][r["id"]] else 0.0 for r in sub)
        a = mean(acc)
        norm = (a - K) / (bay - K) if bay > K else float("nan")
        return {"n": len(sub), "accuracy": round(a, 4), "accuracy_ci95": [round(lo, 4), round(hi, 4)],
                "mean_reward": round(mean(r["reward"] for r in sub), 4),
                "format_valid": round(mean(1.0 if r["valid"] else 0.0 for r in sub), 4),
                "random_accuracy": round(K, 4), "bayes_accuracy": round(bay, 4),
                "normalized_score": round(norm, 4)}
    rep["overall"] = agg(rows)
    for s in SUITES:
        sub = [r for r in rows if r["suite"] == s]
        if sub: rep["by_suite"][s] = agg(sub)
    for d in DOMAIN_MODULES:
        sub = [r for r in rows if r["domain"] == d]
        if sub: rep["by_domain"][d] = agg(sub)
    # memorisation probe: iid suite only, split by whether the observation pattern was in training
    iid = [r for r in rows if r["suite"] == "iid" and r["seen_in_train"] is not None]
    seen = [r for r in iid if r["seen_in_train"]]; unseen = [r for r in iid if not r["seen_in_train"]]
    if iid:
        rep["memorisation_probe"] = {
            "seen_pattern_fraction": round(len(seen) / len(iid), 4),
            "seen": agg(seen) if seen else None, "unseen": agg(unseen) if unseen else None,
            "note": "Accuracy on unseen patterns far below seen patterns suggests memorisation; "
                    "similar accuracy suggests the model learned the mapping."}
    iid_s, robust = rep["by_suite"].get("iid"), [rep["by_suite"][s] for s in SUITES[1:] if s in rep["by_suite"]]
    if iid_s and robust:
        rep["robustness_drop"] = {s: round(iid_s["normalized_score"] - rep["by_suite"][s]["normalized_score"], 4)
                                  for s in SUITES[1:] if s in rep["by_suite"]}
    return rep


def to_markdown(name, rep):
    L = [f"# SEM evaluation — {name}", "",
         "Normalized score: 0 = random chance, 1 = Bayes-optimal ceiling for that suite.", "",
         "| Slice | n | Accuracy (95% CI) | Mean reward | Format valid | Random | Bayes ceiling | Normalized |", "|---|---|---|---|---|---|---|---|"]
    def row(label, a):
        L.append(f"| {label} | {a['n']} | {a['accuracy']:.3f} ({a['accuracy_ci95'][0]:.3f}–{a['accuracy_ci95'][1]:.3f}) | "
                 f"{a['mean_reward']:.3f} | {a['format_valid']:.3f} | {a['random_accuracy']:.3f} | {a['bayes_accuracy']:.3f} | {a['normalized_score']:.3f} |")
    row("**overall**", rep["overall"])
    for s, a in rep["by_suite"].items(): row(f"suite: {s}", a)
    for d, a in rep["by_domain"].items(): row(f"domain: {d}", a)
    mp = rep.get("memorisation_probe")
    if mp:
        L += ["", "## Memorisation probe (iid suite)", f"Fraction of eval patterns also seen in training: {mp['seen_pattern_fraction']}"]
        for k in ("seen", "unseen"):
            if mp.get(k): L.append(f"- {k}: accuracy {mp[k]['accuracy']:.3f} (n={mp[k]['n']}), normalized {mp[k]['normalized_score']:.3f}")
    if rep.get("robustness_drop"):
        L += ["", "## Robustness (normalized-score drop vs iid; positive = worse)"] + [f"- {k}: {v:+.3f}" for k, v in rep["robustness_drop"].items()]
    return "\n".join(L) + "\n"


def register(backend_url, ckpt_id, rep):
    import requests
    hdr = {"Authorization": f"Bearer {os.environ['SEM_API_KEY']}"} if os.environ.get("SEM_API_KEY") else {}
    o = rep["overall"]
    try:
        r = requests.patch(f"{backend_url}/api/checkpoints/{ckpt_id}/eval", headers=hdr, timeout=15, json={
            "mean_reward": rep["by_suite"].get("iid", o)["mean_reward"]})
        print("Registered eval on checkpoint:", r.status_code, r.text[:200])
    except Exception as e:
        print("Could not register eval (report files are still written):", e)


def cmd_compare(a_path, b_path, n=2000):
    A = {d["id"]: d for d in map(json.loads, open(a_path))}
    B = {d["id"]: d for d in map(json.loads, open(b_path))}
    ids = sorted(set(A) & set(B))
    if not ids: sys.exit("no overlapping item ids — were both runs made with the same --n-per-domain/--seed?")
    diffs = [(1.0 if B[i]["correct"] else 0.0) - (1.0 if A[i]["correct"] else 0.0) for i in ids]
    r = random.Random(1); m = len(diffs); bs = sorted(sum(diffs[r.randrange(m)] for _ in range(m)) / m for _ in range(n))
    lo, hi = bs[int(0.025 * n)], bs[int(0.975 * n) - 1]
    b_only = sum(1 for d in diffs if d > 0); a_only = sum(1 for d in diffs if d < 0)
    print(f"Paired on {m} items: B - A accuracy = {mean(diffs):+.4f} (95% CI {lo:+.4f} to {hi:+.4f}); "
          f"B-only correct {b_only}, A-only correct {a_only}")
    print("B is better with 95% confidence." if lo > 0 else "A is better with 95% confidence." if hi < 0
          else "Difference is not statistically distinguishable at this sample size.")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "compare":
        return cmd_compare(sys.argv[2], sys.argv[3])
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--backend", default="bayes", choices=["bayes", "random", "first", "hf", "endpoint", "predictions"])
    p.add_argument("--n-per-domain", type=int, default=100, help="items per domain per suite (default 100 -> 2,400 total; use 300+ for tight CIs)")
    p.add_argument("--seed", type=int, default=DEFAULT_EVAL_SEED)
    p.add_argument("--train-manifest", help="train_manifest.json written by train_grpo.py (enables the memorisation probe)")
    p.add_argument("--out", default="eval_out/run")
    p.add_argument("--dump-set", action="store_true", help="only write eval_set.jsonl and exit")
    p.add_argument("--model"); p.add_argument("--adapter"); p.add_argument("--no-4bit", action="store_true")
    p.add_argument("--batch-size", type=int, default=16); p.add_argument("--max-new-tokens", type=int, default=64)
    p.add_argument("--endpoint"); p.add_argument("--predictions")
    p.add_argument("--register-checkpoint-id"); p.add_argument("--backend-url", default=os.environ.get("SEM_BACKEND_URL", "http://localhost:4001"))
    args = p.parse_args()

    train_hashes = train_pattern_hashes(args.train_manifest) if args.train_manifest else None
    items = build_eval_set(args.n_per_domain, args.seed, train_hashes)
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "eval_set.jsonl"), "w") as f:
        for it in items: f.write(json.dumps({k: it[k] for k in ("id", "suite", "domain", "prompt", "hidden")}) + "\n")
    print(f"Eval set: {len(items)} items, seed {args.seed}")
    if args.dump_set: return

    if args.backend == "hf": comps = generate_hf(items, args)
    elif args.backend == "endpoint": comps = generate_endpoint(items, args)
    else:
        fn = backend_fn(args.backend, args); comps = {it["id"]: fn(it) for it in items}

    bayes_fn = backend_fn("bayes", args)
    refs = {"bayes": {it["id"]: score_item(it, bayes_fn(it))["correct"] for it in items}}
    rows = []
    for it in items:
        s = score_item(it, comps.get(it["id"], ""))
        rows.append({**{k: it[k] for k in ("id", "suite", "domain", "seen_in_train")}, **s})
    with open(os.path.join(args.out, "items.jsonl"), "w") as f:
        for r in rows: f.write(json.dumps(r) + "\n")
    rep = summarize(rows, refs)
    rep["config"] = {"backend": args.backend, "model": args.model, "adapter": args.adapter, "seed": args.seed,
                     "n_per_domain": args.n_per_domain, "noise_eps": NOISE_EPS, "suites": SUITES}
    json.dump(rep, open(os.path.join(args.out, "report.json"), "w"), indent=2)
    md = to_markdown(os.path.basename(args.out.rstrip("/")), rep)
    open(os.path.join(args.out, "report.md"), "w").write(md); print(md)
    if args.register_checkpoint_id: register(args.backend_url, args.register_checkpoint_id, rep)


if __name__ == "__main__":
    main()
