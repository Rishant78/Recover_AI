from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Transaction
from app.services.policy_retriever import retrieve_policies
from app.services.risk_engine import RiskAssessment, calculate_risk


@dataclass
class RecoveryDecision:
    transaction_id: int
    decision: str
    confidence: Decimal
    reasoning: str
    policy_references: list[str]
    stopping_rule: str


def make_recovery_decision(
    db: Session,
    transaction: Transaction,
) -> RecoveryDecision:

    # ---------------------------------------------------------
    # 1. Calculate transaction risk
    # ---------------------------------------------------------

    assessment: RiskAssessment = calculate_risk(
        db=db,
        transaction=transaction,
    )

    # ---------------------------------------------------------
    # 2. Retrieve relevant recovery policies
    # ---------------------------------------------------------

    policy_query = (
        f"transaction status {transaction.status} "
        f"risk level {assessment.risk_level} "
        f"recommended action {assessment.recommended_action} "
        f"{assessment.reason}"
    )

    policies = retrieve_policies(
        query=policy_query,
        top_k=3,
    )

    # ---------------------------------------------------------
    # 3. Extract policy references
    # ---------------------------------------------------------

    policy_references = [
        policy["title"]
        for policy in policies
    ]

    # ---------------------------------------------------------
    # 4. Start with the risk engine recommendation
    #
    # The risk engine determines the candidate action.
    # Policies act as the governance layer.
    # ---------------------------------------------------------

    decision = assessment.recommended_action

    # ---------------------------------------------------------
    # 5. Apply policy-based safety constraints
    # ---------------------------------------------------------

    policy_text = " ".join(
        policy.get("content", "")
        for policy in policies
    ).lower()

    # Hard failures should never be automatically retried.
    if "do not automatically retry" in policy_text:
        if decision == "retry_payment":
            decision = "manual_review"

    # Recovery workflows must always have a stopping rule.
    if not assessment.stopping_rule:
        decision = "manual_review"

    # ---------------------------------------------------------
    # 6. Calculate confidence
    #
    # This is deterministic for now.
    # Later an LLM can provide structured confidence,
    # but the policy layer will remain the guardrail.
    # ---------------------------------------------------------

    confidence = Decimal(
        str(round(assessment.risk_score / 100, 4))
    )

    if not policies:
        confidence = min(
            confidence,
            Decimal("0.5000"),
        )

    # ---------------------------------------------------------
    # 7. Build explainable reasoning
    # ---------------------------------------------------------

    reasoning_parts = [
        f"Risk assessment: {assessment.reason}",
        f"Risk score: {assessment.risk_score}/100.",
        f"Risk level: {assessment.risk_level}.",
        f"Selected recovery action: {decision}.",
    ]

    if policy_references:
        reasoning_parts.append(
            "Decision grounded in recovery policies: "
            + ", ".join(policy_references)
            + "."
        )
    else:
        reasoning_parts.append(
            "No matching recovery policy was retrieved; "
            "automatic recovery confidence was reduced."
        )

    reasoning_parts.append(
        f"Stopping rule: {assessment.stopping_rule}"
    )

    reasoning = " ".join(reasoning_parts)

    # ---------------------------------------------------------
    # 8. Return structured agent decision
    # ---------------------------------------------------------

    return RecoveryDecision(
        transaction_id=transaction.id,
        decision=decision,
        confidence=confidence,
        reasoning=reasoning,
        policy_references=policy_references,
        stopping_rule=assessment.stopping_rule,
    )