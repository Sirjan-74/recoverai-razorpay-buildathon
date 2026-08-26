import random
from datetime import datetime, timedelta

from faker import Faker

from database import Base, engine, SessionLocal
from models import Transaction
from recovery import recommend

SEED = 42
COUNT = 1000

rng = random.Random(SEED)
fake = Faker("en_IN")
Faker.seed(SEED)

# Rebuild the local demo database so schema/data are always reproducible.
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

db = SessionLocal()

statuses = ["paid", "failed", "abandoned"]
reasons = ["timeout", "insufficient_funds", "bank_error"]

for i in range(1, COUNT + 1):
    status = rng.choices(statuses, weights=[55, 30, 15])[0]
    reason = None
    if status == "failed":
        reason = rng.choices(reasons, weights=[45, 35, 20])[0]
    elif status == "abandoned":
        reason = "checkout_abandoned"

    amount = round(rng.uniform(300, 15000), 2)
    attempts = rng.randint(0, 3) if status != "paid" else 0
    previous_successes = rng.randint(0, 8)
    customer_type = "returning" if previous_successes >= 2 else "new"

    if status == "failed" and reason == "timeout":
        recoverability = rng.uniform(0.78, 0.96)
    elif status == "failed" and reason == "insufficient_funds":
        recoverability = rng.uniform(0.35, 0.70)
    elif status == "failed" and reason == "bank_error":
        recoverability = rng.uniform(0.55, 0.85)
    elif status == "abandoned":
        recoverability = rng.uniform(0.45, 0.80)
    else:
        recoverability = 0.0

    tx = Transaction(
        transaction_id=f"TXN{i:05d}",
        customer_name=fake.name(),
        amount=amount,
        status=status,
        failure_reason=reason,
        attempt_count=attempts,
        previous_successes=previous_successes,
        customer_type=customer_type,
        recoverability=round(recoverability, 4),
        recommended_action="NO_ACTION",
        action_status="PENDING",
        recovered_amount=0.0,
        created_at=datetime.now() - timedelta(minutes=rng.randint(1, 60 * 24 * 30)),
    )
    db.add(tx)
    db.flush()
    tx.recommended_action = recommend(tx)["action"]


db.commit()
db.close()

print(f"Created {COUNT} deterministic synthetic transactions (seed={SEED}).")
