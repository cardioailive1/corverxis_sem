"""Pull approved real cases from the collection API and run the calibration check for every domain that is ready.

Automates the step between collection and validation. By default it only REPORTS (nothing is written). With --write
it writes calibrations for domains that pass calibrate.py's gates; run build_spec.py afterwards. It never sets
expert_validated.

  export SEM_BACKEND_URL=https://sem-osc-backend.onrender.com
  export SEM_COLLECT_ADMIN_KEY=...            # an admin key from SEM_COLLECT_ADMIN_KEYS
  python3 collect_sync.py [--write] [--domain slug]
Run it on a schedule (cron, or a scheduled task) to keep validation status current as cases are approved.
"""
import argparse, json, os, subprocess, sys, tempfile, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))

def get(url, key):
    req = urllib.request.Request(url, headers={"x-api-key": key})
    with urllib.request.urlopen(req, timeout=60) as r: return r.read().decode()

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true"); ap.add_argument("--domain")
    ap.add_argument("--base", default=os.environ.get("SEM_BACKEND_URL", "")); ap.add_argument("--key", default=os.environ.get("SEM_COLLECT_ADMIN_KEY", ""))
    a = ap.parse_args()
    if not a.base or not a.key: sys.exit("Set SEM_BACKEND_URL and SEM_COLLECT_ADMIN_KEY.")
    base = a.base.rstrip("/") + "/api/collect"
    progress = json.loads(get(base + "/progress", a.key))
    ready = [p for p in progress if p["ready_to_calibrate"] and (not a.domain or p["slug"] == a.domain)]
    print(f"{len(ready)} of {len(progress)} domains ready to calibrate.")
    for p in progress:
        if p["user_reports"]: print(f"  live agreement {p['slug']}: {p['user_report_agreement']} over {p['user_reports']} user reports (unverified)")
    wrote = 0
    for p in ready:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = os.path.join(tmp, p["slug"] + ".csv"); open(csv_path, "w").write(get(f"{base}/export/{p['slug']}.csv", a.key))
            cmd = [sys.executable, os.path.join(HERE, "calibrate.py"), "--domain", p["slug"], "--cases", csv_path, "--source", "collection API"] + (["--write"] if a.write else [])
            r = subprocess.run(cmd, capture_output=True, text=True); print(r.stdout.strip()); 
            if r.returncode == 0 and a.write: wrote += 1
            elif r.returncode != 0: print(r.stderr.strip() or "not written")
    if wrote: print(f"Wrote {wrote} calibration(s). Now run: python3 build_spec.py")

if __name__ == "__main__": main()
