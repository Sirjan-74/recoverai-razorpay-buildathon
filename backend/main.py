from datetime import datetime
import hashlib
import hmac
import json
import os

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import Base, engine, get_db
from models import Transaction, AuditLog
from recovery import recommend, MAX_RETRIES
from ai_agent import analyze_transaction
from batch_evaluation import evaluate_batch

Base.metadata.create_all(bind=engine)

RECOVERY_MODE = os.getenv("RECOVERY_MODE", "demo").lower()

app = FastAPI(
    title="RecoverAI API",
    description="AI Revenue Recovery Agent — Razorpay AI Buildathon Track 3",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return RedirectResponse(url="/docs")


def now():
    return datetime.now()


def audit(db, transaction_id, event, details):
    db.add(
        AuditLog(
            transaction_id=transaction_id,
            event=event,
            details=details if isinstance(details, str) else json.dumps(details),
            created_at=now(),
        )
    )


def demo_success(transaction):
    """Reproducible synthetic outcome for local demonstrations only."""
    score = int(
        hashlib.sha256(transaction.transaction_id.encode()).hexdigest()[:8],
        16,
    ) % 100
    return score < round(transaction.recoverability * 100)


def find_tx(db, transaction_id):
    tx = (
        db.query(Transaction)
        .filter(Transaction.transaction_id == transaction_id)
        .first()
    )
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "RecoverAI",
        "recovery_mode": RECOVERY_MODE,
        "max_retries": MAX_RETRIES,
    }


@app.get("/api/metrics")
def metrics(db: Session = Depends(get_db)):
    total = db.query(Transaction).count()

    at_risk = (
        db.query(func.sum(Transaction.amount))
        .filter(
            Transaction.status.in_(["failed", "abandoned"]),
            Transaction.action_status != "RECOVERED",
        )
        .scalar()
        or 0
    )

    pending = (
        db.query(Transaction)
        .filter(
            Transaction.status.in_(["failed", "abandoned"]),
            Transaction.action_status.in_(["PENDING", "ATTEMPTED", "LINK_CREATED"]),
        )
        .count()
    )

    recovered = (
        db.query(func.sum(Transaction.recovered_amount))
        .filter(Transaction.action_status == "RECOVERED")
        .scalar()
        or 0
    )

    attempted = (
        db.query(Transaction)
        .filter(Transaction.attempt_count > 0)
        .count()
    )

    recovered_count = (
        db.query(Transaction)
        .filter(Transaction.action_status == "RECOVERED")
        .count()
    )

    approval_required = (
        db.query(Transaction)
        .filter(Transaction.action_status == "APPROVAL_REQUIRED")
        .count()
    )

    escalated = (
        db.query(Transaction)
        .filter(Transaction.action_status == "ESCALATED")
        .count()
    )

    recovery_rate = (recovered_count / attempted) * 100 if attempted else 0

    return {
        "total_transactions": total,
        "revenue_at_risk": round(at_risk, 2),
        "pending_cases": pending,
        "revenue_recovered": round(recovered, 2),
        "recovery_attempts": attempted,
        "recovered_count": recovered_count,
        "recovery_rate": round(recovery_rate, 2),
        "approval_required": approval_required,
        "escalated_cases": escalated,
        "recovery_mode": RECOVERY_MODE,
    }


@app.get("/api/batch-evaluation")
def batch_evaluation(limit: int = 100, db: Session = Depends(get_db)):
    limit = max(10, min(limit, 500))
    rows = (
        db.query(Transaction)
        .filter(Transaction.status.in_(["failed", "abandoned"]))
        .order_by(Transaction.created_at.desc())
        .limit(limit)
        .all()
    )
    return evaluate_batch(rows, limit=limit)


@app.get("/api/transactions")
def transactions(limit: int = 100, db: Session = Depends(get_db)):
    limit = max(1, min(limit, 500))
    rows = (
        db.query(Transaction)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
        .all()
    )

    result = []
    for x in rows:
        decision = recommend(x)
        result.append(
            {
                "id": x.id,
                "transaction_id": x.transaction_id,
                "customer_name": x.customer_name,
                "amount": x.amount,
                "status": x.status,
                "failure_reason": x.failure_reason,
                "attempt_count": x.attempt_count,
                "previous_successes": x.previous_successes,
                "recoverability": round(x.recoverability * 100, 1),
                "recommended_action": decision["action"],
                "policy_reason": decision["reason"],
                "action_status": x.action_status,
                "recovery_link_url": x.recovery_link_url,
                "recovered_amount": x.recovered_amount,
                "created_at": x.created_at.isoformat(),
            }
        )
    return result


