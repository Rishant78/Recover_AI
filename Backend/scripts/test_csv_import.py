import os
import io
import csv
from decimal import Decimal
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import SessionLocal
from app.models import Transaction, RecoveryCase

client = TestClient(app)

def test_csv_import():
    print("\n========================================")
    print("       RECOVER AI - CSV IMPORT TEST")
    print("========================================")

    # 1. Test invalid file type
    print("Testing invalid file type...")
    res = client.post("/api/v1/recovery/import", files={"file": ("test.txt", b"dummy", "text/plain")})
    assert res.status_code == 400
    assert "CSV files" in res.json()["detail"]
    print("  -> Passed")

    # 2. Test missing columns
    print("Testing missing columns...")
    csv_data = "transaction_id,amount\ntxn_1,10.00\n"
    res = client.post("/api/v1/recovery/import", files={"file": ("test.csv", csv_data.encode("utf-8"), "text/csv")})
    assert res.status_code == 400
    assert "Missing required column" in res.json()["detail"]
    print("  -> Passed")

    import uuid
    run_id = uuid.uuid4().hex[:6]
    
    # 3. Test successful import
    print("Testing successful import...")
    csv_data = f"""transaction_id,customer_name,customer_email,amount,currency,status,payment_method,failure_code,failure_reason,timestamp
txn_test_{run_id}_1,Jane Doe,jane.doe_{run_id}@example.com,150.50,USD,failed,credit_card,insufficient_funds,The card has insufficient funds,2026-09-01T10:00:00Z
txn_test_{run_id}_2,John Smith,john.smith_{run_id}@example.com,99.99,USD,abandoned,,,2026-09-01T11:00:00Z
txn_test_{run_id}_3,Alice Kim,alice.kim_{run_id}@example.com,42.00,USD,successful,wallet,,,2026-09-01T12:00:00Z
"""
    res = client.post("/api/v1/recovery/import", files={"file": ("test.csv", csv_data.encode("utf-8"), "text/csv")})
    assert res.status_code == 200
    data = res.json()
    assert data["received"] == 3
    assert data["imported"] == 3
    assert data["rejected"] == 0
    print("  -> Passed")

    # 4. Check DB
    print("Verifying database state...")
    db = SessionLocal()
    txn = db.query(Transaction).filter(Transaction.external_id == f"txn_test_{run_id}_1").first()
    assert txn is not None
    assert txn.amount == Decimal("150.50")
    
    rc = db.query(RecoveryCase).filter(RecoveryCase.transaction_id == txn.id).first()
    assert rc is not None
    assert rc.status == "open"
    db.close()
    print("  -> Passed")

    # 5. Test duplicates
    print("Testing duplicate transaction handling...")
    csv_data = f"""transaction_id,customer_name,customer_email,amount,currency,status,payment_method,failure_code,failure_reason,timestamp
txn_test_{run_id}_1,Jane Doe,jane.doe_{run_id}@example.com,150.50,USD,failed,credit_card,insufficient_funds,The card has insufficient funds,2026-09-01T10:00:00Z
txn_test_{run_id}_4,New User,new_{run_id}@example.com,10.00,USD,failed,credit_card,card_declined,Declined,2026-09-01T10:00:00Z
"""
    res = client.post("/api/v1/recovery/import", files={"file": ("test.csv", csv_data.encode("utf-8"), "text/csv")})
    assert res.status_code == 200
    data = res.json()
    assert data["received"] == 2
    assert data["imported"] == 1
    assert data["rejected"] == 1
    assert "already exists" in data["errors"][0]
    print("  -> Passed")

    print("========================================\n")

if __name__ == "__main__":
    test_csv_import()
