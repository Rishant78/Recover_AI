from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AgentDecision,
    RecoveryCase,
    Transaction,
)

from app.services.action_executor import (
    ActionExecutionResult,
    execute_recovery_action,
)

from app.services.decision_engine import (
    make_recovery_decision,
)

from app.services.guardrails import (
    validate_recovery_action,
)

from app.services.audit_service import (
    record_audit_event,
)


@dataclass
class RecoveryWorkflowResult:
    transaction_id: int
    recovery_case_id: int
    decision: str
    action: str
    status: str
    confidence: Decimal
    amount_recovered: Decimal
    message: str


def run_recovery_workflow(
    db: Session,
    transaction_id: int,
) -> RecoveryWorkflowResult:

    # =========================================================
    # 1. Load transaction
    # =========================================================

    transaction = db.get(
        Transaction,
        transaction_id,
    )

    if not transaction:
        raise ValueError(
            f"Transaction {transaction_id} not found."
        )

    # =========================================================
    # 2. Stop if payment already succeeded
    # =========================================================

    if transaction.status == "successful":

        raise ValueError(
            "Recovery workflow cannot start because "
            "payment has already succeeded."
        )

    # =========================================================
    # 3. Find or create recovery case
    # =========================================================

    recovery_case = db.scalar(
        select(RecoveryCase)
        .where(
            RecoveryCase.transaction_id == transaction.id
        )
    )

    if not recovery_case:

        from app.services.risk_engine import calculate_risk

        risk_assessment = calculate_risk(
            db=db,
            transaction=transaction,
        )

        recovery_case = RecoveryCase(
            transaction_id=transaction.id,
            status="open",
            risk_reason=risk_assessment.reason,
            amount_at_risk=risk_assessment.amount_at_risk,
        )

        db.add(recovery_case)
        db.flush()

        # Record creation of the recovery case
        record_audit_event(
            db=db,
            recovery_case_id=recovery_case.id,
            event_type="recovery_case_created",
            message=(
                f"Recovery case created for transaction "
                f"{transaction.id}. "
                f"Risk level: {risk_assessment.risk_level}. "
                f"Risk score: {risk_assessment.risk_score}/100."
            ),
        )

        db.commit()
        db.refresh(recovery_case)

    # =========================================================
    # 4. Stop if case is already closed/escalated
    #    This is the idempotency guard — prevents a second
    #    recovery run from executing duplicate actions.
    # =========================================================

    if recovery_case.status != "open":

        raise ValueError(
            f"Recovery case is already "
            f"{recovery_case.status}."
        )

    # =========================================================
    # 5. Ask the agent for a recovery decision
    # =========================================================

    decision = make_recovery_decision(
        db=db,
        transaction=transaction,
    )

    # =========================================================
    # 6. Persist AgentDecision
    # =========================================================

    agent_decision = AgentDecision(
        recovery_case_id=recovery_case.id,
        decision=decision.decision,
        confidence=decision.confidence,
        reasoning=decision.reasoning,
    )

    db.add(agent_decision)
    db.flush()

    # =========================================================
    # 7. Record agent decision in audit trail
    # =========================================================

    record_audit_event(
        db=db,
        recovery_case_id=recovery_case.id,
        event_type="agent_decision",
        message=(
            f"Agent selected '{decision.decision}' "
            f"with confidence {decision.confidence}. "
            f"Reasoning: {decision.reasoning}"
        ),
    )

    # =========================================================
    # 8. Run guardrails BEFORE execution
    # =========================================================

    guardrail_result = validate_recovery_action(
        db=db,
        transaction=transaction,
        recovery_case=recovery_case,
        proposed_action=decision.decision,
    )

    # =========================================================
    # 9. Record guardrail result
    # =========================================================

    if guardrail_result.approved:

        record_audit_event(
            db=db,
            recovery_case_id=recovery_case.id,
            event_type="guardrail_approved",
            message=(
                f"Recovery action '{decision.decision}' "
                f"passed all guardrail checks."
            ),
        )

    else:

        record_audit_event(
            db=db,
            recovery_case_id=recovery_case.id,
            event_type="guardrail_blocked",
            message=(
                f"Recovery action '{decision.decision}' "
                f"was blocked by guardrails. "
                f"Violations: "
                f"{'; '.join(guardrail_result.violations)}"
            ),
        )

    # =========================================================
    # 10. Guardrail blocked action
    # =========================================================

    if not guardrail_result.approved:

        recovery_case.status = "escalated"

        record_audit_event(
            db=db,
            recovery_case_id=recovery_case.id,
            event_type="case_escalated",
            message=(
                "Recovery case escalated for manual intervention "
                "because the proposed recovery action failed "
                "guardrail validation."
            ),
        )

        # Single atomic commit for the entire blocked workflow
        db.commit()

        return RecoveryWorkflowResult(
            transaction_id=transaction.id,
            recovery_case_id=recovery_case.id,
            decision=decision.decision,
            action=guardrail_result.action,
            status="escalated",
            confidence=decision.confidence,
            amount_recovered=Decimal("0.00"),
            message=(
                f"Recovery action blocked by guardrails: "
                f"{'; '.join(guardrail_result.violations)}"
            ),
        )

    # =========================================================
    # 11. Execute approved action
    # =========================================================

    execution: ActionExecutionResult = (
        execute_recovery_action(
            db=db,
            recovery_case=recovery_case,
            decision=agent_decision,
        )
    )

    # =========================================================
    # 12. Record execution in audit trail
    # =========================================================

    record_audit_event(
        db=db,
        recovery_case_id=recovery_case.id,
        event_type="recovery_action_executed",
        message=(
            f"Recovery action '{execution.action}' "
            f"executed with status '{execution.status}'. "
            f"Amount recovered: "
            f"{execution.amount_recovered}."
        ),
    )

    # Single atomic commit for the entire approved workflow
    db.commit()

    # =========================================================
    # 13. Return complete workflow result
    # =========================================================

    return RecoveryWorkflowResult(
        transaction_id=transaction.id,
        recovery_case_id=recovery_case.id,
        decision=decision.decision,
        action=execution.action,
        status=execution.status,
        confidence=decision.confidence,
        amount_recovered=execution.amount_recovered,
        message=execution.message,
    )