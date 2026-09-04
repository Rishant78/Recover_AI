from app.db.database import SessionLocal
from app.services.recovery_orchestrator import (
    run_recovery_workflow,
)


def main():

    db = SessionLocal()

    try:

        transaction_id = 1

        result = run_recovery_workflow(
            db=db,
            transaction_id=transaction_id,
        )

        print("\n")
        print("==============================================")
        print("       RECOVER AI — RECOVERY WORKFLOW")
        print("==============================================")

        print(f"Transaction ID  : {result.transaction_id}")
        print(f"Recovery Case   : {result.recovery_case_id}")
        print(f"Agent Decision  : {result.decision}")
        print(f"Action          : {result.action}")
        print(f"Status          : {result.status}")
        print(f"Confidence      : {result.confidence}")
        print(f"Recovered       : ${result.amount_recovered}")

        print("\nMessage:")
        print(result.message)

        print("==============================================")
        print()

    finally:
        db.close()


if __name__ == "__main__":
    main()