@app.get("/api/transactions/{transaction_id}")
def transaction_detail(transaction_id: str, db: Session = Depends(get_db)):
    tx = find_tx(db, transaction_id)
    decision = recommend(tx)

    logs = (
        db.query(AuditLog)
        .filter(AuditLog.transaction_id == tx.transaction_id)
        .order_by(AuditLog.created_at.desc())
        .all()
    )

    return {
        "transaction": {
            "transaction_id": tx.transaction_id,
            "customer_name": tx.customer_name,
            "amount": tx.amount,
            "status": tx.status,
            "failure_reason": tx.failure_reason,
            "attempt_count": tx.attempt_count,
            "previous_successes": tx.previous_successes,
            "recoverability": round(tx.recoverability * 100, 1),
            "recommended_action": decision["action"],
            "action_status": tx.action_status,
            "recovery_link_url": tx.recovery_link_url,
            "recovered_amount": tx.recovered_amount,
        },
        "decision": decision,
        "audit": [
            {
                "event": log.event,
                "details": log.details,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
    }


@app.post("/api/recovery/{transaction_id}")
def execute_recovery(transaction_id: str, db: Session = Depends(get_db)):
    tx = find_tx(db, transaction_id)
    decision = recommend(tx)

    audit(
        db,
        tx.transaction_id,
        "POLICY_DECISION",
        {
            "action": decision["action"],
            "allowed": decision["allowed"],
            "reason": decision["reason"],
        },
    )

    if not decision["allowed"]:
        db.commit()
        return {
            "success": False,
            "message": decision["reason"],
            "action": decision["action"],
            "mode": RECOVERY_MODE,
        }

    if decision["action"] == "ESCALATE":
        tx.action_status = "ESCALATED"
        audit(db, tx.transaction_id, "ESCALATED", decision["reason"])
        db.commit()
        return {
            "success": True,
            "message": "Case escalated to a human operator.",
            "action": "ESCALATE",
            "mode": RECOVERY_MODE,
        }

    if decision["action"] == "REQUIRE_APPROVAL":
        tx.action_status = "APPROVAL_REQUIRED"
        audit(db, tx.transaction_id, "APPROVAL_REQUIRED", decision["reason"])
        db.commit()
        return {
            "success": True,
            "message": "Merchant approval is required before recovery.",
            "action": "REQUIRE_APPROVAL",
            "mode": RECOVERY_MODE,
        }

    # Only bounded recovery actions reach this point.
    if decision["action"] in {"RETRY", "SEND_PAYMENT_LINK"}:
        if tx.attempt_count >= MAX_RETRIES:
            raise HTTPException(status_code=409, detail="Retry limit reached")

        tx.attempt_count += 1
        audit(
            db,
            tx.transaction_id,
            "RECOVERY_ATTEMPTED",
            f"Bounded {decision['action']} action started in {RECOVERY_MODE} mode.",
        )

        if RECOVERY_MODE == "razorpay_test":
            if decision["action"] in {"RETRY", "SEND_PAYMENT_LINK"}:
                from razorpay_adapter import create_payment_link

                try:
                    link = create_payment_link(tx)
                except Exception as exc:
                    tx.action_status = "FAILED"
                    audit(db, tx.transaction_id, "RECOVERY_FAILED", str(exc))
                    db.commit()
                    return {
                        "success": False,
                        "message": "Razorpay Test Mode recovery could not be started.",
                        "action": decision["action"],
                        "error": str(exc),
                    }

                tx.action_status = "LINK_CREATED"
                tx.recovery_link_id = link.get("id")
                tx.recovery_link_url = link.get("short_url")
                audit(
                    db,
                    tx.transaction_id,
                    "RECOVERY_LINK_CREATED",
                    json.dumps({"id": tx.recovery_link_id, "url": tx.recovery_link_url}),
                )
                db.commit()
                return {
                    "success": True,
                    "message": "Razorpay Test Mode recovery link created. Recovery is counted only after payment confirmation.",
                    "action": decision["action"],
                    "mode": RECOVERY_MODE,
                    "payment_link": tx.recovery_link_url,
                }

        # Demo mode is deliberately deterministic and explicitly simulated.
        if demo_success(tx):
            tx.action_status = "RECOVERED"
            tx.recovered_amount = tx.amount
            audit(
                db,
                tx.transaction_id,
                "DEMO_RECOVERY_SUCCEEDED",
                f"Synthetic {decision['action']} outcome succeeded. No live payment was made.",
            )
            db.commit()
            return {
                "success": True,
                "message": f"Demo {decision['action']} succeeded (synthetic outcome; no live payment).",
                "action": decision["action"],
                "mode": "demo",
                "amount_recovered": tx.amount,
            }

        tx.action_status = "ATTEMPTED"
        audit(
            db,
            tx.transaction_id,
            "DEMO_RECOVERY_NOT_CONFIRMED",
            f"Synthetic {decision['action']} outcome did not recover the transaction.",
        )
        db.commit()
        return {
            "success": True,
            "message": f"Demo {decision['action']} was attempted but not recovered.",
            "action": decision["action"],
            "mode": "demo",
            "amount_recovered": 0,
        }

    raise HTTPException(status_code=409, detail="No executable recovery action")


@app.post("/api/transactions/{transaction_id}/analyze")
def analyze_transaction_ai(transaction_id: str, db: Session = Depends(get_db)):
    tx = find_tx(db, transaction_id)
    result = analyze_transaction(tx)

    audit(db, tx.transaction_id, "AI_ANALYSIS", result)
    db.commit()

    return {
        "transaction_id": tx.transaction_id,
        "ai_analysis": result,
    }


@app.post("/api/webhooks/razorpay")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    """Verify Razorpay webhook signature and mark a recovery link paid."""
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(status_code=503, detail="Razorpay webhook secret is not configured")

    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing Razorpay signature")

    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="Invalid Razorpay webhook signature")

    payload = json.loads(body.decode("utf-8"))
    event = payload.get("event")
    link_entity = payload.get("payload", {}).get("payment_link", {}).get("entity", {})
    link_id = link_entity.get("id")

    if event == "payment_link.paid" and link_id:
        tx = (
            db.query(Transaction)
            .filter(Transaction.recovery_link_id == link_id)
            .first()
        )
        if tx:
            paid_amount = float(link_entity.get("amount_paid", 0)) / 100
            tx.status = "paid"
            tx.action_status = "RECOVERED"
            tx.recovered_amount = paid_amount
            audit(
                db,
                tx.transaction_id,
                "RECOVERY_CONFIRMED",
                json.dumps({"payment_link_id": link_id, "amount_recovered": paid_amount}),
            )
            db.commit()

    return {"received": True, "event": event}
