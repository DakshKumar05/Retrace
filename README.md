# Retrace

**Prevent · Detect · Protect · Document · Report**

> Retrace is a prototype payment-risk and incident-response platform focused specifically on
> refund-abuse scams. It complements, rather than replaces, existing payment fraud systems.

---

## The problem

A stranger sends money to your UPI account. Minutes later they message you: *"Sorry bhai, sent that
by mistake — please send it back urgently to my wife's UPI, my account isn't working."*

You send it back. Later, the original credit is disputed or reversed. You are now out the money
twice: once to the scammer's second account, and once when the bank claws back the first payment.
Worse, your account may be flagged while the disputed transaction is investigated.

Three things make this scam work:

1. **It looks like kindness.** Returning money to someone who made a mistake feels obviously correct.
2. **The pressure is time-based.** You are rushed so you don't stop to think.
3. **The refund goes somewhere new.** That single detail is the tell, and it's the easiest one to miss.

## The key innovation: a refund safety score

Generic fraud tools ask *"is this payment fraudulent?"* — a question the victim cannot act on,
because the incoming payment is real. Retrace asks a different question:

> **Is it safe for this user to refund this transaction?**

Every refund request gets scored 0–100 with the exact reasoning attached.

### Two scales, deliberately kept apart

The product brief showed a score of `18/100` labelled CRITICAL in one place and `94/100` labelled
CRITICAL in another. Those are opposite scales, and conflating them is how a person misreads a
warning. The API therefore returns both, always:

| Field | Direction | Used for |
|---|---|---|
| `risk_score` | higher = more dangerous | Drives the risk level and recommendation |
| `safety_score` | higher = safer (`100 - risk_score`) | The big number on the dial: "6 / 100 refund safety" |

Risk bands: `0–30 LOW · 31–60 MEDIUM · 61–80 HIGH · 81–100 CRITICAL`.

---

## Why the refund rail is the whole story

`POST /v1/payments/:id/refund` takes no destination. A Razorpay refund can only return money to the
instrument that paid, and there is no parameter a caller could set to send it somewhere else.

That is the entire scam in one sentence: **it only works if the victim steps off that rail.** The
scammer's "send it to my wife's UPI instead" is a request to abandon a refund — which is safe by
construction — in favour of a fresh peer-to-peer transfer, which is not. The +25 destination-mismatch
rule, the highest-weighted signal in the engine, is really detecting that the user is about to leave
the protected path.

So Retrace's Safe Refund is not a metaphor. With test keys configured it calls the real Razorpay
refund API against the original `pay_...` id, and the money is *structurally incapable* of reaching
the handle the scammer supplied.

| Path | What actually happens | Can the money reach the scammer? |
|---|---|---|
| Safe Refund | `POST /v1/payments/:id/refund` | No — the API has no destination field |
| Manual transfer | A new P2P transfer the user makes | Yes — this is the loss |

Set `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` to test keys and the demo runs on genuine Razorpay
objects end to end: Checkout produces a real payment id, the safety check scores that payment, and
Safe Refund issues a real test-mode refund whose status arrives back over a signed webhook. A live
key is refused by the `rzp_test_` prefix check, so the demo cannot move real money even by accident.

---

## Features

**Before the loss**
- Refund safety scoring with a full explanation of every contributing signal
- A safety check that opens *instead of* processing a refund
- Safe Refund: routes money back along the original payment instead of to a supplied handle
- Scam message analyzer that highlights the exact phrases it matched
- Safe Mode, a protective account state after high-risk activity
- Opt-in emergency fund protection (simulated balance isolation)

**After the loss**
- Automatic incident creation when a risky refund is confirmed
- Evidence vault with SHA-256 fingerprinting and completeness scoring
- Combined incident timeline assembled from transaction, refund, message and system events
- Case lifecycle: Open → Under review → Report ready → Submitted → Resolved
- Incident & Evidence Report as PDF, plus a ZIP package with `manifest.json`

