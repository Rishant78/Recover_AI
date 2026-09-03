import random
from decimal import Decimal

from sqlalchemy import select

from app.db.database import SessionLocal, engine, Base
from app.models import (
    Customer,
    PaymentAttempt,
    RecoveryCase,
    Transaction,
)


CUSTOMER_NAMES = [
    "Aarav Sharma",
    "Vivaan Patel",
    "Aditya Kumar",
    "Arjun Mehta",
    "Rohan Gupta",
    "Kabir Singh",
    "Ishaan Verma",
    "Ananya Sharma",
    "Diya Patel",
    "Aanya Kapoor",
    "Meera Shah",
    "Sara Khan",
    "Kiara Malhotra",
    "Ira Gupta",
    "Anika Reddy",
]

PAYMENT_METHODS = [
    "upi",
    "credit_card",
    "debit_card",
    "net_banking",
]

FAILURE_SCENARIOS = [
    {
        "code": "TIMEOUT",
        "reason": "Payment processor timed out",
        "category": "transient",
    },
    {
        "code": "NETWORK_ERROR",
        "reason": "Temporary network communication failure",
        "category": "transient",
    },
    {
        "code": "PROCESSOR_UNAVAILABLE",
        "reason": "Payment processor temporarily unavailable",
        "category": "transient",
    },
    {
        "code": "INSUFFICIENT_FUNDS",
        "reason": "Customer account has insufficient funds",
        "category": "recoverable",
    },
    {
        "code": "CARD_EXPIRED",
        "reason": "Customer card has expired",
        "category": "recoverable",
    },
    {
        "code": "DO_NOT_HONOR",
        "reason": "Issuer declined the transaction",
        "category": "hard_failure",
    },
    {
        "code": "FRAUD_SUSPECTED",
        "reason": "Transaction flagged by fraud controls",
        "category": "hard_failure",
    },
]


def generate_customer(index: int) -> Customer:
    name = random.choice(CUSTOMER_NAMES)

    # Make the email unique even when names repeat.
    safe_name = name.lower().replace(" ", ".")

    return Customer(
        external_id=f"CUST-{index:05d}",
        name=name,
        email=f"{safe_name}.{index}@example.com",
    )


def generate_transaction(
    customer: Customer,
    index: int,
) -> Transaction:
    event_type = random.choices(
        [
            "successful",
            "payment_failed",
            "checkout_abandoned",
            "subscription_failed",
            "invoice_overdue",
        ],
        weights=[45, 25, 10, 10, 10],
        k=1,
    )[0]

    amount = Decimal(
        str(random.randint(500, 100000))
    ).quantize(Decimal("0.01"))

    status_map = {
        "successful": "successful",
        "payment_failed": "failed",
        "checkout_abandoned": "abandoned",
        "subscription_failed": "failed",
        "invoice_overdue": "overdue",
    }

    return Transaction(
        external_id=f"TXN-{index:06d}",
        customer_id=customer.id,
        amount=amount,
        currency="INR",
        status=status_map[event_type],
    )


def create_payment_attempt(
    transaction: Transaction,
) -> PaymentAttempt:
    scenario = random.choice(FAILURE_SCENARIOS)

    return PaymentAttempt(
        transaction_id=transaction.id,
        payment_method=random.choice(PAYMENT_METHODS),
        status="failed",
        failure_code=scenario["code"],
        failure_reason=scenario["reason"],
    )


def create_recovery_case(
    transaction: Transaction,
) -> RecoveryCase:
    reasons = {
        "failed": "Payment failure detected",
        "abandoned": "Checkout was abandoned before payment completion",
        "overdue": "Invoice payment is overdue",
    }

    return RecoveryCase(
        transaction_id=transaction.id,
        status="open",
        risk_reason=reasons[transaction.status],
        amount_at_risk=transaction.amount,
    )


import os
import csv
from datetime import datetime

def seed_database(number_of_transactions: int = 500):
    print("Initializing database schema...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()

    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "realistic_transactions.csv")
    
    try:
        if os.path.exists(csv_path):
            print(f"Found realistic dataset at {csv_path}. Importing...")
            
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
            customers_map = {}
            recovery_count = 0
            failed_payment_count = 0
            
            for row in rows:
                email = row['customer_email']
                if email not in customers_map:
                    customer = Customer(
                        external_id=f"CUST-{len(customers_map)+1:05d}",
                        name=row['customer_name'],
                        email=email,
                    )
                    db.add(customer)
                    db.flush()
                    customers_map[email] = customer
                
                customer = customers_map[email]
                
                transaction = Transaction(
                    external_id=row['transaction_id'],
                    customer_id=customer.id,
                    amount=Decimal(row['amount']),
                    currency=row['currency'],
                    status=row['status'],
                    created_at=datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00'))
                )
                db.add(transaction)
                db.flush()
                
                if transaction.status == "failed":
                    payment_attempt = PaymentAttempt(
                        transaction_id=transaction.id,
                        payment_method=row['payment_method'],
                        status="failed",
                        failure_code=row['failure_code'],
                        failure_reason=row['failure_reason'],
                        attempted_at=transaction.created_at
                    )
                    db.add(payment_attempt)
                    
                    recovery_case = RecoveryCase(
                        transaction_id=transaction.id,
                        status="open",
                        risk_reason="Payment failure detected",
                        amount_at_risk=transaction.amount,
                    )
                    db.add(recovery_case)
                    failed_payment_count += 1
                    recovery_count += 1
            
            db.commit()
            print()
            print("========================================")
            print("RecoverAI realistic dataset imported")
            print("========================================")
            print(f"Customers:          {len(customers_map)}")
            print(f"Transactions:       {len(rows)}")
            print(f"Payment failures:   {failed_payment_count}")
            print(f"Recovery cases:     {recovery_count}")
            print("========================================")
            
        else:
            print(f"Generating {number_of_transactions} synthetic transactions...")

            customers = []

            for index in range(1, 101):
                customer = generate_customer(index)
                db.add(customer)
                customers.append(customer)

            db.flush()

            recovery_count = 0
            failed_payment_count = 0

            for index in range(1, number_of_transactions + 1):
                customer = random.choice(customers)

                transaction = generate_transaction(
                    customer,
                    index,
                )

                db.add(transaction)
                db.flush()

                if transaction.status == "failed":
                    payment_attempt = create_payment_attempt(
                        transaction
                    )

                    db.add(payment_attempt)

                    recovery_case = create_recovery_case(
                        transaction
                    )

                    db.add(recovery_case)

                    failed_payment_count += 1
                    recovery_count += 1

                elif transaction.status in {
                    "abandoned",
                    "overdue",
                }:
                    recovery_case = create_recovery_case(
                        transaction
                    )

                    db.add(recovery_case)

                    recovery_count += 1

            db.commit()

            print()
            print("========================================")
            print("RecoverAI synthetic dataset created")
            print("========================================")
            print(f"Customers:          {len(customers)}")
            print(f"Transactions:       {number_of_transactions}")
            print(f"Payment failures:   {failed_payment_count}")
            print(f"Recovery cases:     {recovery_count}")
            print("========================================")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()