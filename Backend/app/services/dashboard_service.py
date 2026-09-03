from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import (
    RecoveryAction,
    RecoveryCase,
    Transaction,
)


def get_dashboard_summary(db: Session) -> dict:
    """
    Build high-level recovery metrics for the dashboard.

    Uses aggregated queries to minimize DB round-trips.
    """

    # ---------------------------------------------------------
    # 1. Total transactions
    # ---------------------------------------------------------

    total_transactions = db.scalar(
        select(func.count(Transaction.id))
    ) or 0

    # ---------------------------------------------------------
    # 2. Recovery case metrics in a single aggregated query
    #    instead of 4 separate COUNT queries.
    # ---------------------------------------------------------

    case_stats = db.execute(
        select(
            func.count(RecoveryCase.id).label("total"),
            func.count(
                case(
                    (RecoveryCase.status == "open", RecoveryCase.id),
                )
            ).label("open_count"),
            func.count(
                case(
                    (RecoveryCase.status == "recovered", RecoveryCase.id),
                )
            ).label("recovered_count"),
            func.count(
                case(
                    (RecoveryCase.status == "escalated", RecoveryCase.id),
                )
            ).label("escalated_count"),
            func.count(
                case(
                    (RecoveryCase.status == "blocked", RecoveryCase.id),
                )
            ).label("blocked_count"),
            func.coalesce(
                func.sum(RecoveryCase.amount_at_risk), 0
            ).label("total_at_risk"),
        )
    ).one()

    recovery_candidates = case_stats.total
    open_cases = case_stats.open_count
    recovered_cases = case_stats.recovered_count
    escalated_cases = case_stats.escalated_count
    blocked_cases = case_stats.blocked_count
    revenue_at_risk = Decimal(str(case_stats.total_at_risk))

    # ---------------------------------------------------------
    # 3. Recovery actions + revenue recovered
    # ---------------------------------------------------------

    action_stats = db.execute(
        select(
            func.count(RecoveryAction.id).label("action_count"),
            func.coalesce(
                func.sum(RecoveryAction.amount_recovered), 0
            ).label("total_recovered"),
        )
        .where(
            RecoveryAction.status.in_(
                ["executed", "recovered", "escalated"]
            )
        )
    ).one()

    actions_executed = action_stats.action_count
    revenue_recovered = Decimal(str(action_stats.total_recovered))

    # ---------------------------------------------------------
    # 4. Recovery rate
    # ---------------------------------------------------------

    if revenue_at_risk > 0:
        recovery_rate = (
            revenue_recovered / revenue_at_risk
        )
    else:
        recovery_rate = Decimal("0.00")

    return {
        "transactions_analyzed": total_transactions,
        "recovery_candidates": recovery_candidates,
        "open_cases": open_cases,
        "actions_executed": actions_executed,
        "recovered_cases": recovered_cases,
        "escalated_cases": escalated_cases,
        "blocked_cases": blocked_cases,
        "revenue_at_risk": revenue_at_risk,
        "revenue_recovered": revenue_recovered,
        "recovery_rate": recovery_rate,
    }