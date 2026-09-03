from app.db.database import SessionLocal
from app.services.dashboard_service import get_dashboard_summary


def main():
    db = SessionLocal()

    try:
        result = get_dashboard_summary(db)

        print("\n========================================")
        print("       RECOVER AI - DASHBOARD")
        print("========================================")

        print(
            f"Transactions Analyzed : "
            f"{result['transactions_analyzed']}"
        )

        print(
            f"Recovery Candidates   : "
            f"{result['recovery_candidates']}"
        )

        print(
            f"Actions Executed      : "
            f"{result['actions_executed']}"
        )

        print(
            f"Recovered Cases       : "
            f"{result['recovered_cases']}"
        )

        print(
            f"Escalated Cases       : "
            f"{result['escalated_cases']}"
        )

        print(
            f"Blocked Cases         : "
            f"{result['blocked_cases']}"
        )

        print(
            f"Revenue At Risk       : "
            f"{result['revenue_at_risk']}"
        )

        print(
            f"Revenue Recovered     : "
            f"{result['revenue_recovered']}"
        )

        print(
            f"Recovery Rate         : "
            f"{result['recovery_rate']}"
        )

        print("========================================\n")

    finally:
        db.close()


if __name__ == "__main__":
    main()