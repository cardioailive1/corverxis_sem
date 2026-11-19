# SI-SEM Real Cases (data collection)

Collects **real, de-identified cases with a confirmed cause**, so SI-SEM's probabilities can be checked against
reality before training. Modelled on Frontier Lab Phase 1 (qualified experts submit, a second person reviews).
Separate from the Lab UI and the product UI. API: `backend/collect/collectApi.js` at `/api/collect`.

## Roles
- **Admin**: keys in `SEM_COLLECT_ADMIN_KEYS` on `sem-osc-backend`, as `label=key` pairs (for example `ann=<long random>`).
  Creates contributors (each gets a personal key shown once), sees progress, exports CSV.
- **Contributor**: a person an admin qualified for named domains. Submits cases and reviews other people's cases in
  those domains. Nobody can review their own case, and an approved case is final.

## A case
Domain, the signals that were present (unticked means checked and absent), the confirmed cause (or "other, not
listed", which is tracked but never used to calibrate), how it was confirmed, and an optional source and month.
The submitter attests that the case is de-identified. Free text is screened for emails, phone numbers and ID
numbers as a safety net. Duplicate cases are rejected.

## From collection to validation
1. Admin creates contributors and sends each their key. Contributors submit; a second person approves.
2. **Progress** shows, per domain, approved cases against what is needed: 20 per cause overall and about 22 per cause.
3. When a domain shows ready, export its CSV (admin only) and run the calibration check:
   `python3 training/simulators/calibrate.py --domain <slug> --cases <slug>-cases.csv --source "<where it came from>"`
4. If it passes, add `--write`, then `python3 training/simulators/build_spec.py`. The domain becomes `calibrated`.
   `expert_validated` is only set by hand, after a named expert signs off.
5. Train after this, so SI-SEM learns the calibrated probabilities and not the illustrative ones.

## Setup
1. On `sem-osc-backend` set `SEM_COLLECT_ADMIN_KEYS`. Redeploy so the new tables are created.
2. Deploy `sem-collect-ui` (static, from `./collect`). `collect/config.js` must point at the backend.

## Limits to keep in mind
- Real cases are not a random sample of the world. Calibration here assumes each cause is equally likely beforehand,
  which real prevalence will not match. Use the numbers to check relationships between causes and signals.
- The privacy checks are a safety net. For medical and other regulated data, get the sign-off your organisation
  requires before collecting, and do not put identifiable data in this system.
- Sensitive domains (medical, cardiology, safety, finance) need qualified contributors and reviewers.
