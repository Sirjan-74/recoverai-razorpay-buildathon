from types import SimpleNamespace

from recovery import MAX_AUTO_ACTION_AMOUNT, MAX_RETRIES, recommend


def tx(**overrides):
    values = dict(
        status="failed",
        action_status="PENDING",
        amount=5000,
        attempt_count=0,
        failure_reason="timeout",
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_timeout_retries_when_bounded():
    result = recommend(tx())
    assert result["action"] == "RETRY"
    assert result["allowed"] is True


def test_retry_limit_escalates():
    result = recommend(tx(attempt_count=MAX_RETRIES))
    assert result["action"] == "ESCALATE"


def test_high_value_requires_approval():
    result = recommend(tx(amount=MAX_AUTO_ACTION_AMOUNT + 1))
    assert result["action"] == "REQUIRE_APPROVAL"
    assert result["allowed"] is True


def test_abandoned_sends_link():
    result = recommend(tx(status="abandoned", failure_reason="checkout_abandoned"))
    assert result["action"] == "SEND_PAYMENT_LINK"


def test_recovered_is_terminal():
    result = recommend(tx(action_status="RECOVERED"))
    assert result["action"] == "NO_ACTION"
    assert result["allowed"] is False


def test_existing_link_waits():
    result = recommend(tx(action_status="LINK_CREATED"))
    assert result["action"] == "WAIT_FOR_PAYMENT"
    assert result["allowed"] is False
