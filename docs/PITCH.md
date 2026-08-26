# RecoverAI — 5-minute pitch outline

## 0:00–0:30 — Problem

Failed payments and abandoned checkouts create revenue leakage. Merchants need an agent that can decide what is recoverable without allowing an LLM to take unsafe payment actions.

## 0:30–1:15 — Product

RecoverAI turns a transaction into a closed-loop workflow:

**Detect → Diagnose → Decide → Bound → Recover → Confirm → Audit**

Show the dashboard and transaction queue.

## 1:15–2:15 — AI + safety

Open a transaction and run Gemini.

Explain:

> Gemini diagnoses the likely cause and recovery strategy. It never authorizes the action.

Show the deterministic policy:

- maximum 2 attempts
- automatic actions capped at ₹10,000
- high-value transactions require approval
- exhausted cases escalate

## 2:15–3:15 — Recovery

In Demo Mode, show a deterministic synthetic recovery and immediately show the audit event.

For the strongest Razorpay demonstration, use Test Mode and create a Standard Payment Link. Explain that RecoverAI does **not** count revenue as recovered until `payment_link.paid` is received and the webhook signature is verified.

## 3:15–4:15 — Batch evidence

Run the 100-case synthetic evaluation.

Show:

- auto-eligible cases
- approval cases
- escalations
- synthetic recovered cases/value
- synthetic recovery rate

Be explicit that these are synthetic evaluation results unless you are showing Test Mode-confirmed payments.

## 4:15–5:00 — Why this architecture

The key differentiation is the separation of intelligence from authority:

**Gemini diagnoses. Policy authorizes. Executor acts. Webhook confirms. Audit log proves.**

End with the extension path: Test Mode → webhooks → merchant notifications → larger held-out evaluation.
