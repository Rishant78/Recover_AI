from app.db.database import SessionLocal
from app.services.batch_recovery import run_batch_recovery


def main():
    db = SessionLocal()

    try:
        result = run_batch_recovery(
            db=db,
            limit=500,
        )

        print("\n==========================================")
        print("        RECOVER AI - BATCH RECOVERY")
        print("==========================================")

        print(f"Transactions Analyzed : {result.transactions_analyzed}")
        print(f"Recovery Candidates   : {result.recovery_candidates}")
        print(f"Actions Executed      : {result.actions_executed}")
        print(f"Recovered Cases       : {result.recovered_cases}")
        print(f"Escalated Cases       : {result.escalated_cases}")
        print(f"Blocked Cases         : {result.blocked_cases}")
        print(f"Revenue At Risk       : {result.revenue_at_risk}")
        print(f"Revenue Recovered     : {result.revenue_recovered}")
        print(f"Recovery Rate         : {result.recovery_rate}")

        print("==========================================\n")

    finally:
        db.close()


if __name__ == "__main__":
    main()