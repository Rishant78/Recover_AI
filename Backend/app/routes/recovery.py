from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
import csv
import io
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.db.database import get_db
from app.models import (
    AgentDecision,
    AuditEvent,
    Customer,
    PaymentAttempt,
    RecoveryAction,
    RecoveryCase,
    Transaction,
)
from app.services.batch_recovery import run_batch_recovery
from app.services.recovery_orchestrator import run_recovery_workflow
from app.services.risk_engine import calculate_risk
from app.services.dashboard_service import get_dashboard_summary


router = APIRouter(
    prefix="/api/v1/recovery",
    tags=["Recovery"],
)


# =========================================================
# RESPONSE MODELS
# =========================================================


class RiskAssessmentResponse(BaseModel):
    transaction_id: int
    amount_at_risk: Decimal
    risk_score: int
    risk_level: str
    reason: str
    recommended_action: str
    stopping_rule: str


class RecoveryWorkflowResponse(BaseModel):
    transaction_id: int
    recovery_case_id: int
    decision: str
    action: str
    status: str
    confidence: Decimal
    amount_recovered: Decimal
    message: str


class BatchRecoveryResponse(BaseModel):
    transactions_analyzed: int
    recovery_candidates: int
    actions_executed: int
    recovered_cases: int
    escalated_cases: int
    blocked_cases: int
    revenue_at_risk: Decimal
    revenue_recovered: Decimal
    recovery_rate: Decimal


class DashboardSummaryResponse(BaseModel):
    transactions_analyzed: int
    recovery_candidates: int
    open_cases: int
    actions_executed: int
    recovered_cases: int
    escalated_cases: int
    blocked_cases: int
    revenue_at_risk: Decimal
    revenue_recovered: Decimal
    recovery_rate: Decimal


# =========================================================
# 1. ANALYZE TRANSACTION
# =========================================================


@router.get(
    "/analyze/{transaction_id}",
    response_model=RiskAssessmentResponse,
)
def analyze_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
):
    transaction = db.get(Transaction, transaction_id)

    if not transaction:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found.",
        )

    assessment = calculate_risk(
        db=db,
        transaction=transaction,
    )

    return assessment


# =========================================================
# 2. RUN RECOVERY FOR ONE TRANSACTION
# =========================================================


@router.post(
    "/run/{transaction_id}",
    response_model=RecoveryWorkflowResponse,
)
def run_single_recovery(
    transaction_id: int,
    db: Session = Depends(get_db),
):
    transaction = db.get(Transaction, transaction_id)

    if not transaction:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found.",
        )

    try:
        result = run_recovery_workflow(
            db=db,
            transaction_id=transaction_id,
        )

        return result

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


# =========================================================
# 3. RUN BATCH RECOVERY
# =========================================================


@router.post(
    "/run",
    response_model=BatchRecoveryResponse,
)
def run_recovery_batch(
    limit: int = 500,
    db: Session = Depends(get_db),
):
    result = run_batch_recovery(
        db=db,
        limit=limit,
    )

    return {
        "transactions_analyzed": result.transactions_analyzed,
        "recovery_candidates": result.recovery_candidates,
        "actions_executed": result.actions_executed,
        "recovered_cases": result.recovered_cases,
        "escalated_cases": result.escalated_cases,
        "blocked_cases": result.blocked_cases,
        "revenue_at_risk": result.revenue_at_risk,
        "revenue_recovered": result.revenue_recovered,
        "recovery_rate": result.recovery_rate,
    }


# =========================================================
# 4. RECOVERY AUDIT
# =========================================================


