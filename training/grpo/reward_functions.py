"""
The reward function GRPOTrainer actually calls during training.

Matches trl's current, confirmed reward-function signature:
    def reward_fn(completions, **kwargs) -> list[float]
where `completions` is a list of raw model output strings, and any extra
columns in the training dataset (besides "prompt") arrive as matching lists
inside **kwargs — this is how the ground-truth intervention and which
domain's verifier to use get passed through per-example.

This file deliberately does NOT reimplement any domain logic — it imports
and reuses the same six simulator modules already built and tested under
training/simulators/, so the reward signal during real training is
identical to what's already been validated, not a second, drifting copy.
"""
import json
import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "simulators"))
import industrial_fault_simulator as industrial_fault_diagnosis
import medical_diagnostics_simulator as medical_diagnostics
import security_incident_simulator as security_incident_investigation
import financial_fraud_simulator as financial_fraud_investigation
import scientific_discovery_simulator as scientific_discovery
import production_incident_simulator as production_incident_rootcause

DOMAIN_MODULES = {
    "industrial-fault-diagnosis": industrial_fault_diagnosis,
    "medical-diagnostics": medical_diagnostics,
    "security-incident-investigation": security_incident_investigation,
    "financial-fraud-investigation": financial_fraud_investigation,
    "scientific-discovery": scientific_discovery,
    "production-incident-rootcause": production_incident_rootcause,
}


def parse_completion_to_structure(completion: str) -> dict | None:
    """The model is prompted to respond with ONLY a JSON object. This
    parses that — with a regex fallback for the very common real-world
    case where a model wraps its answer in a little extra text despite
    instructions not to. Returns None (not a crash) if genuinely
    unparseable, which the reward function below turns into 0.0 — a
    real, intentional penalty for malformed output, not a bug to hide."""
    completion = completion.strip()
    try:
        return json.loads(completion)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[^{}]*\}", completion)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


def sem_reward(completions: list[str], hidden_intervention: list[str], domain: list[str], **kwargs) -> list[float]:
    """The actual reward function passed to GRPOTrainer(reward_funcs=[...]).
    hidden_intervention and domain arrive as extra dataset columns — see
    dataset.py for where these get attached per training example.
    hidden_intervention arrives as a JSON string, not a raw dict — see
    dataset.py's comment on why (HF Dataset schema unification pollutes
    raw dicts with other domains' keys set to None)."""
    rewards = []
    for completion, true_intervention_json, dom in zip(completions, hidden_intervention, domain):
        module = DOMAIN_MODULES.get(dom)
        if module is None:
            rewards.append(0.0)   # unknown domain — should never happen if dataset.py is correct, but never crash training over it
            continue
        try:
            true_intervention = json.loads(true_intervention_json)
        except (json.JSONDecodeError, TypeError):
            rewards.append(0.0)   # malformed ground truth would be a real bug in dataset construction, not the model's fault — but still shouldn't crash training
            continue
        proposed = parse_completion_to_structure(completion)
        if proposed is None:
            rewards.append(0.0)
            continue
        reward = module.verify_proposed_structure(proposed, true_intervention)
        rewards.append(float(reward))
    return rewards


if __name__ == "__main__":
    # Self-test: confirm the bridge behaves correctly before it's ever
    # wired into real GRPO training — genuinely runnable, no GPU needed.
    import random
    rng = random.Random(7)

    print("Testing sem_reward() against real scenarios from all 6 domains...")
    all_passed = True
    for domain, module in DOMAIN_MODULES.items():
        intervention = module.sample_intervention(rng)
        # A perfect completion (correctly formatted, correct answer)
        correct_completion = json.dumps(intervention)
        # A malformed completion (not valid JSON at all)
        garbage_completion = "I think it's probably the first one, definitely."
        # A wrapped completion (valid JSON, but with extra text — the regex fallback case)
        key = list(intervention.keys())[0]
        wrapped_completion = f"Based on the evidence, my answer is: {json.dumps(intervention)}. I'm confident."

        rewards = sem_reward(
            [correct_completion, garbage_completion, wrapped_completion],
            [json.dumps(intervention), json.dumps(intervention), json.dumps(intervention)],
            [domain, domain, domain],
        )
        ok = rewards[0] == 1.0 and rewards[1] == 0.0 and rewards[2] == 1.0
        status = "✓" if ok else "✗ FAIL"
        if not ok: all_passed = False
        print(f"  {status} {domain:35s} correct={rewards[0]} garbage={rewards[1]} wrapped-in-text={rewards[2]}")

    print()
    print("All domains passed ✓" if all_passed else "SOME DOMAINS FAILED — see above")
    assert all_passed
