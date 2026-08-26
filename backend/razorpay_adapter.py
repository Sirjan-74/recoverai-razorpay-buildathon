import os
import time
import requests

BASE_URL = "https://api.razorpay.com/v1"


def is_configured() -> bool:
    return bool(os.getenv("RAZORPAY_KEY_ID") and os.getenv("RAZORPAY_KEY_SECRET"))


def create_payment_link(transaction):
    """Create a Razorpay Test Mode Standard Payment Link for a recovery action."""
    if not is_configured():
        raise RuntimeError("Razorpay Test Mode credentials are not configured.")

    payload = {
        "amount": int(round(transaction.amount * 100)),
        "currency": "INR",
        "reference_id": f"recoverai-{transaction.transaction_id}-{int(time.time())}",
        "description": f"RecoverAI recovery for {transaction.transaction_id}",
        "customer": {"name": transaction.customer_name},
        "notify": {"email": False, "sms": False, "whatsapp": False},
        "reminder_enable": True,
    }

    response = requests.post(
        f"{BASE_URL}/payment_links",
        auth=(os.environ["RAZORPAY_KEY_ID"], os.environ["RAZORPAY_KEY_SECRET"]),
        json=payload,
        timeout=20,
    )
    response.raise_for_status()
    return response.json()
