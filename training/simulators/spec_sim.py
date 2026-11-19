"""Generic simulator engine driven by domains_spec.json (see build_spec.py).
Every domain is: hidden cause -> noisy binary signals (each fires with the probability in the
cause's profile, or default_p), verified by exact match with partial credit for overlapping profiles."""
import json, os, random

_SPEC = None
def spec():
    global _SPEC
    if _SPEC is None:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "domains_spec.json")) as f:
            _SPEC = {d["slug"]: d for d in json.load(f)["domains"]}
    return _SPEC

def slugs(): return list(spec().keys())

def install(module, slug, list_name):
    """Populate `module` with the attributes the old hand-written simulators exposed."""
    d = spec()[slug]; key = d["key"]; causes, signals, prof, dp = d["causes"], d["signals"], d["profiles"], d["default_p"]
    def sample_intervention(rng): return {key: rng.choice(causes)}
    def generate_observations(intervention, rng):
        p = prof[intervention[key]]
        return {s: rng.random() < p.get(s, dp) for s in signals}
    def verify_proposed_structure(proposed, intervention, rng=None, n_trials=20):
        if not isinstance(proposed, dict) or key not in proposed: return 0.0
        if proposed[key] == intervention[key]: return 1.0
        tp, pp = prof[intervention[key]], prof.get(proposed[key], {})
        overlap = sum(min(tp.get(s, 0), pp.get(s, 0)) for s in signals); total = sum(tp.values())
        return round(0.3 * (overlap / total), 3) if total > 0 else 0.0
    module.__dict__.update({
        list_name: causes, "CAUSES_LIST": causes, "SYMPTOM_PROFILES": prof, "SIGNAL_PROFILES": prof,
        "ALL_SYMPTOMS": signals, "ALL_SIGNALS": signals, "SLUG": slug, "KEY": key, "DEFAULT_P": dp,
        "sample_intervention": sample_intervention, "generate_observations": generate_observations,
        "verify_proposed_structure": verify_proposed_structure,
    })

def cli(module):
    """`--generate N` prints scenarios as JSON; otherwise a self-test."""
    import sys
    if "--generate" in sys.argv:
        n = int(sys.argv[sys.argv.index("--generate") + 1]); rng = random.Random(); out = []
        for _ in range(n):
            iv = module.sample_intervention(rng)
            out.append({"hidden_intervention": iv, "observations": module.generate_observations(iv, rng)})
        print(json.dumps(out)); return
    rng = random.Random(42); key = module.KEY; first = module.CAUSES_LIST[0]; correct, wrong = 0, []
    for _ in range(500):
        iv = module.sample_intervention(rng); module.generate_observations(iv, rng)
        r = module.verify_proposed_structure({key: first}, iv)
        if r == 1.0: correct += 1
        else: wrong.append(r)
    print(f"{module.SLUG}: {len(module.CAUSES_LIST)} causes, {len(module.ALL_SIGNALS)} signals; always-'{first}' baseline correct {correct}/500, wrong-guess reward {min(wrong):.3f}-{max(wrong):.3f}")
    assert 0 < correct < 500
    print("Simulator self-test passed ✓")
