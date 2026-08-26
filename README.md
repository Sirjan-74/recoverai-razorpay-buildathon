# RecoverAI — AI Revenue Recovery Agent

RecoverAI is a full-stack Track 3 submission for the **Razorpay AI Buildathon: AI Revenue Recovery**. It detects revenue at risk, uses Gemini for diagnosis, applies a deterministic safety policy, executes a bounded recovery workflow, and records an auditable trail.

## What the project demonstrates

**Detect → Diagnose → Decide → Bound → Recover → Confirm → Audit**

- **Detect:** synthetic payment failures and checkout abandonment are stored in SQLite.
- **Diagnose:** Gemini analyzes the transaction and returns structured risk/cause/strategy/confidence data.
- **Decide:** a deterministic policy engine decides the final action. Gemini never authorizes money movement.
- **Bound:** automatic recovery is limited to ₹10,000 and two attempts; high-value cases require approval and exhausted cases escalate.
- **Recover:** Demo Mode provides deterministic synthetic outcomes. Optional Razorpay Test Mode creates real Test Mode Payment Links for recovery actions.
- **Confirm:** in Razorpay Test Mode, recovered revenue is counted only after a verified `payment_link.paid` webhook.
- **Audit:** policy decisions, AI analysis, attempts, link creation, escalation, and recovery confirmation are logged.

## Razorpay Track 3 alignment

The current Razorpay AI Buildathon Track 3 asks builders to detect revenue at risk, determine the right intervention, and execute a bounded recovery workflow. The stated bar is **measured recovery across a batch, compliant escalation, stopping rules, and an audit trail**.

RecoverAI addresses each requirement:

| Requirement | RecoverAI implementation |
|---|---|
| Detect revenue at risk | Failed + abandoned transaction queue and risk metrics |
| Determine intervention | Gemini diagnosis + deterministic recovery policy |
| Bounded workflow | 2-attempt limit + ₹10,000 auto-action cap |
| Compliant escalation | `ESCALATE` and `REQUIRE_APPROVAL` states |
| Batch evidence | 100-case reproducible synthetic evaluation endpoint |
| Audit trail | SQLite `audit_logs` for AI, policy and recovery events |
| Real test integration | Optional Razorpay Test Mode Payment Links + webhook confirmation |

## Architecture

```text
                    ┌──────────────────────┐
                    │   React + Vite UI     │
                    │ Queue / Metrics / AI  │
                    └──────────┬───────────┘
                               │ HTTP
                    ┌──────────▼───────────┐
                    │      FastAPI         │
                    │ API + Webhook layer  │
                    └──────┬───────┬───────┘
                           │       │
              ┌────────────▼─┐   ┌─▼────────────────┐
              │ SQLite       │   │ Gemini diagnosis  │
              │ transactions │   │ diagnosis only   │
              │ audit_logs   │   └──────────────────┘
              └──────┬───────┘
                     │
              ┌──────▼──────────┐
              │ Deterministic   │
              │ Policy Engine   │
              │ retries / cap   │
              │ approval / esc. │
              └──────┬──────────┘
                     │
          ┌──────────▼───────────┐
          │ Recovery Executor    │
          │ Demo OR Razorpay     │
          │ Test Mode Link       │
          └──────────┬───────────┘
                     │
              payment_link.paid
                     │
              ┌──────▼───────┐
              │ RECOVERED +  │
              │ Audit Log    │
              └──────────────┘
```

## Safety model

The important design choice is that **AI does not control money-moving actions**.

Gemini can say that a timeout looks transient and recommend a retry. The deterministic policy still checks the transaction status, retry count and amount before any recovery action can run.

Rules:

- Paid/recovered transaction → `NO_ACTION`
- Attempts ≥ 2 → `ESCALATE`
- Amount > ₹10,000 → `REQUIRE_APPROVAL`
- Abandoned checkout → `SEND_PAYMENT_LINK`
- Timeout / bank error → bounded `RETRY`
- Insufficient funds → `SEND_PAYMENT_LINK`
- Unknown failure → `ESCALATE`
- Existing recovery link → wait for payment confirmation

## Recovery modes

### Demo Mode (default)

```env
RECOVERY_MODE=demo
```

Demo recovery uses a reproducible synthetic outcome based on the transaction's recoverability score. The UI explicitly labels the value as **Demo Recovered Value**. No live payment is made.

This makes the project runnable without exposing or requiring Razorpay credentials.

### Razorpay Test Mode

```env
RECOVERY_MODE=razorpay_test
RAZORPAY_KEY_ID=...
RAZORPAY_KEY_SECRET=...
RAZORPAY_WEBHOOK_SECRET=...
```

For `RETRY` and `SEND_PAYMENT_LINK`, RecoverAI creates a Razorpay Test Mode Standard Payment Link. The transaction remains `LINK_CREATED` until the server receives and verifies the `payment_link.paid` webhook. Only then is `recovered_amount` recorded.

Razorpay's Payment Link API accepts an amount in the smallest currency unit and supports Test Mode links. Razorpay also documents the `payment_link.paid` webhook event for confirmed payment-link recovery.

## Batch evidence

`GET /api/batch-evaluation?limit=100` evaluates 100 failed/abandoned synthetic cases without mutating live transactions.

It reports:

- batch size
- auto-eligible cases
- approval-required cases
- escalated cases
- deterministic synthetic recovered cases
- synthetic recovered value
- synthetic recovery rate
- representative outcomes

The README and UI deliberately call these **synthetic evaluation results**. They must not be presented as live Razorpay revenue.

## Project structure

```text
recover-ai/
├── backend/
│   ├── ai_agent.py
│   ├── batch_evaluation.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   ├── razorpay_adapter.py
│   ├── recovery.py
│   ├── seed.py
│   ├── test_recovery.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── .env.example
│   ├── package.json
│   └── vite.config.js
├── docs/
│   └── PITCH.md
├── .gitignore
└── README.md
```

## Run locally

### 1. Backend

Open PowerShell in `backend`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create `.env` from `.env.example` and add your Gemini key:

```env
LLM_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.6-flash
RECOVERY_MODE=demo
```

Seed the reproducible demo database:

```powershell
python seed.py
```

Start FastAPI:

```powershell
uvicorn main:app --reload
```

Open:

- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`

### 2. Frontend

Open a second terminal in `frontend`:

```powershell
npm install
npm run dev
```

Open the Vite URL, normally `http://localhost:5173`.

## Test the policy engine

From `backend`:

```powershell
pytest -q
```

The tests cover the key safety boundaries: retries, high-value approval, abandonment, recovered terminal state, and an already-created recovery link.

## Demo flow

1. Start the backend and frontend.
2. Show the revenue-at-risk dashboard.
3. Inspect a failed or abandoned transaction.
4. Run **Analyze with Gemini** and explain that AI is diagnosis-only.
5. Show the deterministic policy action and its safety reason.
6. Execute one bounded recovery in Demo Mode, or create a Test Mode Payment Link when Razorpay credentials are configured.
7. Show the Audit Trail.
8. Run the 100-case batch evaluation and explain the measured synthetic evidence.
9. Show an approval-required or escalated case to demonstrate stopping rules.

## Security / submission hygiene

Never commit:

- `.env`
- Razorpay secrets
- Gemini API keys
- `.venv/`
- `node_modules/`
- `recoverai.db`
- `__pycache__/`

Only `.env.example` should be committed.

## Important honesty note

This repository supports both a safe local Demo Mode and an optional Razorpay Test Mode integration. **Do not describe synthetic demo outcomes as real money recovered.** For a real recovery claim, use Razorpay Test Mode and show the verified payment-link confirmation path.
