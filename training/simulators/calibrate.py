"""Calibrate one domain's cause->signal probabilities from REAL labelled cases, and check it on held-out cases.

Input CSV: one row per real case. Columns: `cause` (must be one of the domain's causes) plus either
  * one 0/1 column per signal name, or
  * a `signals` column with semicolon-separated signal names.
Usage:
  python3 calibrate.py --domain cardiology-ecg-review --cases cases.csv            # report only
  python3 calibrate.py --domain cardiology-ecg-review --cases cases.csv --write    # also write calibrations/<slug>.json
then run `python3 build_spec.py` to rebuild the spec with the calibrated probabilities.

Method: for each cause c and signal s, p = (k*prior + positives) / (k + n_c), where prior is the current
(illustrative) probability and k is --prior-strength. With few cases the numbers stay near the prior.
Check: the cases are split once (seeded) into fit and held-out. The held-out accuracy of the Bayes classifier
using illustrative vs calibrated probabilities is compared. Status becomes "calibrated" only if there are enough
cases (>= --min-per-cause per cause that appears, and >= 20 x causes overall) and the calibrated model is not worse than
the illustrative one on held-out cases. This tool never sets "expert_validated"; that needs a named expert's sign-off.
"""
import argparse, csv, datetime, json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_sim

def load_cases(path, d):
    cases = []
    with open(path, newline="") as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            c = (row.get("cause") or "").strip()
            if c not in d["causes"]: raise SystemExit(f"row {i}: unknown cause {c!r}")
            if row.get("signals") is not None and "signals" in row:
                sig = {x.strip() for x in row["signals"].split(";") if x.strip()}
            else:
                sig = {s for s in d["signals"] if str(row.get(s, "0")).strip() in ("1", "true", "True")}
            bad = sig - set(d["signals"])
            if bad: raise SystemExit(f"row {i}: unknown signals {sorted(bad)}")
            cases.append((c, sig))
    return cases

def fit(d, cases, k):
    prof = {c: {} for c in d["causes"]}; n = {c: 0 for c in d["causes"]}
    for c, _ in cases: n[c] += 1
    for c in d["causes"]:
        for s in d["signals"]:
            prior = d["profiles"][c].get(s, d["default_p"]); pos = sum(1 for cc, sg in cases if cc == c and s in sg)
            prof[c][s] = min(0.98, max(0.01, (k * prior + pos) / (k + n[c])))
    return prof, n

def predict(d, prof, sig):
    best, bl = None, -1e18
    for c in d["causes"]:
        ll = sum(math.log(prof[c].get(s, d["default_p"]) if s in sig else 1 - prof[c].get(s, d["default_p"])) for s in d["signals"])
        if ll > bl: best, bl = c, ll
    return best

def acc(d, prof, cases):
    return sum(predict(d, prof, sg) == c for c, sg in cases) / len(cases)

def wilson(p, n, z=1.96):
    if n == 0: return (0, 0)
    den = 1 + z*z/n; mid = (p + z*z/(2*n)) / den; h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / den
    return (max(0, mid-h), min(1, mid+h))

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--domain", required=True); ap.add_argument("--cases", required=True)
    ap.add_argument("--prior-strength", type=float, default=10.0); ap.add_argument("--holdout", type=float, default=0.3)
    ap.add_argument("--seed", type=int, default=7); ap.add_argument("--min-per-cause", type=int, default=15)
    ap.add_argument("--source", default="", help="where the cases came from (recorded in the status)")
    ap.add_argument("--write", action="store_true"); a = ap.parse_args()
    d = spec_sim.spec().get(a.domain) or sys.exit(f"unknown domain {a.domain}")
    # the checked-in spec may already be calibrated; the baseline for comparison is the spec as it stands
    cases = load_cases(a.cases, d); rng = random.Random(a.seed); rng.shuffle(cases)
    cut = int(len(cases) * (1 - a.holdout)); train, held = cases[:cut], cases[cut:]
    if not held: sys.exit("not enough cases for a held-out set")
    prof, n = fit(d, train, a.prior_strength)
    a_old, a_new = acc(d, d["profiles"], held), acc(d, prof, held)
    lo, hi = wilson(a_new, len(held))
    seen = [c for c in d["causes"] if n[c] > 0]; thin = [c for c in seen if n[c] < a.min_per_cause]
    ok_n = len(cases) >= 20 * len(d["causes"]) and not thin and len(seen) >= len(d["causes"]) * 0.8
    ok_acc = a_new >= a_old
    print(f"{a.domain}: {len(cases)} cases ({len(train)} fit / {len(held)} held out), {len(seen)}/{len(d['causes'])} causes present")
    print(f"held-out accuracy  current: {a_old:.3f}   calibrated: {a_new:.3f}  (95% CI {lo:.3f}-{hi:.3f})")
    if thin: print("causes with too few fit cases:", ", ".join(f"{c}={n[c]}" for c in thin))
    print("enough data:", ok_n, "| calibrated model not worse:", ok_acc)
    status = "calibrated" if ok_n and ok_acc else "illustrative"
    print("resulting status:", status)
    if a.write:
        if status != "calibrated": sys.exit("Not written: the data does not meet the bar for 'calibrated'.")
        final, _ = fit(d, cases, a.prior_strength)   # refit on everything once the held-out check has passed
        out = {"profiles": {c: {s: round(p, 4) for s, p in pr.items()} for c, pr in final.items()},
               "validation": {"status": "calibrated", "n_cases": len(cases), "holdout_accuracy": round(a_new, 4),
                              "holdout_accuracy_ci": [round(lo, 4), round(hi, 4)], "baseline_holdout_accuracy": round(a_old, 4),
                              "source": a.source, "date": datetime.date.today().isoformat(), "signed_off_by": None}}
        os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibrations"), exist_ok=True)
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibrations", a.domain + ".json")
        json.dump(out, open(path, "w"), indent=1); print("wrote", path, "- now run build_spec.py")

if __name__ == "__main__": main()
