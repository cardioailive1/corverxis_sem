"""
SEM training loop — the actual propose/verify/reward mechanism, runnable
end to end against a real simulator (industrial_fault_simulator.py here).

This is a REFERENCE implementation showing the correct shape of the loop.
At production scale, the "propose" step would call a dedicated, fine-tuned
model being trained via RL (the reward below would update model weights,
GRPO/PPO-style). Here, to keep this genuinely runnable and testable without
requiring GPU training infrastructure, the propose step calls Claude via
the Anthropic API as a stand-in — this tests the real loop mechanics
(scenario generation, proposal, verification, reward, logging) correctly,
even though the "model" being called isn't yet the purpose-trained SEM.

Run this directly to see the loop work end to end:
    python3 training_loop.py --n_scenarios 10
"""
import argparse
import json
import random
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "simulators"))
from industrial_fault_simulator import (
    sample_intervention, generate_observations, verify_proposed_structure,
    COMPONENTS, ALL_SYMPTOMS,
)


def build_proposal_prompt(observations: dict) -> str:
    true_symptoms = [s for s, present in observations.items() if present]
    return (
        f"A machine has {len(COMPONENTS)} possible failing components: {', '.join(COMPONENTS)}. "
        f"The following symptoms were observed: {', '.join(true_symptoms) if true_symptoms else 'none — all readings normal'}. "
        f"Propose which single component most likely failed, based on the observed symptom pattern. "
        f"Respond with ONLY the component name, exactly as listed above, nothing else."
    )


def propose_structure(observations: dict, anthropic_client=None) -> dict:
    """The 'propose' step. Uses Claude as a stand-in for the not-yet-trained
    SEM model — see module docstring. Returns a structure in the same shape
    the verifier expects."""
    if anthropic_client is None:
        # Offline/no-API-key fallback: a simple heuristic proposer, so this
        # script is still fully runnable and testable without any API key.
        present = [s for s, v in observations.items() if v]
        if not present:
            return {"failed_component": random.choice(COMPONENTS)}
        # naive: guess whichever component's profile has the most overlap with symptoms present
        from industrial_fault_simulator import SYMPTOM_PROFILES
        scores = {c: sum(SYMPTOM_PROFILES[c].get(s, 0) for s in present) for c in COMPONENTS}
        return {"failed_component": max(scores, key=scores.get)}

    prompt = build_proposal_prompt(observations)
    msg = anthropic_client.messages.create(
        model="claude-sonnet-4-6", max_tokens=20,
        messages=[{"role": "user", "content": prompt}],
    )
    guess = msg.content[0].text.strip().lower().replace(" ", "_")
    if guess not in COMPONENTS:
        guess = random.choice(COMPONENTS)   # malformed response — don't let the loop crash
    return {"failed_component": guess}


def run_training_loop(n_scenarios: int, seed: int = 0, use_api: bool = False):
    rng = random.Random(seed)
    anthropic_client = None
    if use_api:
        try:
            import anthropic
            anthropic_client = anthropic.Anthropic()
        except Exception as e:
            print(f"Could not initialize Anthropic client ({e}) — falling back to heuristic proposer.")

    results = []
    for i in range(n_scenarios):
        intervention = sample_intervention(rng)          # hidden — never passed to propose_structure
        observations = generate_observations(intervention, rng)
        proposal = propose_structure(observations, anthropic_client)
        reward = verify_proposed_structure(proposal, intervention, rng)

        results.append({
            "scenario": i, "observations": observations,
            "true_intervention": intervention, "proposed": proposal, "reward": reward,
        })
        print(f"[{i+1}/{n_scenarios}] true={intervention['failed_component']:20s} "
              f"proposed={proposal['failed_component']:20s} reward={reward}")

    mean_reward = sum(r["reward"] for r in results) / len(results)
    print(f"\nMean reward across {n_scenarios} scenarios: {mean_reward:.3f}")
    return results, mean_reward


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n_scenarios", type=int, default=10)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--use_api", action="store_true", help="Use Claude via Anthropic API as the proposer instead of the offline heuristic")
    args = parser.parse_args()

    results, mean_reward = run_training_loop(args.n_scenarios, args.seed, args.use_api)

    out_path = "training_run_output.json"
    with open(out_path, "w") as f:
        json.dump({"mean_reward": mean_reward, "results": results}, f, indent=2)
    print(f"Full results written to {out_path}")
