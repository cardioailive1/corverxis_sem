"""Production Incident Root-Causing simulator — Python reference version,
mirrors backend/simulators/productionIncidentSimulator.js exactly."""
import random

ROOT_CAUSES = ["bad_deploy", "database_connection_pool_exhaustion", "third_party_api_outage", "traffic_spike_ddos", "memory_leak"]
SIGNAL_PROFILES = {
    "bad_deploy":                          {"deploy_within_last_hour": 0.9, "error_rate_spike": 0.75, "latency_increase": 0.4, "upstream_5xx_errors": 0.3, "database_timeout_errors": 0.15, "cpu_usage_high": 0.2, "memory_usage_climbing": 0.1},
    "database_connection_pool_exhaustion": {"database_timeout_errors": 0.9, "latency_increase": 0.7, "error_rate_spike": 0.5, "deploy_within_last_hour": 0.1, "cpu_usage_high": 0.2, "memory_usage_climbing": 0.15, "upstream_5xx_errors": 0.1},
    "third_party_api_outage":              {"upstream_5xx_errors": 0.85, "latency_increase": 0.6, "error_rate_spike": 0.55, "deploy_within_last_hour": 0.05, "database_timeout_errors": 0.1, "cpu_usage_high": 0.1, "memory_usage_climbing": 0.05},
    "traffic_spike_ddos":                  {"cpu_usage_high": 0.85, "latency_increase": 0.75, "error_rate_spike": 0.6, "database_timeout_errors": 0.3, "memory_usage_climbing": 0.2, "deploy_within_last_hour": 0.05, "upstream_5xx_errors": 0.15},
    "memory_leak":                         {"memory_usage_climbing": 0.9, "latency_increase": 0.5, "error_rate_spike": 0.35, "cpu_usage_high": 0.25, "deploy_within_last_hour": 0.1, "database_timeout_errors": 0.1, "upstream_5xx_errors": 0.05},
}
ALL_SIGNALS = ["error_rate_spike", "latency_increase", "deploy_within_last_hour", "database_timeout_errors", "cpu_usage_high", "memory_usage_climbing", "upstream_5xx_errors"]

def sample_intervention(rng): return {"root_cause": rng.choice(ROOT_CAUSES)}
def generate_observations(intervention, rng):
    profile = SIGNAL_PROFILES[intervention["root_cause"]]
    return {s: rng.random() < profile.get(s, 0.03) for s in ALL_SIGNALS}
def verify_proposed_structure(proposed, intervention, rng=None, n_trials=20):
    if not isinstance(proposed, dict) or "root_cause" not in proposed: return 0.0
    if proposed["root_cause"] == intervention["root_cause"]: return 1.0
    true_p, prop_p = SIGNAL_PROFILES[intervention["root_cause"]], SIGNAL_PROFILES.get(proposed["root_cause"], {})
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
        iv = sample_intervention(rng); guess = {"root_cause": "bad_deploy"}
        r = verify_proposed_structure(guess, iv)
        if r == 1.0: correct += 1
        elif iv["root_cause"] != "bad_deploy": wrong_rewards.append(r)
    print(f"Self-test: {correct}/200 correct, wrong-guess reward range {min(wrong_rewards):.3f}-{max(wrong_rewards):.3f}")
    assert 0 < correct < 200
    print("Simulator self-test passed ✓")
