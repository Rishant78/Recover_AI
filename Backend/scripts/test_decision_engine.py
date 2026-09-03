from app.db.database import SessionLocal
from app.models import AgentDecision, Transaction
from app.services.decision_engine import make_recovery_decision


def main():
    db = SessionLocal()

    try:
        transaction = db.query(Transaction).first()

        if not transaction:
            print("No transactions found.")
            return

        decision = make_recovery_decision(
            db=db,
            transaction=transaction,
        )

        # Find the recovery case created for this transaction
        recovery_case = transaction.recovery_case

        if not recovery_case:
            print("No recovery case found for this transaction.")
            return

        # Persist the agent decision
        agent_decision = AgentDecision(
            recovery_case_id=recovery_case.id,
            decision=decision.decision,
            confidence=decision.confidence,
            reasoning=decision.reasoning,
        )

        db.add(agent_decision)
        db.commit()
        db.refresh(agent_decision)

        print("\n========== RECOVER AI DECISION ==========")

        print(f"Transaction ID : {decision.transaction_id}")
        print(f"Recovery Case  : {recovery_case.id}")
        print(f"Decision       : {decision.decision}")
        print(f"Confidence     : {decision.confidence}")
        print(f"Policies       : {decision.policy_references}")
        print(f"Stopping Rule  : {decision.stopping_rule}")
        print(f"Decision ID    : {agent_decision.id}")

        print("\nReasoning:")
        print(decision.reasoning)

        print("=========================================\n")

    finally:
        db.close()


if __name__ == "__main__":
    main()