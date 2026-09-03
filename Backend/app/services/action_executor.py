from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AgentDecision,
    AuditEvent,
    PaymentAttempt,
    RecoveryAction,
    RecoveryCase,
    Transaction,
)


@dataclass
class ActionExecutionResult:
    action: str
    status: str
    message: str
    amount_recovered: Decimal


MAX_AUTOMATED_RETRIES = 2


def execute_recovery_action(
    db: Session,
    recovery_case: RecoveryCase,
    decision: AgentDecision,
) -> ActionExecutionResult:

    transaction = recovery_case.transaction

    # =========================================================
    # 1. GLOBAL STOP CONDITIONS
    # =========================================================

    if transaction.status == "successful":
        return _stop(
            db,
            recovery_case,
            "Payment already succeeded. Recovery workflow stopped.",
        )

    if recovery_case.status in {"resolved", "escalated", "closed"}:
        return _stop(
            db,
            recovery_case,
            f"Recovery case is already {recovery_case.status}.",
        )

    # =========================================================
    # 2. DETERMINE PREVIOUS AUTOMATED RETRIES
    # =========================================================

    retry_count = db.scalar(
        select(func.count(RecoveryAction.id))
        .where(
            RecoveryAction.recovery_case_id == recovery_case.id,
            RecoveryAction.action_type == "retry_payment",
        )
    ) or 0

    # =========================================================
    # 3. ENFORCE RETRY STOPPING RULE
    # =========================================================

    if (
        decision.decision == "retry_payment"
        and retry_count >= MAX_AUTOMATED_RETRIES
    ):
        recovery_case.status = "escalated"

        audit = AuditEvent(
            recovery_case_id=recovery_case.id,
            event_type="recovery_escalated",
            message=(
                "Maximum automated payment retries reached. "
                "Further automated retries are prohibited."
            ),
        )

        db.add(audit)
        db.commit()

        return ActionExecutionResult(
            action="retry_payment",
            status="escalated",
            message="Maximum automated retries reached. Case escalated.",
            amount_recovered=Decimal("0.00"),
        )

    # =========================================================
    # 4. HARD FAILURE SAFETY CHECK
    # =========================================================

    if decision.decision == "manual_review":
        recovery_case.status = "escalated"

        action = RecoveryAction(
            recovery_case_id=recovery_case.id,
            action_type="manual_review",
            status="escalated",
            amount_recovered=Decimal("0.00"),
            executed_at=datetime.now(timezone.utc),
            result="Automated recovery prohibited. Manual intervention required.",
        )

        audit = AuditEvent(
            recovery_case_id=recovery_case.id,
            event_type="manual_review_required",
            message=(
                "Decision engine selected manual review. "
                "No automated payment action was executed."
            ),
        )

        db.add(action)
        db.add(audit)
        db.commit()

        return ActionExecutionResult(
            action="manual_review",
            status="escalated",
            message="Case escalated for manual review.",
            amount_recovered=Decimal("0.00"),
        )

    # =========================================================
    # 5. EXECUTE RETRY
    # =========================================================

    if decision.decision == "retry_payment":

        is_successful = decision.confidence and decision.confidence > Decimal("0.40")
        
        amount = transaction.amount if is_successful else Decimal("0.00")
        recovery_case.status = "recovered" if is_successful else "open"
        if is_successful:
            recovery_case.resolved_at = datetime.now(timezone.utc)
            transaction.status = "successful"
            
        action = RecoveryAction(
            recovery_case_id=recovery_case.id,
            action_type="retry_payment",
            status="executed",
            amount_recovered=amount,
            executed_at=datetime.now(timezone.utc),
            result=(
                f"Automated retry #{retry_count + 1} executed "
                f"through recovery simulation. Success: {is_successful}"
            ),
        )

        audit = AuditEvent(
            recovery_case_id=recovery_case.id,
            event_type="payment_retry",
            message=(
                f"Automated payment retry #{retry_count + 1} executed. "
                f"Stopping rule: maximum {MAX_AUTOMATED_RETRIES} retries. "
                f"Outcome: {'Recovered' if is_successful else 'Failed'}"
            ),
        )

        db.add(action)
        db.add(audit)
        db.commit()

        return ActionExecutionResult(
            action="retry_payment",
            status="executed",
            message=f"Automated payment retry #{retry_count + 1} executed.",
            amount_recovered=amount,
        )

    # =========================================================
    # 6. CUSTOMER PAYMENT RECOVERY
    # =========================================================

    if decision.decision == "send_payment_recovery_link":
        is_successful = decision.confidence and decision.confidence > Decimal("0.40")
        amount = transaction.amount if is_successful else Decimal("0.00")
        recovery_case.status = "recovered" if is_successful else "open"
        if is_successful:
            recovery_case.resolved_at = datetime.now(timezone.utc)
            transaction.status = "successful"

        action = RecoveryAction(
            recovery_case_id=recovery_case.id,
            action_type="send_payment_recovery_link",
            status="executed",
            amount_recovered=amount,
            executed_at=datetime.now(timezone.utc),
            result=f"Payment recovery link generated. Simulated Customer Payment: {'Successful' if is_successful else 'Pending'}",
        )

        audit = AuditEvent(
            recovery_case_id=recovery_case.id,
            event_type="recovery_link_sent",
            message=(
                f"Customer payment recovery link generated. "
                f"Outcome: {'Recovered by customer' if is_successful else 'Waiting on customer'}"
            ),
        )

        db.add(action)
        db.add(audit)
        db.commit()

        return ActionExecutionResult(
            action="send_payment_recovery_link",
            status="executed",
            message="Payment recovery link generated.",
            amount_recovered=amount,
        )

    # =========================================================
    # 7. PAYMENT METHOD UPDATE
    # =========================================================

    if decision.decision == "request_payment_method_update":
        is_successful = decision.confidence and decision.confidence > Decimal("0.40")
        amount = transaction.amount if is_successful else Decimal("0.00")
        recovery_case.status = "recovered" if is_successful else "open"
        if is_successful:
            recovery_case.resolved_at = datetime.now(timezone.utc)
            transaction.status = "successful"

        action = RecoveryAction(
            recovery_case_id=recovery_case.id,
            action_type="request_payment_method_update",
            status="executed",
            amount_recovered=amount,
            executed_at=datetime.now(timezone.utc),
            result=f"Customer requested to update payment method. Simulated Update & Retry: {'Successful' if is_successful else 'Pending'}",
        )

        audit = AuditEvent(
            recovery_case_id=recovery_case.id,
            event_type="payment_method_update_requested",
            message=f"Customer payment method update requested. Outcome: {'Recovered' if is_successful else 'Waiting on customer'}",
        )

        db.add(action)
        db.add(audit)
        db.commit()

        return ActionExecutionResult(
            action="request_payment_method_update",
            status="executed",
            message="Payment method update request generated.",
            amount_recovered=amount,
        )

    # =========================================================
    # 8. UNKNOWN ACTION = SAFE STOP
    # =========================================================

    recovery_case.status = "escalated"

    audit = AuditEvent(
        recovery_case_id=recovery_case.id,
        event_type="unknown_recovery_action",
        message=(
            f"Unknown recovery decision '{decision.decision}'. "
            "Automated execution blocked for safety."
        ),
    )

    db.add(audit)
    db.commit()

    return ActionExecutionResult(
        action=decision.decision,
        status="blocked",
        message="Unknown recovery action. Automated execution blocked.",
        amount_recovered=Decimal("0.00"),
    )


def _stop(
    db: Session,
    recovery_case: RecoveryCase,
    message: str,
) -> ActionExecutionResult:

    audit = AuditEvent(
        recovery_case_id=recovery_case.id,
        event_type="recovery_stopped",
        message=message,
    )

    db.add(audit)
    db.commit()

    return ActionExecutionResult(
        action="no_action",
        status="stopped",
        message=message,
        amount_recovered=Decimal("0.00"),
    )