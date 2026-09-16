"""Scientific Discovery simulator — Python reference version, mirrors
backend/simulators/scientificDiscoverySimulator.js exactly."""
import random

MECHANISMS = ["catalyst_effect", "confounding_variable", "measurement_artifact", "genuine_novel_effect", "temperature_dependency"]
SIGNAL_PROFILES = {
    "catalyst_effect":        {"dose_response_relationship": 0.85, "result_reproducible": 0.8, "effect_size_large": 0.6, "correlates_with_control_variable": 0.1, "instrument_calibration_drift": 0.05},
    "confounding_variable":   {"correlates_with_control_variable": 0.9, "result_reproducible": 0.6, "dose_response_relationship": 0.3, "effect_size_large": 0.4, "instrument_calibration_drift": 0.1},
    "measurement_artifact":   {"instrument_calibration_drift": 0.85, "result_reproducible": 0.2, "correlates_with_control_variable": 0.15, "dose_response_relationship": 0.1, "effect_size_large": 0.3},
    "genuine_novel_effect":   {"result_reproducible": 0.9, "dose_response_relationship": 0.7, "effect_size_large": 0.55, "correlates_with_control_variable": 0.05, "instrument_calibration_drift": 0.03},
    "temperature_dependency": {"dose_response_relationship": 0.5, "result_reproducible": 0.75, "correlates_with_control_variable": 0.4, "effect_size_large": 0.35, "instrument_calibration_drift": 0.1},
}
ALL_SIGNALS = ["result_reproducible", "correlates_with_control_variable", "effect_size_large", "dose_response_relationship", "instrument_calibration_drift"]

def sample_intervention(rng): return {"mechanism": rng.choice(MECHANISMS)}
def generate_observations(intervention, rng):
    profile = SIGNAL_PROFILES[intervention["mechanism"]]
    return {s: rng.random() < profile.get(s, 0.05) for s in ALL_SIGNALS}
def verify_proposed_structure(proposed, intervention, rng=None, n_trials=20):
    if not isinstance(proposed, dict) or "mechanism" not in proposed: return 0.0
    if proposed["mechanism"] == intervention["mechanism"]: return 1.0
    true_p, prop_p = SIGNAL_PROFILES[intervention["mechanism"]], SIGNAL_PROFILES.get(proposed["mechanism"], {})
    overlap = sum(min(true_p.get(s, 0), prop_p.get(s, 0)) for s in ALL_SIGNALS)
    total = sum(true_p.values())
    return round(0.3 * (overlap / total), 3) if total > 0 else 0.0

if __name__ == "__main__":
    import sys, json
    if "--generate" in sys.argv:
        n = int(sys.argv[sys.argv.index("--generate") + 1]); rng = random.Random(); out = []
        for _ in range(n):
            iv = sample_intervention(rng); out.append({"hidden_intervention": iv, "observations": generate_observations(iv, rng)})
        print(json.dumps(out)); sys.exit(0)
    rng = random.Random(42); correct, wrong_rewards = 0, []
    for _ in range(200):
        iv = sample_intervention(rng); guess = {"mechanism": "genuine_novel_effect"}
        r = verify_proposed_structure(guess, iv)
        if r == 1.0: correct += 1
        elif iv["mechanism"] != "genuine_novel_effect": wrong_rewards.append(r)
    print(f"Self-test: {correct}/200 correct, wrong-guess reward range {min(wrong_rewards):.3f}-{max(wrong_rewards):.3f}")
    assert 0 < correct < 200
    print("Simulator self-test passed ✓")