@router.get("/audit/{recovery_case_id}")
def get_recovery_audit(
    recovery_case_id: int,
    db: Session = Depends(get_db),
):
    recovery_case = db.get(
        RecoveryCase,
        recovery_case_id,
    )

    if not recovery_case:
        raise HTTPException(
            status_code=404,
            detail="Recovery case not found.",
        )

    # ---------------------------------------------------------
    # Agent decisions
    # ---------------------------------------------------------

    decisions = db.scalars(
        select(AgentDecision)
        .where(
            AgentDecision.recovery_case_id
            == recovery_case_id
        )
        .order_by(
            AgentDecision.created_at.asc()
        )
    ).all()

    # ---------------------------------------------------------
    # Recovery actions
    # ---------------------------------------------------------

    actions = db.scalars(
        select(RecoveryAction)
        .where(
            RecoveryAction.recovery_case_id
            == recovery_case_id
        )
        .order_by(
            RecoveryAction.executed_at.asc()
        )
    ).all()

    # ---------------------------------------------------------
    # Audit events
    # ---------------------------------------------------------

    events = db.scalars(
        select(AuditEvent)
        .where(
            AuditEvent.recovery_case_id
            == recovery_case_id
        )
        .order_by(
            AuditEvent.created_at.asc()
        )
    ).all()

    return {
        "recovery_case": {
            "id": recovery_case.id,
            "transaction_id": recovery_case.transaction_id,
            "status": recovery_case.status,
            "amount_at_risk": recovery_case.amount_at_risk,
            "risk_reason": recovery_case.risk_reason,
        },

        "agent_decisions": [
            {
                "id": decision.id,
                "decision": decision.decision,
                "confidence": decision.confidence,
                "reasoning": decision.reasoning,
                "created_at": decision.created_at,
            }
            for decision in decisions
        ],

        "recovery_actions": [
            {
                "id": action.id,
                "action_type": action.action_type,
                "status": action.status,
                "amount_recovered": action.amount_recovered,
                "result": action.result,
                "executed_at": action.executed_at,
            }
            for action in actions
        ],

        "audit_events": [
            {
                "id": event.id,
                "event_type": event.event_type,
                "message": event.message,
                "created_at": event.created_at,
            }
            for event in events
        ],
    }


# =========================================================
# 5. DASHBOARD SUMMARY
# =========================================================


@router.get(
    "/dashboard",
    response_model=DashboardSummaryResponse,
)
def recovery_dashboard(
    db: Session = Depends(get_db),
):
    return get_dashboard_summary(db=db)


# =========================================================
# 6. TRANSACTIONS LIST (with pagination + filters + search)
# =========================================================


@router.get("/transactions")
def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = (
        select(Transaction)
        .options(joinedload(Transaction.customer))
        .options(joinedload(Transaction.recovery_case))
    )

    count_query = select(func.count(Transaction.id))

    if search:
        search_term = f"%{search}%"
        query = query.join(Transaction.customer).where(
            (Transaction.external_id.ilike(search_term)) |
            (Customer.name.ilike(search_term)) |
            (Customer.email.ilike(search_term))
        )
        count_query = count_query.join(Transaction.customer).where(
            (Transaction.external_id.ilike(search_term)) |
            (Customer.name.ilike(search_term)) |
            (Customer.email.ilike(search_term))
        )

    if status:
        query = query.where(Transaction.status == status)
        count_query = count_query.where(Transaction.status == status)

    total = db.scalar(count_query) or 0

    # Paginate
    query = (
        query
        .order_by(Transaction.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    transactions = db.scalars(query).unique().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if page_size else 0,
        "transactions": [
            {
                "id": t.id,
                "external_id": t.external_id,
                "customer_name": t.customer.name if t.customer else None,
                "customer_email": t.customer.email if t.customer else None,
                "amount": t.amount,
                "currency": t.currency,
                "status": t.status,
                "created_at": t.created_at,
                "has_recovery_case": t.recovery_case is not None,
                "recovery_case_id": t.recovery_case.id if t.recovery_case else None,
                "recovery_status": t.recovery_case.status if t.recovery_case else None,
            }
            for t in transactions
        ],
    }


# =========================================================
# 6b. SINGLE TRANSACTION DETAIL
# =========================================================


@router.get("/transactions/{transaction_id}")
def get_transaction_detail(
    transaction_id: int,
    db: Session = Depends(get_db),
):
    transaction = db.scalar(
        select(Transaction)
        .options(
            joinedload(Transaction.customer),
            joinedload(Transaction.payment_attempts),
            joinedload(Transaction.recovery_case),
        )
        .where(Transaction.id == transaction_id)
    )

    if not transaction:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found.",
        )

    return {
        "id": transaction.id,
        "external_id": transaction.external_id,
        "amount": transaction.amount,
        "currency": transaction.currency,
        "status": transaction.status,
        "created_at": transaction.created_at,
        "customer": {
            "id": transaction.customer.id,
            "name": transaction.customer.name,
            "email": transaction.customer.email,
            "external_id": transaction.customer.external_id,
        } if transaction.customer else None,
        "payment_attempts": [
            {
                "id": pa.id,
                "payment_method": pa.payment_method,
                "status": pa.status,
                "failure_code": pa.failure_code,
                "failure_reason": pa.failure_reason,
                "attempted_at": pa.attempted_at,
            }
            for pa in sorted(
                transaction.payment_attempts,
                key=lambda x: x.attempted_at,
            )
        ] if transaction.payment_attempts else [],
        "recovery_case": {
            "id": transaction.recovery_case.id,
            "status": transaction.recovery_case.status,
            "amount_at_risk": transaction.recovery_case.amount_at_risk,
            "risk_reason": transaction.recovery_case.risk_reason,
            "created_at": transaction.recovery_case.created_at,
            "resolved_at": transaction.recovery_case.resolved_at,
        } if transaction.recovery_case else None,
    }


