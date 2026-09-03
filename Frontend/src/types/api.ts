/* ============================================================
   TypeScript types matching the backend API responses
   ============================================================ */

export interface DashboardSummary {
  transactions_analyzed: number
  recovery_candidates: number
  open_cases: number
  actions_executed: number
  recovered_cases: number
  escalated_cases: number
  blocked_cases: number
  revenue_at_risk: number | string
  revenue_recovered: number | string
  recovery_rate: number | string
}

export interface TransactionItem {
  id: number
  external_id: string
  customer_name: string | null
  customer_email: string | null
  amount: number
  currency: string
  status: string
  created_at: string
  has_recovery_case: boolean
  recovery_case_id: number | null
  recovery_status: string | null
}

export interface TransactionListResponse {
  total: number
  page: number
  page_size: number
  pages: number
  transactions: TransactionItem[]
}

export interface RecoveryCaseItem {
  id: number
  transaction_id: number
  transaction_external_id: string | null
  customer_name: string | null
  status: string
  risk_reason: string
  amount_at_risk: number
  created_at: string
  resolved_at: string | null
  decision: string | null
  confidence: number | null
  amount_recovered: number
  action_count: number
}

export interface CaseListResponse {
  total: number
  page: number
  page_size: number
  pages: number
  cases: RecoveryCaseItem[]
}

export interface PaymentAttempt {
  id: number
  payment_method: string
  status: string
  failure_code: string | null
  failure_reason: string | null
  attempted_at: string
}

export interface AgentDecision {
  id: number
  decision: string
  confidence: number
  reasoning: string
  created_at: string
}

export interface RecoveryAction {
  id: number
  action_type: string
  status: string
  amount_recovered: number
  result: string | null
  executed_at: string | null
}

export interface AuditEvent {
  id: number
  event_type: string
  message: string
  created_at: string
}

export interface CaseDetail {
  recovery_case: {
    id: number
    status: string
    risk_reason: string
    amount_at_risk: number
    created_at: string
    resolved_at: string | null
  }
  transaction: {
    id: number
    external_id: string
    amount: number
    currency: string
    status: string
    created_at: string
    customer_name: string | null
    customer_email: string | null
  }
  payment_attempts: PaymentAttempt[]
  agent_decisions: AgentDecision[]
  recovery_actions: RecoveryAction[]
  audit_events: AuditEvent[]
}

export interface RiskAssessment {
  transaction_id: number
  amount_at_risk: number | string
  risk_score: number
  risk_level: string
  reason: string
  recommended_action: string
  stopping_rule: string
}

export interface TransactionDetail {
  id: number
  external_id: string
  amount: number
  currency: string
  status: string
  created_at: string
  customer: {
    id: number
    name: string
    email: string
    external_id: string
  } | null
  payment_attempts: PaymentAttempt[]
  recovery_case: {
    id: number
    status: string
    amount_at_risk: number
    risk_reason: string
    created_at: string
    resolved_at: string | null
  } | null
}

export interface RecoveryWorkflowResponse {
  transaction_id: number
  recovery_case_id: number
  decision: string
  action: string
  status: string
  confidence: number
  amount_recovered: number
  message: string
}

export interface BatchRecoveryResponse {
  transactions_analyzed: number
  recovery_candidates: number
  actions_executed: number
  recovered_cases: number
  escalated_cases: number
  blocked_cases: number
  revenue_at_risk: number
  revenue_recovered: number
  recovery_rate: number
}

