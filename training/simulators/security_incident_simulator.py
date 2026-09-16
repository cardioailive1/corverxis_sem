"""Security Incident Investigation simulator — Python reference version,
mirrors backend/simulators/securityIncidentSimulator.js exactly."""
import random

ATTACK_VECTORS = ["phishing_credential_theft", "unpatched_cve_exploit", "insider_threat", "supply_chain_compromise", "brute_force_login"]
SIGNAL_PROFILES = {
    "phishing_credential_theft": {"unusual_login_location": 0.8, "after_hours_access": 0.5, "multiple_failed_logins": 0.15, "privilege_escalation_event": 0.3, "new_admin_account_created": 0.1, "outbound_data_transfer_spike": 0.35, "known_malware_signature": 0.05},
    "unpatched_cve_exploit":     {"known_malware_signature": 0.7, "privilege_escalation_event": 0.75, "outbound_data_transfer_spike": 0.4, "unusual_login_location": 0.2, "after_hours_access": 0.3, "multiple_failed_logins": 0.05, "new_admin_account_created": 0.2},
    "insider_threat":            {"outbound_data_transfer_spike": 0.75, "after_hours_access": 0.7, "unusual_login_location": 0.1, "privilege_escalation_event": 0.2, "new_admin_account_created": 0.1, "multiple_failed_logins": 0.02, "known_malware_signature": 0.02},
    "supply_chain_compromise":   {"known_malware_signature": 0.6, "new_admin_account_created": 0.45, "privilege_escalation_event": 0.55, "outbound_data_transfer_spike": 0.5, "unusual_login_location": 0.15, "after_hours_access": 0.2, "multiple_failed_logins": 0.03},
    "brute_force_login":         {"multiple_failed_logins": 0.9, "unusual_login_location": 0.5, "after_hours_access": 0.4, "privilege_escalation_event": 0.1, "outbound_data_transfer_spike": 0.1, "new_admin_account_created": 0.05, "known_malware_signature": 0.02},
}
ALL_SIGNALS = ["unusual_login_location", "privilege_escalation_event", "outbound_data_transfer_spike", "known_malware_signature", "after_hours_access", "multiple_failed_logins", "new_admin_account_created"]

def sample_intervention(rng): return {"attack_vector": rng.choice(ATTACK_VECTORS)}
def generate_observations(intervention, rng):
    profile = SIGNAL_PROFILES[intervention["attack_vector"]]
    return {s: rng.random() < profile.get(s, 0.03) for s in ALL_SIGNALS}
def verify_proposed_structure(proposed, intervention, rng=None, n_trials=20):
    if not isinstance(proposed, dict) or "attack_vector" not in proposed: return 0.0
    if proposed["attack_vector"] == intervention["attack_vector"]: return 1.0
    true_p, prop_p = SIGNAL_PROFILES[intervention["attack_vector"]], SIGNAL_PROFILES.get(proposed["attack_vector"], {})
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
        iv = sample_intervention(rng); guess = {"attack_vector": "brute_force_login"}
        r = verify_proposed_structure(guess, iv)
        if r == 1.0: correct += 1
        elif iv["attack_vector"] != "brute_force_login": wrong_rewards.append(r)
    print(f"Self-test: {correct}/200 correct, wrong-guess reward range {min(wrong_rewards):.3f}-{max(wrong_rewards):.3f}")
    assert 0 < correct < 200
    print("Simulator self-test passed ✓")
