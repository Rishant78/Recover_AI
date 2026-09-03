from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.services.audit_service import (
    record_action,
    record_audit_event,
    record_decision,
)

from app.models import PaymentAttempt, RecoveryCase, Transaction
from app.services.recovery_simulator import (
    RecoveryResult,
    simulate_recovery,
)
from app.services.risk_engine import calculate_risk


@dataclass
class BatchRecoveryResult:
    transactions_analyzed: int
    recovery_candidates: int
    actions_executed: int
    recovered_cases: int
    escalated_cases: int
    blocked_cases: int
    revenue_at_risk: Decimal
    revenue_recovered: Decimal
    recovery_rate: float
    results: list[RecoveryResult] = field(default_factory=list)


def run_batch_recovery(
    db: Session,
    limit: int = 500,
) -> BatchRecoveryResult:

    # ---------------------------------------------------------
    # 1. Load transactions with eager-loaded relationships
    #    to avoid N+1 queries inside the loop.
    # ---------------------------------------------------------

    transactions = db.scalars(
        select(Transaction)
        .options(
            joinedload(Transaction.payment_attempts),
            joinedload(Transaction.recovery_case),
        )
        .order_by(Transaction.id)
        .limit(limit)
    ).unique().all()

    results = []

    revenue_at_risk = Decimal("0.00")
    revenue_recovered = Decimal("0.00")

    recovery_candidates = 0
    actions_executed = 0
    recovered_cases = 0
    escalated_cases = 0
    blocked_cases = 0

    for transaction in transactions:

        assessment = calculate_risk(
            db=db,
            transaction=transaction,
        )

        # Already-successful transactions are not recovery candidates.
        if assessment.risk_level == "none":
            continue

        recovery_candidates += 1

        revenue_at_risk += assessment.amount_at_risk

        # ---------------------------------------------------------
        # Null safety: skip if no recovery case exists.
        # This can happen if seed data is inconsistent.
        # ---------------------------------------------------------

        recovery_case = transaction.recovery_case

        if not recovery_case:
            continue

        # ---------------------------------------------------------
        # Idempotency: skip if the case has already been processed.
        # Prevents duplicate execution on re-run.
        # ---------------------------------------------------------

        if recovery_case.status != "open":
            continue

        # ---------------------------------------------------------
        # Use the latest payment attempt (already loaded)
        # ---------------------------------------------------------

        payment_attempt = None
        if transaction.payment_attempts:
            payment_attempt = max(
                transaction.payment_attempts,
                key=lambda pa: pa.attempted_at,
            )

        # ---------------------------------------------------------
        # Audit: risk assessment
        # ---------------------------------------------------------

        record_audit_event(
            db=db,
            recovery_case_id=recovery_case.id,
            event_type="RISK_ASSESSED",
            message=(
                f"Transaction assessed as {assessment.risk_level} risk. "
                f"Amount at risk: {assessment.amount_at_risk}. "
                f"Reason: {assessment.reason}"
            ),
        )

        result = simulate_recovery(
            transaction=transaction,
            payment_attempt=payment_attempt,
            action=assessment.recommended_action,
        )

        # ---------------------------------------------------------
        # Record decision
        # ---------------------------------------------------------

        record_decision(
            db=db,
            recovery_case_id=recovery_case.id,
            decision=assessment.recommended_action,
            confidence=Decimal(str(assessment.risk_score / 100)),
            reasoning=assessment.reason,
        )

        # ---------------------------------------------------------
        # Record action
        # ---------------------------------------------------------

        record_action(
            db=db,
            recovery_case_id=recovery_case.id,
            action_type=assessment.recommended_action,
            status=result.status,
            amount_recovered=result.recovered_amount,
            result=result.explanation,
        )

        # ---------------------------------------------------------
        # Audit: action executed
        # ---------------------------------------------------------

        record_audit_event(
            db=db,
            recovery_case_id=recovery_case.id,
            event_type="ACTION_EXECUTED",
            message=(
                f"Action '{assessment.recommended_action}' executed. "
                f"Status: {result.status}. "
                f"Recovered: {result.recovered_amount}."
            ),
        )

        # ---------------------------------------------------------
        # Audit: recovery outcome + update case status
        # ---------------------------------------------------------

        if result.status == "recovered":

            recovery_case.status = "recovered"

            record_audit_event(
                db=db,
                recovery_case_id=recovery_case.id,
                event_type="RECOVERY_COMPLETED",
                message=(
                    f"Recovery successful. "
                    f"Amount recovered: {result.recovered_amount}."
                ),
            )

        elif result.status == "escalated":

            recovery_case.status = "escalated"

            record_audit_event(
                db=db,
                recovery_case_id=recovery_case.id,
                event_type="ESCALATED",
                message=result.explanation,
            )

        else:

            record_audit_event(
                db=db,
                recovery_case_id=recovery_case.id,
                event_type="RECOVERY_FAILED",
                message=result.explanation,
            )

        # ---------------------------------------------------------
        # Commit all records for this transaction atomically.
        # Each iteration is one atomic unit of work.
        # ---------------------------------------------------------

        db.commit()

        results.append(result)

        actions_executed += 1

        revenue_recovered += result.recovered_amount

        if result.status == "recovered":
            recovered_cases += 1

        elif result.status == "escalated":
            escalated_cases += 1

        elif result.status == "blocked":
            blocked_cases += 1

    if revenue_at_risk > 0:
        recovery_rate = float(
            revenue_recovered / revenue_at_risk
        )
    else:
        recovery_rate = 0.0

    return BatchRecoveryResult(
        transactions_analyzed=len(transactions),
        recovery_candidates=recovery_candidates,
        actions_executed=actions_executed,
        recovered_cases=recovered_cases,
        escalated_cases=escalated_cases,
        blocked_cases=blocked_cases,
        revenue_at_risk=revenue_at_risk,
        revenue_recovered=revenue_recovered,
        recovery_rate=recovery_rate,
        results=results,
    )