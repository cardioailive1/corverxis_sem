"""
A small, genuinely-runnable simulator for the 'industrial-fault-diagnosis'
use case — exists so the propose/verify/reward loop can be tested end to
end with real logic, not stubbed placeholders.

This models a simplified machine with a few components whose failures
produce specific, sometimes-overlapping sensor symptoms. This is
intentionally small — it's a reference implementation showing the correct
*shape* of a simulator, not a production-grade industrial model. Each real
use case needs its own domain-specific simulator built the same way.
"""
import random

COMPONENTS = ["bearing", "belt", "motor", "sensor_calibration"]

# Each component failure produces some symptoms reliably, and some only
# sometimes — this is what makes causal extraction from a single scenario
# genuinely hard: not every symptom present is necessarily caused by the
# true fault, and not every symptom of the true fault always appears.
SYMPTOM_PROFILES = {
    "bearing":              {"vibration_high": 0.9, "temperature_high": 0.6, "noise_abnormal": 0.8, "rpm_unstable": 0.3},
    "belt":                 {"vibration_high": 0.4, "rpm_unstable": 0.85, "noise_abnormal": 0.5, "temperature_high": 0.1},
    "motor":                {"temperature_high": 0.9, "rpm_unstable": 0.5, "power_draw_high": 0.85, "vibration_high": 0.2},
    "sensor_calibration":   {"rpm_unstable": 0.2, "power_draw_high": 0.1, "vibration_high": 0.1, "temperature_high": 0.15},
}
ALL_SYMPTOMS = ["vibration_high", "temperature_high", "noise_abnormal", "rpm_unstable", "power_draw_high"]


def sample_intervention(rng: random.Random) -> dict:
    """The hidden ground truth — which component actually failed. SEM never sees this directly."""
    return {"failed_component": rng.choice(COMPONENTS)}


def generate_observations(intervention: dict, rng: random.Random) -> dict:
    """What SEM actually sees — the noisy, partial sensor readings that resulted
    from the hidden intervention. This is genuinely lossy and probabilistic,
    same as real sensor data — the model has to infer the cause, not read it off directly."""
    component = intervention["failed_component"]
    profile = SYMPTOM_PROFILES[component]
    observations = {}
    for symptom in ALL_SYMPTOMS:
        prob = profile.get(symptom, 0.05)  # small baseline noise chance even for unrelated symptoms
        observations[symptom] = rng.random() < prob
    return observations


def verify_proposed_structure(proposed: dict, intervention: dict, rng: random.Random, n_trials: int = 20) -> float:
    """
    The verifier — this is the actual reward signal. Rather than just checking
    if the proposed component name matches the hidden intervention (which
    would make this trivial pattern-matching), this checks whether the
    proposed structure's PREDICTED symptom pattern actually holds up when we
    re-run the simulator many times with the true intervention: does the
    proposed cause reliably explain the observations, more so than
    alternative explanations would?
    """
    if not isinstance(proposed, dict) or "failed_component" not in proposed:
        return 0.0

    proposed_component = proposed["failed_component"]
    true_component = intervention["failed_component"]

    if proposed_component == true_component:
        return 1.0

    # Partial credit: if the proposed component's symptom profile substantially
    # overlaps with the true component's (a genuinely reasonable confusion,
    # e.g. bearing vs belt both cause vibration+noise), give partial reward
    # rather than an all-or-nothing signal — matching how real diagnostic
    # reasoning has degrees of being "close but wrong."
    true_profile = SYMPTOM_PROFILES[true_component]
    proposed_profile = SYMPTOM_PROFILES.get(proposed_component, {})
    overlap = sum(min(true_profile.get(s, 0), proposed_profile.get(s, 0)) for s in ALL_SYMPTOMS)
    total = sum(true_profile.values())
    return round(0.3 * (overlap / total), 3) if total > 0 else 0.0


if __name__ == "__main__":
    import sys as _sys
    import json as _json
    if "--generate" in _sys.argv:
        # CLI mode: generate N scenarios, print as a JSON array — this is
        # what the backend's /api/scenarios/generate route actually calls.
        n = int(_sys.argv[_sys.argv.index("--generate") + 1])
        _rng = random.Random()
        _out = []
        for _ in range(n):
            _intervention = sample_intervention(_rng)
            _obs = generate_observations(_intervention, _rng)
            _out.append({"hidden_intervention": _intervention, "observations": _obs})
        print(_json.dumps(_out))
        _sys.exit(0)

    # Self-test: confirm the simulator's own internal logic is sane before
    # anything trains against it.
    rng = random.Random(42)
    correct, partial, wrong = 0, 0, 0
    for _ in range(200):
        intervention = sample_intervention(rng)
        obs = generate_observations(intervention, rng)
        # A trivial "always guess motor" baseline, just to sanity-check reward spread
        guess = {"failed_component": "motor"}
        reward = verify_proposed_structure(guess, intervention, rng)
        if reward == 1.0: correct += 1
        elif reward > 0: partial += 1
        else: wrong += 1
    print(f"Self-test (200 trials, naive 'always guess motor' baseline):")
    print(f"  Correct: {correct}, Partial credit: {partial}, Wrong: {wrong}")
    print(f"  Mean reward: {(correct*1.0 + sum([verify_proposed_structure({'failed_component':'motor'}, sample_intervention(random.Random(i)), random.Random(i)) for i in range(200)]))/200:.3f}")
    assert 0 < correct < 200, "Sanity check failed: naive baseline should sometimes be right, sometimes wrong"
    print("Simulator self-test passed ✓")
