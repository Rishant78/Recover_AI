import random
from dataclasses import dataclass
from decimal import Decimal

from app.models import PaymentAttempt, Transaction


@dataclass
class RecoveryResult:
    transaction_id: int
    action: str
    status: str
    recovered_amount: Decimal
    explanation: str


def simulate_recovery(
    transaction: Transaction,
    payment_attempt: PaymentAttempt | None,
    action: str,
) -> RecoveryResult:

    amount = transaction.amount

    # ---------------------------------------------------------
    # Payment retry
    # ---------------------------------------------------------

    if action == "retry_payment":

        if not payment_attempt:
            return RecoveryResult(
                transaction_id=transaction.id,
                action=action,
                status="failed",
                recovered_amount=Decimal("0.00"),
                explanation="No payment attempt information available.",
            )

        success_probability = {
            "TIMEOUT": 0.80,
            "NETWORK_ERROR": 0.75,
            "PROCESSOR_UNAVAILABLE": 0.70,
            "INSUFFICIENT_FUNDS": 0.45,
            "CARD_EXPIRED": 0.15,
            "DO_NOT_HONOR": 0.05,
            "FRAUD_SUSPECTED": 0.01,
        }.get(
            payment_attempt.failure_code,
            0.20,
        )

        recovered = random.random() < success_probability

        if recovered:
            return RecoveryResult(
                transaction_id=transaction.id,
                action=action,
                status="recovered",
                recovered_amount=amount,
                explanation=(
                    f"Payment retry succeeded with simulated "
                    f"probability {success_probability:.0%}."
                ),
            )

        return RecoveryResult(
            transaction_id=transaction.id,
            action=action,
            status="failed",
            recovered_amount=Decimal("0.00"),
            explanation=(
                f"Payment retry failed with simulated "
                f"probability {success_probability:.0%}."
            ),
        )

    # ---------------------------------------------------------
    # Customer recovery link
    # ---------------------------------------------------------

    if action == "send_payment_recovery_link":

        success_probability = 0.60

        if random.random() < success_probability:
            return RecoveryResult(
                transaction_id=transaction.id,
                action=action,
                status="recovered",
                recovered_amount=amount,
                explanation=(
                    "Customer completed payment through the recovery link."
                ),
            )

        return RecoveryResult(
            transaction_id=transaction.id,
            action=action,
            status="failed",
            recovered_amount=Decimal("0.00"),
            explanation=(
                "Customer did not complete payment through the recovery link."
            ),
        )

    # ---------------------------------------------------------
    # Checkout abandonment
    # ---------------------------------------------------------

    if action == "send_checkout_reminder":

        success_probability = 0.45

        if random.random() < success_probability:
            return RecoveryResult(
                transaction_id=transaction.id,
                action=action,
                status="recovered",
                recovered_amount=amount,
                explanation=(
                    "Customer returned and completed the abandoned checkout."
                ),
            )

        return RecoveryResult(
            transaction_id=transaction.id,
            action=action,
            status="failed",
            recovered_amount=Decimal("0.00"),
            explanation=(
                "Customer did not return after the checkout reminder."
            ),
        )

    # ---------------------------------------------------------
    # Invoice reminder
    # ---------------------------------------------------------

    if action == "send_invoice_reminder":

        success_probability = 0.50

        if random.random() < success_probability:
            return RecoveryResult(
                transaction_id=transaction.id,
                action=action,
                status="recovered",
                recovered_amount=amount,
                explanation=(
                    "Invoice was paid after the recovery reminder."
                ),
            )

        return RecoveryResult(
            transaction_id=transaction.id,
            action=action,
            status="failed",
            recovered_amount=Decimal("0.00"),
            explanation=(
                "Invoice remained unpaid after the reminder."
            ),
        )

    # ---------------------------------------------------------
    # Payment method update
    # ---------------------------------------------------------

    if action == "request_payment_method_update":

        success_probability = 0.55

        if random.random() < success_probability:
            return RecoveryResult(
                transaction_id=transaction.id,
                action=action,
                status="recovered",
                recovered_amount=amount,
                explanation=(
                    "Customer updated the payment method and completed payment."
                ),
            )

        return RecoveryResult(
            transaction_id=transaction.id,
            action=action,
            status="failed",
            recovered_amount=Decimal("0.00"),
            explanation=(
                "Customer did not update the payment method."
            ),
        )

    # ---------------------------------------------------------
    # Manual review
    # ---------------------------------------------------------

    if action == "manual_review":

        return RecoveryResult(
            transaction_id=transaction.id,
            action=action,
            status="escalated",
            recovered_amount=Decimal("0.00"),
            explanation=(
                "Automatically blocked. Case requires manual review."
            ),
        )

    # ---------------------------------------------------------
    # Unknown action
    # ---------------------------------------------------------

    return RecoveryResult(
        transaction_id=transaction.id,
        action=action,
        status="blocked",
        recovered_amount=Decimal("0.00"),
        explanation=(
            f"Unknown recovery action '{action}'."
        ),
    )