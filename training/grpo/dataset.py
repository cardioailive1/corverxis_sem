"""
Builds the training dataset GRPOTrainer actually trains against.

GRPOTrainer requires a dataset with a "prompt" column (confirmed against
trl's current docs). Any additional columns pass through to the reward
function as **kwargs — this is how `hidden_intervention` and `domain`
reach reward_functions.py's sem_reward() per-example.
"""
import sys
import os
import json
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "simulators"))
import industrial_fault_simulator
import medical_diagnostics_simulator
import security_incident_simulator
import financial_fraud_simulator
import scientific_discovery_simulator
import production_incident_simulator

DOMAIN_MODULES = {
    "industrial-fault-diagnosis": industrial_fault_simulator,
    "medical-diagnostics": medical_diagnostics_simulator,
    "security-incident-investigation": security_incident_simulator,
    "financial-fraud-investigation": financial_fraud_simulator,
    "scientific-discovery": scientific_discovery_simulator,
    "production-incident-rootcause": production_incident_simulator,
}

# One instruction template per domain — genuinely different phrasing per
# domain rather than a single generic template, since the actual key name
# the model needs to output differs (e.g. "condition" for medical,
# "attack_vector" for security) and the model needs to know that.
DOMAIN_INSTRUCTIONS = {
    "industrial-fault-diagnosis": ("industrial fault diagnosis", "failed_component", industrial_fault_simulator.COMPONENTS),
    "medical-diagnostics": ("medical diagnostics", "condition", medical_diagnostics_simulator.CONDITIONS),
    "security-incident-investigation": ("security incident investigation", "attack_vector", security_incident_simulator.ATTACK_VECTORS),
    "financial-fraud-investigation": ("financial fraud investigation", "cause", financial_fraud_simulator.CAUSES),
    "scientific-discovery": ("scientific discovery", "mechanism", scientific_discovery_simulator.MECHANISMS),
    "production-incident-rootcause": ("production incident root-causing", "root_cause", production_incident_simulator.ROOT_CAUSES),
}


def build_prompt(domain: str, observations: dict) -> str:
    domain_label, key_name, options = DOMAIN_INSTRUCTIONS[domain]
    present = [k for k, v in observations.items() if v]
    signals_text = ", ".join(present) if present else "no significant signals — all readings normal"
    return (
        f"You are performing {domain_label}. Possible causes: {', '.join(options)}. "
        f"Observed signals: {signals_text}. "
        f"Propose the single most likely cause. "
        f'Respond with ONLY a JSON object in the form {{"{key_name}": "<your answer>"}}, nothing else.'
    )


def generate_training_examples(n_per_domain: int, seed: int = None) -> list[dict]:
    """Generates n_per_domain scenarios from EVERY domain, mixed together —
    training across all 6 simulators in one run, not one domain at a time,
    so the model learns the general skill rather than overfitting to a
    single domain's signal patterns."""
    rng = random.Random(seed)
    examples = []
    for domain, module in DOMAIN_MODULES.items():
        for _ in range(n_per_domain):
            intervention = module.sample_intervention(rng)
            observations = module.generate_observations(intervention, rng)
            examples.append({
                "prompt": build_prompt(domain, observations),
                # Stored as a JSON string, not a raw dict — HuggingFace's
                # Dataset.from_list() unifies heterogeneous dict schemas
                # across rows into one superset schema with None-padding
                # for missing keys (confirmed directly: a mixed-domain
                # dataset's hidden_intervention rows came back polluted
                # with every other domain's key names set to None). A
                # JSON string sidesteps that entirely — Arrow just stores
                # it as a string, no schema unification to go wrong.
                "hidden_intervention": json.dumps(intervention),
                "domain": domain,
            })
    rng.shuffle(examples)   # mixed order, not grouped by domain — avoids the model learning "the last N examples are always this domain"
    return examples


def build_hf_dataset(n_per_domain: int, seed: int = None):
    """Returns an actual datasets.Dataset, ready to pass to GRPOTrainer as
    train_dataset. Import of `datasets` is deliberately local — this
    module's core logic (generate_training_examples) is testable without
    that dependency installed at all, only this specific function needs it."""
    from datasets import Dataset
    examples = generate_training_examples(n_per_domain, seed)
    return Dataset.from_list(examples)


if __name__ == "__main__":
    # Self-test — genuinely runnable without GPU or the datasets library.
    examples = generate_training_examples(n_per_domain=5, seed=42)
    print(f"Generated {len(examples)} examples (expected {5 * len(DOMAIN_MODULES)})")
    assert len(examples) == 5 * len(DOMAIN_MODULES)

    domains_seen = set(e["domain"] for e in examples)
    print(f"Domains represented: {len(domains_seen)} (expected {len(DOMAIN_MODULES)})")
    assert domains_seen == set(DOMAIN_MODULES.keys())

    sample = examples[0]
    print()
    print("Sample example:")
    print(f"  domain: {sample['domain']}")
    print(f"  hidden_intervention (JSON string): {sample['hidden_intervention']}")
    print(f"  prompt: {sample['prompt'][:200]}...")

    # Confirm hidden_intervention round-trips correctly as JSON, and is
    # a clean, single-key dict — not polluted with other domains' keys.
    parsed = json.loads(sample["hidden_intervention"])
    print(f"  parses back to: {parsed}")
    assert len(parsed) == 1, f"Expected a single-key dict, got {len(parsed)} keys — schema pollution regression"

    # Confirm every example has all 3 required columns
    all_valid = all("prompt" in e and "hidden_intervention" in e and "domain" in e for e in examples)
    print()
    print("All examples have required columns:", all_valid)
    assert all_valid

    # The actual regression test: build the real HF Dataset and confirm
    # the schema-unification bug (None-padded keys from other domains)
    # genuinely doesn't happen anymore with the JSON-string approach.
    try:
        ds = build_hf_dataset(n_per_domain=3, seed=1)
        sample_parsed = json.loads(ds[0]["hidden_intervention"])
        print()
        print(f"Built real HF Dataset, {len(ds)} rows. Sample hidden_intervention: {sample_parsed}")
        assert len(sample_parsed) == 1, "Schema pollution regression — HF Dataset flattened multiple domains' keys together again"
        print("HF Dataset schema-pollution regression check passed ✓")
    except ImportError:
        print()
        print("(datasets library not installed — skipping the HF Dataset regression check specifically, core logic above already verified)")

    print("Dataset self-test passed ✓")