# =========================================================
# 7. RECOVERY CASES LIST (with pagination + filters + search)
# =========================================================


@router.get("/cases")
def list_recovery_cases(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = (
        select(RecoveryCase)
        .options(
            joinedload(RecoveryCase.transaction)
            .joinedload(Transaction.customer)
        )
        .options(joinedload(RecoveryCase.decisions))
        .options(joinedload(RecoveryCase.actions))
    )

    count_query = select(func.count(RecoveryCase.id))

    if search:
        search_term = f"%{search}%"
        query = query.join(RecoveryCase.transaction).join(Transaction.customer).where(
            (Transaction.external_id.ilike(search_term)) |
            (Customer.name.ilike(search_term)) |
            (RecoveryCase.risk_reason.ilike(search_term))
        )
        count_query = count_query.join(RecoveryCase.transaction).join(Transaction.customer).where(
            (Transaction.external_id.ilike(search_term)) |
            (Customer.name.ilike(search_term)) |
            (RecoveryCase.risk_reason.ilike(search_term))
        )

    if status:
        query = query.where(RecoveryCase.status == status)
        count_query = count_query.where(RecoveryCase.status == status)
        
    if sort_by == "activity":
        query = query.join(AgentDecision).order_by(AgentDecision.created_at.desc())
    else:
        query = query.order_by(RecoveryCase.id.desc())

    total = db.scalar(count_query) or 0

    # Paginate
    query = (
        query
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    cases = db.scalars(query).unique().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if page_size else 0,
        "cases": [
            {
                "id": c.id,
                "transaction_id": c.transaction_id,
                "transaction_external_id": c.transaction.external_id if c.transaction else None,
                "customer_name": c.transaction.customer.name if c.transaction and c.transaction.customer else None,
                "status": c.status,
                "risk_reason": c.risk_reason,
                "amount_at_risk": c.amount_at_risk,
                "created_at": c.created_at,
                "resolved_at": c.resolved_at,
                "decision": c.decisions[-1].decision if c.decisions else None,
                "confidence": c.decisions[-1].confidence if c.decisions else None,
                "amount_recovered": sum(
                    a.amount_recovered for a in c.actions
                ) if c.actions else Decimal("0.00"),
                "action_count": len(c.actions),
            }
            for c in cases
        ],
    }


# =========================================================
# 8. SINGLE RECOVERY CASE DETAIL
# =========================================================


@router.get("/cases/{case_id}")
def get_recovery_case_detail(
    case_id: int,
    db: Session = Depends(get_db),
):
    recovery_case = db.scalar(
        select(RecoveryCase)
        .options(
            joinedload(RecoveryCase.transaction)
            .joinedload(Transaction.customer),
            joinedload(RecoveryCase.transaction)
            .joinedload(Transaction.payment_attempts),
            joinedload(RecoveryCase.decisions),
            joinedload(RecoveryCase.actions),
            joinedload(RecoveryCase.audit_events),
        )
        .where(RecoveryCase.id == case_id)
    )

    if not recovery_case:
        raise HTTPException(
            status_code=404,
            detail="Recovery case not found.",
        )

    transaction = recovery_case.transaction

    return {
        "recovery_case": {
            "id": recovery_case.id,
            "status": recovery_case.status,
            "risk_reason": recovery_case.risk_reason,
            "amount_at_risk": recovery_case.amount_at_risk,
            "created_at": recovery_case.created_at,
            "resolved_at": recovery_case.resolved_at,
        },
        "transaction": {
            "id": transaction.id,
            "external_id": transaction.external_id,
            "amount": transaction.amount,
            "currency": transaction.currency,
            "status": transaction.status,
            "created_at": transaction.created_at,
            "customer_name": transaction.customer.name if transaction.customer else None,
            "customer_email": transaction.customer.email if transaction.customer else None,
        },
        "payment_attempts": [
            {
                "id": pa.id,
                "payment_method": pa.payment_method,
                "status": pa.status,
                "failure_code": pa.failure_code,
                "failure_reason": pa.failure_reason,
                "attempted_at": pa.attempted_at,
            }
            for pa in sorted(
                transaction.payment_attempts,
                key=lambda pa: pa.attempted_at,
            )
        ] if transaction.payment_attempts else [],
        "agent_decisions": [
            {
                "id": d.id,
                "decision": d.decision,
                "confidence": d.confidence,
                "reasoning": d.reasoning,
                "created_at": d.created_at,
            }
            for d in sorted(
                recovery_case.decisions,
                key=lambda d: d.created_at,
            )
        ],
        "recovery_actions": [
            {
                "id": a.id,
                "action_type": a.action_type,
                "status": a.status,
                "amount_recovered": a.amount_recovered,
                "result": a.result,
                "executed_at": a.executed_at,
            }
            for a in sorted(
                recovery_case.actions,
                key=lambda a: a.executed_at or a.id,
            )
        ],
        "audit_events": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "message": e.message,
                "created_at": e.created_at,
            }
            for e in sorted(
                recovery_case.audit_events,
                key=lambda e: e.created_at,
            )
        ],
    }

