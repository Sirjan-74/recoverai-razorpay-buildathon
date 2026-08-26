from models import Transaction

MAX_RETRIES = 2
MAX_AUTO_ACTION_AMOUNT = 10000.0
AUTO_ACTIONS = {"RETRY", "SEND_PAYMENT_LINK"}
TERMINAL_STATUSES = {"RECOVERED", "ESCALATED", "APPROVAL_REQUIRED", "BLOCKED"}


def recommend(tx: Transaction):
    """Deterministic safety policy. AI may recommend, but this function authorizes the action."""
    if tx.status == "paid" or tx.action_status == "RECOVERED":
        return {
            "action": "NO_ACTION",
            "reason": "Payment is already successful or has already been recovered.",
            "allowed": False,
        }

    if tx.action_status == "APPROVAL_REQUIRED":
        return {
            "action": "REQUIRE_APPROVAL",
            "reason": "This transaction is waiting for merchant approval.",
            "allowed": False,
        }

    if tx.action_status == "ESCALATED":
        return {
            "action": "ESCALATE",
            "reason": "This case has already been escalated to a human operator.",
            "allowed": False,
        }

    if tx.action_status == "LINK_CREATED":
        return {
            "action": "WAIT_FOR_PAYMENT",
            "reason": "A recovery payment link is already active; wait for payment confirmation.",
            "allowed": False,
        }

    if tx.attempt_count >= MAX_RETRIES:
        return {
            "action": "ESCALATE",
            "reason": "Maximum recovery attempts reached.",
            "allowed": True,
        }

    if tx.amount > MAX_AUTO_ACTION_AMOUNT:
        return {
            "action": "REQUIRE_APPROVAL",
            "reason": "Amount exceeds the automatic-action threshold.",
            "allowed": True,
        }

    if tx.status == "abandoned":
        return {
            "action": "SEND_PAYMENT_LINK",
            "reason": "Checkout was abandoned; a payment link is an appropriate bounded recovery action.",
            "allowed": True,
        }

    if tx.failure_reason == "timeout":
        return {
            "action": "RETRY",
            "reason": "Timeout is potentially transient and the retry limit has not been reached.",
            "allowed": True,
        }

    if tx.failure_reason == "bank_error":
        return {
            "action": "RETRY",
            "reason": "Bank-side error may be transient; bounded retry is allowed.",
            "allowed": True,
        }

    if tx.failure_reason == "insufficient_funds":
        return {
            "action": "SEND_PAYMENT_LINK",
            "reason": "A later payment attempt is more appropriate than an immediate retry.",
            "allowed": True,
        }

    return {
        "action": "ESCALATE",
        "reason": "No safe automatic recovery strategy matched.",
        "allowed": True,
    }
