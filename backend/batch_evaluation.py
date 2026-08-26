import hashlib
from recovery import recommend


def _score(transaction_id: str) -> int:
    return int(hashlib.sha256(transaction_id.encode()).hexdigest()[:8], 16) % 100


def evaluate_batch(transactions, limit=100):
    """Run a reproducible synthetic recovery evaluation without mutating live transactions."""
    cases = transactions[:limit]
    counts = {
        "total": len(cases),
        "auto_eligible": 0,
        "approval_required": 0,
        "escalated": 0,
        "no_action": 0,
        "simulated_recovered": 0,
    }
    at_risk = 0.0
    recovered_value = 0.0
    examples = []

    for tx in cases:
        decision = recommend(tx)
        if tx.status in {"failed", "abandoned"} and tx.action_status != "RECOVERED":
            at_risk += tx.amount

        if decision["action"] in {"RETRY", "SEND_PAYMENT_LINK"} and decision["allowed"]:
            counts["auto_eligible"] += 1
            recovered = _score(tx.transaction_id) < round(tx.recoverability * 100)
            if recovered:
                counts["simulated_recovered"] += 1
                recovered_value += tx.amount
            if len(examples) < 10:
                examples.append({
                    "transaction_id": tx.transaction_id,
                    "action": decision["action"],
                    "recoverability": round(tx.recoverability * 100, 1),
                    "outcome": "RECOVERED" if recovered else "NOT_RECOVERED",
                })
        elif decision["action"] == "REQUIRE_APPROVAL":
            counts["approval_required"] += 1
        elif decision["action"] == "ESCALATE":
            counts["escalated"] += 1
        else:
            counts["no_action"] += 1

    rate = (
        counts["simulated_recovered"] / counts["auto_eligible"] * 100
        if counts["auto_eligible"]
        else 0
    )

    return {
        "mode": "SYNTHETIC_EVALUATION",
        "note": "Deterministic demo outcomes; these are not live Razorpay payments.",
        "counts": counts,
        "at_risk_value": round(at_risk, 2),
        "simulated_recovered_value": round(recovered_value, 2),
        "simulated_recovery_rate": round(rate, 2),
        "examples": examples,
    }
