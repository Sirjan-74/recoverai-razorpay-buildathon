from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, unique=True, index=True, nullable=False)
    customer_name = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String, nullable=False)
    failure_reason = Column(String, nullable=True)
    attempt_count = Column(Integer, default=0, nullable=False)
    previous_successes = Column(Integer, default=0, nullable=False)
    customer_type = Column(String, default="new")
    recoverability = Column(Float, default=0.0, nullable=False)
    recommended_action = Column(String, default="NO_ACTION", nullable=False)
    action_status = Column(String, default="PENDING", nullable=False)
    recovery_link_id = Column(String, nullable=True)
    recovery_link_url = Column(String, nullable=True)
    recovered_amount = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, index=True, nullable=False)
    event = Column(String, nullable=False)
    details = Column(Text)
    created_at = Column(DateTime, nullable=False)
