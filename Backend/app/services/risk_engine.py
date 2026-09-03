from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    PaymentAttempt,
    Transaction,
)


@dataclass
class RiskAssessment:
    transaction_id: int
    amount_at_risk: Decimal
    risk_score: int
    risk_level: str
    reason: str
    recommended_action: str
    stopping_rule: str


FAILURE_CATEGORIES = {
    "timeout": "transient",
    "network_error": "transient",
    "processor_unavailable": "transient",
    "insufficient_funds": "recoverable",
    "card_expired": "recoverable",
    "card_declined": "recoverable",
    "do_not_honor": "hard_failure",
    "fraud_suspected": "hard_failure",
}


def calculate_risk(
    db: Session,
    transaction: Transaction,
) -> RiskAssessment:

    # ---------------------------------------------------------
    # 1. Start with the transaction's current state
    # ---------------------------------------------------------

    if transaction.status == "successful":
        return RiskAssessment(
            transaction_id=transaction.id,
            amount_at_risk=Decimal("0.00"),
            risk_score=0,
            risk_level="none",
            reason="Payment has already succeeded.",
            recommended_action="no_action",
            stopping_rule="Stop immediately because revenue is already recovered.",
        )

    score = 0
    reasons = []

    # ---------------------------------------------------------
    # 2. Determine the type of revenue risk
    # ---------------------------------------------------------

    if transaction.status == "failed":
        score += 70
        reasons.append("Payment failure detected.")

    elif transaction.status == "abandoned":
        score += 55
        reasons.append("Checkout was abandoned before payment completion.")

    elif transaction.status == "overdue":
        score += 65
        reasons.append("Invoice payment is overdue.")

    # ---------------------------------------------------------
    # 3. Examine payment failure details
    # ---------------------------------------------------------

    latest_attempt = db.scalar(
        select(PaymentAttempt)
        .where(
            PaymentAttempt.transaction_id == transaction.id
        )
        .order_by(PaymentAttempt.attempted_at.desc())
        .limit(1)
    )

    failure_category = None

    if latest_attempt:
        failure_category = FAILURE_CATEGORIES.get(
            latest_attempt.failure_code
        )

        if failure_category == "transient":
            score += 15
            reasons.append(
                "Failure appears transient and may succeed on retry."
            )

        elif failure_category == "recoverable":
            score += 10
            reasons.append(
                "Failure may be resolved by customer intervention."
            )

        elif failure_category == "hard_failure":
            score -= 30
            reasons.append(
                "Failure indicates a hard decline or elevated risk."
            )

    # ---------------------------------------------------------
    # 4. Consider transaction value
    # ---------------------------------------------------------

    if transaction.amount >= Decimal("50000"):
        score += 10
        reasons.append("High-value transaction increases recovery priority.")

    elif transaction.amount < Decimal("2000"):
        score -= 5

    # ---------------------------------------------------------
    # 5. Examine previous successful transactions
    # ---------------------------------------------------------

    successful_count = db.scalar(
        select(func.count(Transaction.id))
        .where(
            Transaction.customer_id == transaction.customer_id,
            Transaction.status == "successful",
        )
    ) or 0

    if successful_count >= 3:
        score += 10
        reasons.append(
            "Customer has a history of successful payments."
        )

    # ---------------------------------------------------------
    # 6. Count previous payment attempts
    # ---------------------------------------------------------

    attempt_count = db.scalar(
        select(func.count(PaymentAttempt.id))
        .where(
            PaymentAttempt.transaction_id == transaction.id
        )
    ) or 0

    if attempt_count >= 3:
        score -= 15
        reasons.append(
            "Multiple payment attempts already occurred."
        )

    # ---------------------------------------------------------
    # 7. Clamp score
    # ---------------------------------------------------------

    score = max(0, min(100, score))

    # ---------------------------------------------------------
    # 8. Determine risk level
    # ---------------------------------------------------------

    if score >= 75:
        risk_level = "high"

    elif score >= 50:
        risk_level = "medium"

    else:
        risk_level = "low"

    # ---------------------------------------------------------
    # 9. Determine recommended recovery action
    # ---------------------------------------------------------

    if transaction.status == "abandoned":
        recommended_action = "send_checkout_reminder"
        stopping_rule = (
            "Maximum 2 reminders. Stop immediately if checkout completes."
        )

    elif transaction.status == "overdue":
        recommended_action = "send_invoice_reminder"
        stopping_rule = (
            "Maximum 3 reminders. Escalate if payment remains overdue."
        )

    elif failure_category == "transient":
        recommended_action = "retry_payment"
        stopping_rule = (
            "Maximum 2 automated retries. Stop after success or repeated failure."
        )

    elif failure_category == "recoverable":
        if latest_attempt and latest_attempt.failure_code == "card_expired":
            recommended_action = "request_payment_method_update"
        else:
            recommended_action = "send_payment_recovery_link"

        stopping_rule = (
            "One customer intervention request followed by escalation."
        )

    elif failure_category == "hard_failure":
        recommended_action = "manual_review"
        stopping_rule = (
            "Do not automatically retry. Escalate for manual review."
        )

    else:
        recommended_action = "manual_review"
        stopping_rule = (
            "Do not execute an automated recovery action without classification."
        )

    return RiskAssessment(
        transaction_id=transaction.id,
        amount_at_risk=transaction.amount,
        risk_score=score,
        risk_level=risk_level,
        reason=" ".join(reasons),
        recommended_action=recommended_action,
        stopping_rule=stopping_rule,
    )