**Analyst view**
- Fraud intelligence dashboard with charts and a live risk feed
- Fraud network graph built with NetworkX, clustering senders across victims

---

## Architecture

```
                              USER
                               │
                        React + Vite + MUI
                               │
                          REST / JWT
                               │
                        FastAPI backend
                               │
        ┌──────────────────────┼──────────────────────┐
   Transaction              Refund                 Evidence
     service                service                 service
        └──────────────────────┼──────────────────────┘
                               ▼
                          RISK ENGINE
                               │
        ┌────────────┬─────────┴─────────┬────────────┐
     Rules         Demo ML            NLP           Network
     engine        model             analyzer       analysis
     (45%)         (25%)              (15%)          (15%)
        └────────────┴─────────┬─────────┴────────────┘
                               ▼
                     FINAL RISK SCORE (cap 98)
                               │
              ┌────────────────┼────────────────┐
            SAFE            VERIFY           CRITICAL
              │                │                │
         Normal flow       Warning          Safe Mode
                                                │
                             ┌──────────────────┼──────────────────┐
                          Evidence           Timeline           Incident
                           vault
                             └──────────────────┬──────────────────┘
                                                ▼
                                        Report generator
                                                ▼
                                  Incident & Evidence Report
```

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | React 18, Vite, TypeScript, MUI 6 | Typed contracts against the API; MUI gives accessible primitives without hand-rolling a design system |
| Charts | Recharts | Declarative, small enough for four charts |
| Graph render | Plain SVG | Layout comes pre-computed from NetworkX, so no client-side graph library is needed |
| Backend | FastAPI, Pydantic v2 | Request validation and OpenAPI docs come from the same type definitions |
| ORM | SQLAlchemy 2.0 | Typed `Mapped[...]` models |
| Database | PostgreSQL, SQLite fallback | Postgres in Docker; SQLite by default so the project runs with zero infrastructure |
| Rules / ML / NLP | Python, pandas, scikit-learn | Random forest on synthetic data, plus a regex rules engine |
| Network | NetworkX | Cluster detection and spring layout |
| PDF | ReportLab | Platypus flowables for a multi-page structured document |
| Auth | PyJWT + bcrypt | Bcrypt direct rather than passlib, to avoid the passlib/bcrypt 4.x version warning |
| Payments | Razorpay Test Mode via httpx | Orders, Checkout, refund-to-source and HMAC-verified webhooks against the real API |

---

## Fraud detection methodology

### 1. Rules engine (45% of the blend)

Eight weighted rules, each a pure function of a `RefundContext`:

| Signal | Weight |
|---|---|
| Refund destination differs from the paying account | +25 |
| Refund requested within 10 minutes | +20 |
| Sender has no prior history with this account | +15 |
| Sending account is under 30 days old | +15 |
| Sender flagged in earlier activity | +15 |
| More than one refund request on the same payment | +15 |
| Amount well outside normal incoming payments | +10 |
| Urgency or pressure language in the message | +10 |

The single highest-weighted signal — refund destination differs from the paying account — is the same
pattern regulators are moving to control directly. RBI's proposed "friction-by-design" plan for 2026
adds a mandatory delay specifically for payments to a **first-time payee**, i.e. exactly the moment a
refund is redirected to an account with no prior relationship to the user. The rule wasn't written to
match the regulation; it independently converged on the same signal.

Maximum raw sum is 125. Rather than clamping at 100 (which would make every bad case look identical),
the score is **compressed above a knee**:

```python
score = raw                      if raw <= 60
score = 60 + (raw - 60) * 0.53   otherwise, capped at 100
```

This keeps the 61–100 range meaningful instead of saturating.

### 2. Demo ML model (25%)

`RandomForestClassifier`, 180 trees, depth 9, trained on 6,000 synthetic rows.

Features: `transaction_amount`, `account_age_days`, `transaction_frequency`,
`time_to_refund_seconds`, `refund_amount_ratio`, `previous_suspicious_activity`,
`refund_destination_match`, `previous_reports`, `urgency_score`.