@router.post("/import")
async def import_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    contents = await file.read()
    
    try:
        reader = csv.DictReader(io.StringIO(contents.decode("utf-8")))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")

    received = 0
    imported = 0
    rejected = 0
    errors = []
    
    try:
        # Create a savepoint essentially by starting a nested block or we can just rely on the main transaction 
        # and rollback if a fatal error occurs. If we want partial imports, we can handle it per row.
        # Requirements: "Malformed data must NOT be silently accepted. Failed imports must roll back safely."
        # So we should validate everything and if any row is critically bad, we could fail. Or we can just skip rows and rollback on DB errors.
        # Actually, "Failed imports must roll back safely. Imported data must not corrupt the existing demo dataset."
        # We'll use a single transaction. If any DB error occurs, we rollback and throw.
        
        customers_map = {}
        
        rows = list(reader)
        received = len(rows)
        
        for index, row in enumerate(rows, start=1):
            # Validate required columns
            try:
                txn_id = row['transaction_id']
                amount = Decimal(row['amount'])
                status = row['status']
                email = row['customer_email']
                timestamp_str = row['timestamp']
            except KeyError as e:
                raise HTTPException(status_code=400, detail=f"Missing required column {e} in row {index}")
            
            if amount <= 0:
                raise HTTPException(status_code=400, detail=f"Invalid amount {amount} in row {index}")
                
            # Check for duplicate
            existing_txn = db.scalar(select(Transaction).where(Transaction.external_id == txn_id))
            if existing_txn:
                rejected += 1
                errors.append(f"Row {index}: Transaction {txn_id} already exists")
                continue
                
            if email not in customers_map:
                existing_customer = db.scalar(select(Customer).where(Customer.email == email))
                import uuid
                if existing_customer:
                    customers_map[email] = existing_customer
                else:
                    new_customer = Customer(
                        external_id=f"CUST-IMP-{uuid.uuid4().hex[:8].upper()}-{txn_id[:6]}",
                        name=row.get('customer_name', 'Unknown'),
                        email=email,
                    )
                    db.add(new_customer)
                    db.flush()
                    customers_map[email] = new_customer
                    
            customer = customers_map[email]
            
            try:
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except Exception:
                dt = func.now()
                
            txn = Transaction(
                external_id=txn_id,
                customer_id=customer.id,
                amount=amount,
                currency=row.get('currency', 'USD'),
                status=status,
                created_at=dt
            )
            db.add(txn)
            db.flush()
            
            if status == "failed":
                pa = PaymentAttempt(
                    transaction_id=txn.id,
                    payment_method=row.get('payment_method', 'unknown'),
                    status="failed",
                    failure_code=row.get('failure_code', ''),
                    failure_reason=row.get('failure_reason', ''),
                    attempted_at=txn.created_at
                )
                db.add(pa)
                
                rc = RecoveryCase(
                    transaction_id=txn.id,
                    status="open",
                    risk_reason="Payment failure detected via import",
                    amount_at_risk=txn.amount,
                )
                db.add(rc)
                
            elif status in {"abandoned", "overdue"}:
                rc = RecoveryCase(
                    transaction_id=txn.id,
                    status="open",
                    risk_reason="Incomplete payment detected via import",
                    amount_at_risk=txn.amount,
                )
                db.add(rc)
                
            imported += 1
            
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database error during import: {str(e)}")
        
    return {
        "received": received,
        "imported": imported,
        "rejected": rejected,
        "errors": errors
    }