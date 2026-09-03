from app.db.database import SessionLocal
from app.models import AgentDecision, RecoveryCase
from app.services.action_executor import execute_recovery_action


def main():
    db = SessionLocal()

    try:
        recovery_case = db.query(RecoveryCase).first()

        if not recovery_case:
            print("No recovery case found.")
            return

        decision = (
            db.query(AgentDecision)
            .filter(
                AgentDecision.recovery_case_id == recovery_case.id
            )
            .order_by(AgentDecision.created_at.desc())
            .first()
        )

        if not decision:
            print("No agent decision found.")
            return

        print("\n==============================")
        print("RECOVER AI ACTION EXECUTOR")
        print("==============================")

        print(f"Recovery Case : {recovery_case.id}")
        print(f"Transaction   : {recovery_case.transaction_id}")
        print(f"Decision      : {decision.decision}")

        result = execute_recovery_action(
            db=db,
            recovery_case=recovery_case,
            decision=decision,
        )

        print("\n--- EXECUTION RESULT ---")
        print(f"Action        : {result.action}")
        print(f"Status        : {result.status}")
        print(f"Message       : {result.message}")
        print(f"Recovered     : {result.amount_recovered}")

        print("==============================\n")

    finally:
        db.close()


if __name__ == "__main__":
    main()