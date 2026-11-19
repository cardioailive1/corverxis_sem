"""Checks the shared domain spec and the Python/Node agreement. Run from training/:  python3 simulators/test_spec.py [parity.json]
parity.json is written by the Node test (PARITY_OUT=... node --test product/productApi.test.js) and holds the prompts the
product API builds; they must equal grpo/dataset.py build_prompt byte for byte."""
import json, os, sys, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "grpo"))
import spec_sim, build_spec

a = open(os.path.join(HERE, "domains_spec.json")).read()
b = open(os.path.join(HERE, "..", "..", "backend", "simulators", "domains_spec.json")).read()
assert a == b, "training and backend domains_spec.json differ; run build_spec.py"
spec = json.loads(a)["domains"]; build_spec.validate(spec)
assert json.loads(a) == json.loads(json.dumps({"version": 2, "domains": build_spec.D})), "domains_spec.json is stale vs build_spec.py"
print(f"spec ok: {len(spec)} domains, causes {[len(d['causes']) for d in spec]}")

import dataset
assert set(dataset.DOMAIN_MODULES) == {d["slug"] for d in spec}
if len(sys.argv) > 1:
    js = json.load(open(sys.argv[1])); n = bad = 0
    for slug, rows in js.items():
        sigs = spec_sim.spec()[slug]["signals"]
        for r in rows:
            n += 1
            if dataset.build_prompt(slug, {s: s in r["present"] for s in sigs}) != r["prompt"]:
                bad += 1
    print(f"prompt parity: {n} prompts across {len(js)} domains, {bad} mismatches"); assert bad == 0
print("OK")
