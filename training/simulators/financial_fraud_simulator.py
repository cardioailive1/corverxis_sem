"""Financial Fraud/Anomaly Investigation simulator — Python reference
version, mirrors backend/simulators/financialFraudSimulator.js exactly.
Includes a genuine 'not fraud' class — see the JS version's comment."""
import random

CAUSES = ["stolen_card_testing", "account_takeover", "synthetic_identity", "merchant_collusion", "legitimate_unusual_purchase"]
SIGNAL_PROFILES = {
    "stolen_card_testing":         {"rapid_small_transactions": 0.9, "velocity_spike": 0.85, "new_shipping_address": 0.2, "device_fingerprint_mismatch": 0.3, "high_risk_merchant_category": 0.4, "geo_mismatch": 0.3},
    "account_takeover":            {"device_fingerprint_mismatch": 0.85, "geo_mismatch": 0.7, "new_shipping_address": 0.6, "velocity_spike": 0.4, "rapid_small_transactions": 0.15, "high_risk_merchant_category": 0.2},
    "synthetic_identity":          {"new_shipping_address": 0.7, "high_risk_merchant_category": 0.3, "velocity_spike": 0.25, "device_fingerprint_mismatch": 0.2, "rapid_small_transactions": 0.1, "geo_mismatch": 0.15},
    "merchant_collusion":          {"high_risk_merchant_category": 0.8, "rapid_small_transactions": 0.3, "velocity_spike": 0.3, "new_shipping_address": 0.05, "device_fingerprint_mismatch": 0.1, "geo_mismatch": 0.1},
    "legitimate_unusual_purchase": {"new_shipping_address": 0.25, "geo_mismatch": 0.2, "velocity_spike": 0.1, "high_risk_merchant_category": 0.1, "rapid_small_transactions": 0.03, "device_fingerprint_mismatch": 0.05},
}
ALL_SIGNALS = ["rapid_small_transactions", "new_shipping_address", "device_fingerprint_mismatch", "velocity_spike", "high_risk_merchant_category", "geo_mismatch"]

def sample_intervention(rng): return {"cause": rng.choice(CAUSES)}
def generate_observations(intervention, rng):
    profile = SIGNAL_PROFILES[intervention["cause"]]
    return {s: rng.random() < profile.get(s, 0.02) for s in ALL_SIGNALS}
def verify_proposed_structure(proposed, intervention, rng=None, n_trials=20):
    if not isinstance(proposed, dict) or "cause" not in proposed: return 0.0
    if proposed["cause"] == intervention["cause"]: return 1.0
    true_p, prop_p = SIGNAL_PROFILES[intervention["cause"]], SIGNAL_PROFILES.get(proposed["cause"], {})
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
        iv = sample_intervention(rng); guess = {"cause": "stolen_card_testing"}
        r = verify_proposed_structure(guess, iv)
        if r == 1.0: correct += 1
        elif iv["cause"] != "stolen_card_testing": wrong_rewards.append(r)
    print(f"Self-test: {correct}/200 correct, wrong-guess reward range {min(wrong_rewards):.3f}-{max(wrong_rewards):.3f}")
    assert 0 < correct < 200
    print("Simulator self-test passed ✓")
