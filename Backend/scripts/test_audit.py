from app.db.database import SessionLocal
from app.models import (
    AgentDecision,
    AuditEvent,
    RecoveryAction,
    RecoveryCase,
)


def main():
    db = SessionLocal()

    try:
        # Inspect the recovery case created for Transaction 1
        recovery_case = (
            db.query(RecoveryCase)
            .filter(RecoveryCase.transaction_id == 1)
            .first()
        )

        if not recovery_case:
            print("No recovery case found for Transaction 1.")
            return

        print("\n========== RECOVER AI AUDIT TRAIL ==========")

        print(f"Recovery Case ID : {recovery_case.id}")
        print(f"Transaction ID   : {recovery_case.transaction_id}")
        print(f"Case Status      : {recovery_case.status}")

        # -------------------------------------------------
        # Agent Decisions
        # -------------------------------------------------

        decisions = (
            db.query(AgentDecision)
            .filter(
                AgentDecision.recovery_case_id == recovery_case.id
            )
            .order_by(AgentDecision.created_at.asc())
            .all()
        )

        print("\n--- Agent Decisions ---")

        if not decisions:
            print("No agent decisions found.")
        else:
            for decision in decisions:
                print(f"Decision ID : {decision.id}")
                print(f"Decision    : {decision.decision}")
                print(f"Confidence  : {decision.confidence}")
                print(f"Reasoning   : {decision.reasoning}")
                print(f"Created At  : {decision.created_at}")
                print("-" * 40)

        # -------------------------------------------------
        # Recovery Actions
        # -------------------------------------------------

        actions = (
            db.query(RecoveryAction)
            .filter(
                RecoveryAction.recovery_case_id == recovery_case.id
            )
            .order_by(RecoveryAction.id.asc())
            .all()
        )

        print("\n--- Recovery Actions ---")

        if not actions:
            print("No recovery actions found.")
        else:
            for action in actions:
                print(f"Action ID       : {action.id}")
                print(f"Action Type     : {action.action_type}")
                print(f"Status          : {action.status}")
                print(f"Amount Recovered: {action.amount_recovered}")
                print(f"Result          : {action.result}")
                print(f"Executed At     : {action.executed_at}")
                print("-" * 40)

        # -------------------------------------------------
        # Audit Events
        # -------------------------------------------------

        events = (
            db.query(AuditEvent)
            .filter(
                AuditEvent.recovery_case_id == recovery_case.id
            )
            .order_by(AuditEvent.created_at.asc())
            .all()
        )

        print("\n--- Audit Events ---")

        if not events:
            print("No audit events found.")
        else:
            for event in events:
                print(f"Event ID   : {event.id}")
                print(f"Event Type : {event.event_type}")
                print(f"Message    : {event.message}")
                print(f"Created At : {event.created_at}")
                print("-" * 40)

        print("=============================================\n")

    finally:
        db.close()


if __name__ == "__main__":
    main()