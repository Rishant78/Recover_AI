from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.financial import (
    AgentDecision,
    AuditEvent,
    RecoveryAction,
)


def record_decision(
    db: Session,
    recovery_case_id: int,
    decision: str,
    reasoning: str,
    confidence: Decimal | None = None,
) -> AgentDecision:

    agent_decision = AgentDecision(
        recovery_case_id=recovery_case_id,
        decision=decision,
        confidence=confidence,
        reasoning=reasoning,
    )

    db.add(agent_decision)

    return agent_decision


def record_action(
    db: Session,
    recovery_case_id: int,
    action_type: str,
    status: str,
    amount_recovered: Decimal = Decimal("0.00"),
    result: str | None = None,
) -> RecoveryAction:

    action = RecoveryAction(
        recovery_case_id=recovery_case_id,
        action_type=action_type,
        status=status,
        amount_recovered=amount_recovered,
        result=result,
    )

    db.add(action)

    return action


def record_audit_event(
    db: Session,
    recovery_case_id: int,
    event_type: str,
    message: str,
) -> AuditEvent:

    event = AuditEvent(
        recovery_case_id=recovery_case_id,
        event_type=event_type,
        message=message,
    )

    db.add(event)

    return event