The generator draws scam and legitimate rows from deliberately overlapping distributions, then flips
4.5% of labels so the model cannot learn a trivial split. Where a public number exists, a distribution
is anchored to it instead of guessed: the fraud-class `transaction_amount` is centred on ~Rs 7,900,
matching the average loss per reported UPI fraud case in FY24–25 (Rs 1,087cr / 13.42 lakh cases,
Rs 981cr / 12.64 lakh cases — RBI/Parliament data). Every other distribution remains a stated design
assumption. Reported accuracy ≈ 0.96 and ROC-AUC ≈ 0.95
**describe the generator, not the real world** — every response carries that disclaimer, and the UI
never presents a model score as proof of fraud.

### 3. NLP analyzer (15%)

Nine explainable pattern groups: urgency, accidental-payment claims, third-party destinations,
refund requests, emotional pressure, authority impersonation, account excuses, credential requests
and off-platform pushes. Includes Hinglish variants (`galti se`, `jaldi`, `wapas`).

Two design decisions worth noting:
- **Saturating weights.** A second match in the same group adds half weight; a third adds nothing.
  Six urgency words are not six times more urgent than one.
- **Mitigating patterns.** Language like "as discussed" or "original account" *subtracts* from risk.
- Every signal returns the phrase that triggered it, so the report can quote its own reasoning.

### 4. Network analysis (15%)

A directed multi-type graph (senders, victims, transactions, refund destinations). Cluster risk
scales with fan-out: how many accounts one sender paid, how many distinct refund destinations were
supplied, and how many transactions link them. Layout is computed server-side with
`spring_layout` and shipped as pixel coordinates.

### Combining them

```
blended = Σ(weight × component) / Σ(weights present)
```

Components that produced no signal are dropped from the denominator rather than counted as zero.
When **three or more independent detectors** exceed 75, a corroboration bonus of +4 applies —
agreement across independent methods is genuine evidence. The result is capped at **98, never 100**,
because the system should not assert certainty about a person's intent.

Worked example (the flagship demo case):

```
rules 86 · ML 97% · message 94 · network 88
→ blended 89.7 + 4 corroboration = 94 / 100 CRITICAL → DO_NOT_REFUND
```

---

## Explainability

No screen ever shows a bare number. The reusable `RiskExplanation` component renders every
contributing signal with its weight, the layer that produced it, and the specific detail behind it:

```
+25  Refund destination is not the account the money came from
     Paid in from abc123@upi, refund requested to xyz987@upi
+20  Refund was requested very soon after the payment arrived
     4 minutes after the credit
+15  Money came from an account you have never transacted with
```

