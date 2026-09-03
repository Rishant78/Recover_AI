from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    PaymentAttempt,
    RecoveryAction,
    RecoveryCase,
    Transaction,
)


@dataclass
class GuardrailResult:
    approved: bool
    action: str
    reason: str
    violations: list[str]


MAX_AUTOMATED_RETRIES = 2


def validate_recovery_action(
    db: Session,
    transaction: Transaction,
    recovery_case: RecoveryCase,
    proposed_action: str,
) -> GuardrailResult:

    violations: list[str] = []

    # ---------------------------------------------------------
    # 1. Recovery case must still be open
    # ---------------------------------------------------------

    if recovery_case.status != "open":
        violations.append(
            "Recovery case is no longer open."
        )

    # ---------------------------------------------------------
    # 2. Successful payment = immediate stop
    # ---------------------------------------------------------

    if transaction.status == "successful":
        violations.append(
            "Payment has already succeeded."
        )

    # ---------------------------------------------------------
    # 3. Load latest payment attempt (single query,
    #    reused for both attempt count and hard-failure check)
    # ---------------------------------------------------------

    attempts = db.scalars(
        select(PaymentAttempt)
        .where(
            PaymentAttempt.transaction_id == transaction.id
        )
        .order_by(PaymentAttempt.attempted_at.desc())
    ).all()

    attempt_count = len(attempts)
    latest_attempt = attempts[0] if attempts else None

    # ---------------------------------------------------------
    # 4. Enforce retry limit
    # ---------------------------------------------------------

    if proposed_action == "retry_payment":

        if attempt_count >= MAX_AUTOMATED_RETRIES:
            violations.append(
                f"Maximum automated retries reached ({MAX_AUTOMATED_RETRIES})."
            )

    # ---------------------------------------------------------
    # 5. Prevent retrying hard failures
    # ---------------------------------------------------------

    if proposed_action == "retry_payment":

        if latest_attempt:

            hard_failure_codes = {
                "DO_NOT_HONOR",
                "FRAUD_SUSPECTED",
            }

            if latest_attempt.failure_code in hard_failure_codes:
                violations.append(
                    "Payment failure is classified as a hard failure."
                )

    # ---------------------------------------------------------
    # 6. Prevent automated recovery on zero-value transactions
    # ---------------------------------------------------------

    if proposed_action != "manual_review":

        if transaction.amount <= Decimal("0.00"):
            violations.append(
                "Transaction amount must be greater than zero."
            )

    # ---------------------------------------------------------
    # 7. Prevent duplicate action execution
    #    (idempotency guard at the guardrail level)
    # ---------------------------------------------------------

    existing_action_count = db.scalar(
        select(func.count(RecoveryAction.id))
        .where(
            RecoveryAction.recovery_case_id == recovery_case.id,
            RecoveryAction.action_type == proposed_action,
        )
    ) or 0

    if proposed_action != "manual_review" and existing_action_count > 0:
        violations.append(
            f"Action '{proposed_action}' has already been executed for this case."
        )

    # ---------------------------------------------------------
    # 8. Final decision
    # ---------------------------------------------------------

    if violations:

        return GuardrailResult(
            approved=False,
            action="manual_review",
            reason="Recovery action blocked by guardrails.",
            violations=violations,
        )

    return GuardrailResult(
        approved=True,
        action=proposed_action,
        reason="Recovery action passed all guardrail checks.",
        violations=[],
    )