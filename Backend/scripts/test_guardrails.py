from sqlalchemy import select

from app.db.database import SessionLocal
from app.models import RecoveryCase, Transaction
from app.services.guardrails import validate_recovery_action


def main():

    db = SessionLocal()

    try:

        transaction = db.get(Transaction, 1)

        if not transaction:
            print("Transaction 1 not found.")
            return

        recovery_case = db.scalar(
            select(RecoveryCase)
            .where(
                RecoveryCase.transaction_id == transaction.id
            )
        )

        if not recovery_case:
            print("Recovery case not found.")
            return

        result = validate_recovery_action(
            db=db,
            transaction=transaction,
            recovery_case=recovery_case,
            proposed_action="retry_payment",
        )

        print("\n==============================")
        print("RECOVER AI GUARDRAIL TEST")
        print("==============================")

        print(f"Transaction ID : {transaction.id}")
        print(f"Proposed Action: retry_payment")
        print(f"Approved       : {result.approved}")
        print(f"Final Action   : {result.action}")
        print(f"Reason         : {result.reason}")

        print("\nViolations:")

        if result.violations:
            for violation in result.violations:
                print(f"- {violation}")
        else:
            print("- None")

        print("==============================")

    finally:
        db.close()


if __name__ == "__main__":
    main()