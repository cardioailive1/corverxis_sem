"""Medical Diagnostics simulator — Python reference version, mirrors
backend/simulators/medicalDiagnosticsSimulator.js exactly. See
industrial_fault_simulator.py for the full explanation of this pattern."""
import random

CONDITIONS = ["influenza", "bacterial_pneumonia", "covid19", "common_cold", "allergic_rhinitis"]
SYMPTOM_PROFILES = {
    "influenza":           {"fever_high": 0.85, "body_aches": 0.9, "fatigue": 0.8, "cough_dry": 0.5, "sore_throat": 0.4, "sneezing": 0.1, "loss_of_taste_smell": 0.05, "shortness_of_breath": 0.15},
    "bacterial_pneumonia": {"fever_high": 0.9, "cough_productive": 0.85, "shortness_of_breath": 0.7, "fatigue": 0.6, "body_aches": 0.3, "sore_throat": 0.1, "sneezing": 0.05, "loss_of_taste_smell": 0.05},
    "covid19":             {"fever_high": 0.6, "fatigue": 0.75, "body_aches": 0.5, "loss_of_taste_smell": 0.55, "cough_dry": 0.5, "shortness_of_breath": 0.35, "sore_throat": 0.3, "sneezing": 0.1},
    "common_cold":         {"sneezing": 0.85, "sore_throat": 0.6, "cough_dry": 0.4, "fatigue": 0.3, "fever_high": 0.1, "body_aches": 0.15, "shortness_of_breath": 0.02, "loss_of_taste_smell": 0.02},
    "allergic_rhinitis":   {"sneezing": 0.9, "sore_throat": 0.15, "fatigue": 0.2, "fever_high": 0.01, "cough_dry": 0.2, "body_aches": 0.02, "shortness_of_breath": 0.1, "loss_of_taste_smell": 0.02},
}
ALL_SYMPTOMS = ["fever_high", "cough_productive", "cough_dry", "shortness_of_breath", "sore_throat", "body_aches", "sneezing", "loss_of_taste_smell", "fatigue"]

def sample_intervention(rng): return {"condition": rng.choice(CONDITIONS)}
def generate_observations(intervention, rng):
    profile = SYMPTOM_PROFILES[intervention["condition"]]
    return {s: rng.random() < profile.get(s, 0.03) for s in ALL_SYMPTOMS}
def verify_proposed_structure(proposed, intervention, rng=None, n_trials=20):
    if not isinstance(proposed, dict) or "condition" not in proposed: return 0.0
    if proposed["condition"] == intervention["condition"]: return 1.0
    true_p, prop_p = SYMPTOM_PROFILES[intervention["condition"]], SYMPTOM_PROFILES.get(proposed["condition"], {})
    overlap = sum(min(true_p.get(s, 0), prop_p.get(s, 0)) for s in ALL_SYMPTOMS)
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
        iv = sample_intervention(rng); guess = {"condition": "influenza"}
        r = verify_proposed_structure(guess, iv)
        if r == 1.0: correct += 1
        elif iv["condition"] != "influenza": wrong_rewards.append(r)
    print(f"Self-test: {correct}/200 correct, wrong-guess reward range {min(wrong_rewards):.3f}-{max(wrong_rewards):.3f}")
    assert 0 < correct < 200
    print("Simulator self-test passed ✓")