---

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/register` `/api/auth/login` | Auth; login errors are identical for unknown email and wrong password |
| GET/POST | `/api/lab/scam-presets`, `/account`, `/funds`, `/scam`, `/resolve` | Scam Lab: build-your-own scenario, including the clawback |
| POST | `/api/lab/batch` | Generates a randomised stream of refund requests and scores each |
| GET | `/api/auth/me` | Current user |
| GET | `/api/dashboard` | Aggregated home screen |
| GET | `/api/transactions` `?filter=&search=` | List with filters |
| GET | `/api/transactions/{reference}` | Detail with behaviour timeline |
| POST | `/api/risk/analyze-refund` | **The core endpoint** |
| POST | `/api/risk/analyze-message` | Message analysis |
| GET | `/api/risk/model-info` | Model metrics and disclaimer |
| GET/POST | `/api/refunds`, `/refunds/safe`, `/refunds/manual` | Refund flows |
| POST | `/api/safe-mode`, `/api/protection/*` | Protective states |
| GET/POST | `/api/evidence`, `/evidence/upload`, `/{id}/verify` | Evidence vault |
| GET/POST/PATCH | `/api/incidents` | Case lifecycle |
| POST | `/api/reports/generate`, `/{id}/pdf`, `/{id}/package` | Report and package |
| GET | `/api/admin/statistics`, `/risk-feed`, `/fraud-network` | Admin only (403 otherwise) |
| GET/POST | `/api/payments/config`, `/payments/order`, `/payments/verify` | Razorpay Test Mode intake |
| POST | `/api/webhooks/razorpay` | Provider callbacks, HMAC-verified |
| POST | `/api/simulation/scam`, `/simulation/reset` | Guided demo |

Interactive docs at `http://localhost:8000/docs`.

### Example

```bash
curl -X POST http://localhost:8000/api/risk/analyze-refund \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"transaction_id":"TX83921","refund_amount":8000,
       "original_sender":"abc123@upi","refund_destination":"xyz987@upi",
       "time_since_payment":180}'
```

```json
{
  "risk_score": 94, "safety_score": 6,
  "risk_level": "CRITICAL", "recommendation": "DO_NOT_REFUND",
  "reasons": ["Refund destination is not the account the money came from", "..."],
  "ml_disclaimer": "Demo model trained on synthetic data. Not validated on real transactions."
}
```

---

## Database schema

Thirteen tables: `users`, `emergency_protection_settings`, `transactions`, `transaction_events`,
`refund_requests`, `risk_assessments`, `fraud_signals`, `alerts`, `incidents`, `incident_events`,
`evidence`, `reports`, `fraud_networks`.

Every risk assessment is stored with its signals, so a score computed months ago can still be
explained. Composite indexes on `(user_id, created_at)` and `(user_id, status)` back the list views.

---

## Setup

### Fastest path (SQLite, no infrastructure)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload          # http://localhost:8000

# Frontend, in a second terminal
cd frontend
npm install
npm run dev                            # http://localhost:5173
```

The database is created and seeded on first boot.

### Running against real Razorpay Test Mode

```bash
export RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxx      # test keys only; live keys are refused
export RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxx
export RAZORPAY_WEBHOOK_SECRET=xxxxxxxxxxxxxxxx   # optional, for refund status callbacks
```

A **Receive a real Test Mode payment** card then appears on the Simulate screen. Point a Razorpay
dashboard webhook at `POST /api/webhooks/razorpay` (`refund.processed`, `refund.failed`,
`payment.captured`) to see refund status land on its own; signatures are verified against the raw
body and unsigned calls are rejected.

### Docker (PostgreSQL)

```bash
cp .env.example .env      # then set JWT_SECRET
docker compose up --build # frontend :8080, API :8000
```

### Demo account

```
demo@retrace.com
Demo@123
```

Seeded as **admin**, so one login shows both the user screens and the analyst dashboards. Register a
new account to see the empty-state behaviour instead.

### Scam Lab — build the scam yourself

The guided simulation plays a fixed script. **Scam Lab** lets you construct the situation instead, in
four steps, with the same risk engine scoring whatever you build:

1. **Open an account** — your own name, UPI handle and opening balance. It starts completely empty,
   so every transaction that follows is one you made. You are signed in as it; the generated password
   is shown once.
2. **Add funds** — ordinary money in. This matters: the scam only costs something if there is real
   balance behind the payment you send back.
3. **Bring in the scam** — choose the amount, who paid you, which handle they want the refund sent
   to, how many minutes later they ask, and the message itself. Four presets cover the classic
   accidental-transfer story, a Hinglish variant, support impersonation, and a genuine mistake as a
   control. Point the refund destination back at the paying account and watch the score collapse.
4. **Decide** — safe refund, or transfer manually.

The manual path is the only place the product plays out the **second loss**. The money is sent to the
scammer, then the original credit is disputed and clawed back: two debits against one credit, so the
balance ends one payment down. Opening at ₹50,000 and running an ₹8,000 scam ends at ₹42,000 on the
manual path and back at ₹50,000 on the safe one.

### Automated request streams

Under the four steps, **Generate requests** fires a batch of randomised refund requests at the
account — up to 25 — and scores each as it lands. The mix is roughly 60% scams, 20% borderline and
20% genuine mistakes, because a generator that only emitted obvious scams would show the engine
agreeing with itself rather than discriminating. Sender profile (how long the account has existed,
whether it is flagged, prior reports) is drawn independently of the refund destination, so scores
spread across a band instead of snapping to one value per category. A typical run of 20:

| Generated as | n | Risk range | Level |
|---|---|---|---|
| scam | 12 | 72–94 | HIGH → CRITICAL |
| borderline | 2 | 45–54 | MEDIUM |
| genuine | 6 | 16–23 | LOW |

The results table shows what each request *actually* was next to what the engine decided, so the two
can be compared directly. The engine never receives that label.

### Running the checks

```bash
cd backend && python smoke_test.py    # 39 end-to-end checks
cd frontend && npm run build          # type-check and production build
```

---

## Demo script (2–3 minutes)

1. Sign in with the demo account.
2. **Simulate scam** in the sidebar → **Transfer manually**.
3. The dial lands on 94/100 risk. Scroll the explanation — every weight is visible.
4. A case opens, Safe Mode turns on, the timeline builds, the evidence checklist starts at 6/7.
5. **Open the case** → **Generate report** → the PDF downloads.
6. **Reports** → **Evidence package** for the ZIP with `manifest.json` and hashes.
7. **Admin → Fraud network**: one paying account fanning out to seven victims and four destinations.
8. **Reset demo data**, then run it again choosing **Safe refund** — no case, because nothing was lost.

---

## Security

- Bcrypt password hashing (cost 12), 72-byte input clamp
- JWT bearer tokens with issuer validation; identical login errors regardless of which field is wrong
- Role-based access; admin routes return 403 for regular users
- Pydantic validation on every request body, with flattened plain-language error messages
- Uploads: extension allowlist, 15 MB streamed cap, sanitised filenames, path-traversal guard on
  every read, SHA-256 at intake with a re-verification endpoint
- All secrets from environment variables; no keys in source; passwords never logged
- **The app never asks for a UPI PIN, OTP, bank password, card CVV or net-banking login**

## Privacy

Financial evidence is sensitive, so the app collects as little as possible. All data is synthetic;
uploads stay on the server running the app; files are stored byte-for-byte with a fingerprint
recorded separately rather than being modified; any file can be deleted. See `GET /api/privacy`.

---

## Limitations

Worth stating plainly, because a demo that oversells itself is worse than one that doesn't:

- **Test Mode only, by construction.** With `rzp_test_` keys the app really does call Razorpay:
  Checkout collects a payment, and Safe Refund calls the refund API against that payment id. A live
  key is refused outright, so no real rupee can move. Without keys everything falls back to simulation.
- **The ML model proves nothing.** It is trained on data generated from the same assumptions the
  rules encode, so its agreement with the rules is partly circular. It is scaffolding for the
  architecture, not evidence of accuracy.
- **Rule weights are hand-set,** not learned from outcome data. With real labels they should be
  fitted, and calibrated so a score of 80 means something specific.
- **Safe Mode cannot stop a real transaction.** It is an application state.
- **The report is not a police report** and says so on every page.
- **Baseline analytics figures are illustrative,** added to real seeded counts so the dashboards look
  like a deployment. The API labels them as demonstration data.
- **No rate limiting, refresh tokens, or audit log** — all needed before this went near production.

## Future improvements

Calibrate scores against real outcome labels · replace the demo classifier with a
gradient-boosted model on real features and add SHAP for per-prediction attribution · move from regex
NLP to a fine-tuned classifier while keeping the rules as a fallback · graph embeddings for cluster
detection instead of fan-out heuristics · real provider integration for refunds · WebSocket risk feed
· evidence hash anchoring for stronger provenance · rate limiting and refresh-token rotation.

---

Built as an educational prototype. Not a licensed financial product, and not a substitute for
reporting fraud to your bank or to cybercrime.gov.in.
