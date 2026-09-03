from app.db.database import SessionLocal
from app.models import RecoveryCase, AuditEvent


def main():
    db = SessionLocal()

    try:
        recovery_case = (
            db.query(RecoveryCase)
            .order_by(RecoveryCase.id.desc())
            .first()
        )

        if not recovery_case:
            print("No recovery case found.")
            return

        events = (
            db.query(AuditEvent)
            .filter(
                AuditEvent.recovery_case_id == recovery_case.id
            )
            .order_by(AuditEvent.created_at.asc())
            .all()
        )

        print("\n========== RECOVER AI AUDIT TRAIL ==========")
        print(f"Recovery Case ID : {recovery_case.id}")
        print(f"Transaction ID   : {recovery_case.transaction_id}")
        print()

        if not events:
            print("No audit events found.")
            return

        for event in events:
            print(
                f"[{event.event_type}] "
                f"{event.message}"
            )

        print("=============================================\n")

    finally:
        db.close()


if __name__ == "__main__":
    main()