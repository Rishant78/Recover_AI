import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api/client'
import StatusBadge from '../components/StatusBadge'
import RiskGauge from '../components/RiskGauge'
import {
  formatCurrency,
  formatDateTime,
  formatActionType,
  formatPercent,
  formatEventType,
} from '../utils/format'
import type { CaseDetail, RiskAssessment, RecoveryWorkflowResponse } from '../types/api'

export default function CaseDetailView() {
  const { caseId } = useParams<{ caseId: string }>()
  const [detail, setDetail] = useState<CaseDetail | null>(null)
  const [riskAssessment, setRiskAssessment] = useState<RiskAssessment | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Recovery execution state
  const [executing, setExecuting] = useState(false)
  const [executionResult, setExecutionResult] = useState<RecoveryWorkflowResponse | null>(null)
  const [executionError, setExecutionError] = useState<string | null>(null)

  const fetchCase = async () => {
    if (!caseId) return
    setLoading(true)
    setError(null)
    try {
      const data = await api.getCaseDetail(Number(caseId))
      setDetail(data)

      // Auto fetch transaction risk analysis
      if (data.transaction?.id) {
        try {
          const risk = await api.analyzeTransaction(data.transaction.id)
          setRiskAssessment(risk)
        } catch {
          // Non-blocking
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load case details')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCase()
  }, [caseId])

  const handleExecuteRecovery = async () => {
    if (!detail?.transaction?.id) return
    setExecuting(true)
    setExecutionError(null)
    try {
      const res = await api.runSingleRecovery(detail.transaction.id)
      setExecutionResult(res)
      // Refresh case detail
      fetchCase()
    } catch (err) {
      setExecutionError(err instanceof Error ? err.message : 'Recovery workflow execution failed')
    } finally {
      setExecuting(false)
    }
  }

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner" />
        Loading recovery case details...
      </div>
    )
  }

  if (error || !detail) {
    return (
      <div className="error-container">
        <p>Recovery case not found or failed to load.</p>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>{error}</p>
        <Link to="/cases" className="back-link" style={{ marginTop: '12px' }}>
          ← Return to Recovery Cases
        </Link>
      </div>
    )
  }

  const { recovery_case, transaction, payment_attempts, agent_decisions, recovery_actions, audit_events } = detail
  const latestDecision = agent_decisions[agent_decisions.length - 1]
  const latestAction = recovery_actions[recovery_actions.length - 1]

  // Extract policy references from reasoning if formatted
  const policyMatches = latestDecision?.reasoning?.match(/grounded in recovery policies:\s*([^.]+)\./i)
  const policies = policyMatches ? policyMatches[1].split(',').map(p => p.trim()) : []

  // Extract stopping rule from reasoning
  const stoppingRuleMatch = latestDecision?.reasoning?.match(/Stopping rule:\s*(.+)$/i)
  const stoppingRule = stoppingRuleMatch ? stoppingRuleMatch[1] : (riskAssessment?.stopping_rule || null)

  return (
    <>
      <Link to="/cases" className="back-link">
        ← Back to Cases
      </Link>

      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h2>Case #{recovery_case.id}</h2>
            <StatusBadge status={recovery_case.status} />
          </div>
          <p>
            Transaction {transaction.external_id} • Created {formatDateTime(recovery_case.created_at)}
          </p>
        </div>

        {recovery_case.status === 'open' && (
          <button
            disabled={executing}
            onClick={handleExecuteRecovery}
            className="btn-primary"
          >
            {executing ? (
              <>
                <div className="spinner" style={{ width: 14, height: 14, borderTopColor: '#fff' }} />
                Executing Pipeline...
              </>
            ) : (
              'Run AI Recovery Workflow'
            )}
          </button>
        )}
      </div>

      {executionResult && (
        <div
          style={{
            background: 'rgba(52, 211, 153, 0.08)',
            border: '1px solid rgba(52, 211, 153, 0.3)',
            borderRadius: 'var(--radius-md)',
            padding: '14px 18px',
            color: 'var(--accent-green)',
            fontSize: '0.85rem',
            marginBottom: '20px',
          }}
        >
          <strong>Workflow Executed: </strong> {executionResult.message} (Action: {executionResult.action}, Status: {executionResult.status})
        </div>
      )}

      {executionError && (
        <div
          style={{
            background: 'rgba(248, 113, 113, 0.08)',
            border: '1px solid rgba(248, 113, 113, 0.3)',
            borderRadius: 'var(--radius-md)',
            padding: '14px 18px',
            color: 'var(--accent-red)',
            fontSize: '0.85rem',
            marginBottom: '20px',
          }}
        >
          {executionError}
        </div>
      )}

      {/* Recovery Pipeline Step Progress Overview */}
      <div
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border-primary)',
          borderRadius: 'var(--radius-lg)',
          padding: '16px 22px',
          marginBottom: '24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '8px',
          overflowX: 'auto',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ width: 24, height: 24, borderRadius: '50%', background: 'var(--accent-blue-bg)', color: 'var(--accent-blue)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem', fontWeight: 600 }}>1</span>
          <div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Input</div>
            <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-primary)' }}>Transaction</div>
          </div>
        </div>
        <span style={{ color: 'var(--text-muted)' }}>→</span>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ width: 24, height: 24, borderRadius: '50%', background: riskAssessment ? 'var(--accent-amber-bg)' : 'rgba(255,255,255,0.05)', color: riskAssessment ? 'var(--accent-amber)' : 'var(--text-muted)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem', fontWeight: 600 }}>2</span>
          <div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Risk Engine</div>
            <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              {riskAssessment ? `${riskAssessment.risk_level.toUpperCase()} (${riskAssessment.risk_score})` : 'Assessed'}
            </div>
          </div>
        </div>
        <span style={{ color: 'var(--text-muted)' }}>→</span>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ width: 24, height: 24, borderRadius: '50%', background: latestDecision ? 'var(--accent-purple-bg)' : 'rgba(255,255,255,0.05)', color: latestDecision ? 'var(--accent-purple)' : 'var(--text-muted)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem', fontWeight: 600 }}>3</span>
          <div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>AI Decision</div>
            <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              {latestDecision ? formatActionType(latestDecision.decision) : 'Pending'}
            </div>
          </div>
        </div>
        <span style={{ color: 'var(--text-muted)' }}>→</span>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ width: 24, height: 24, borderRadius: '50%', background: latestAction ? 'var(--accent-blue-bg)' : 'rgba(255,255,255,0.05)', color: latestAction ? 'var(--accent-blue)' : 'var(--text-muted)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem', fontWeight: 600 }}>4</span>
          <div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Guardrail & Action</div>
            <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              {latestAction ? formatActionType(latestAction.action_type) : 'Pending'}
            </div>
          </div>
        </div>
        <span style={{ color: 'var(--text-muted)' }}>→</span>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ width: 24, height: 24, borderRadius: '50%', background: recovery_case.status === 'recovered' ? 'var(--accent-green-bg)' : 'var(--accent-blue-bg)', color: recovery_case.status === 'recovered' ? 'var(--accent-green)' : 'var(--accent-blue)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem', fontWeight: 600 }}>5</span>
          <div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Outcome</div>
            <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              {recovery_case.status.toUpperCase()}
            </div>
          </div>
        </div>
      </div>

      {/* Main Grid: Details + AI Decision */}
      <div className="detail-grid">
        {/* Case & Transaction Summary */}
        <div className="detail-section">
          <div className="detail-section-title">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            Case & Financial Information
          </div>
          <div className="detail-row">
            <span className="detail-label">Amount at Risk</span>
            <span className="detail-value" style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--accent-red)' }}>
              {formatCurrency(recovery_case.amount_at_risk, transaction.currency)}
            </span>
          </div>
          <div className="detail-row">
            <span className="detail-label">Total Recovered</span>
            <span className="detail-value" style={{ fontWeight: 700, color: 'var(--accent-green)' }}>
              {formatCurrency(recovery_actions.reduce((acc, a) => acc + Number(a.amount_recovered), 0), transaction.currency)}
            </span>
          </div>
          <div className="detail-row">
            <span className="detail-label">Initial Risk Trigger</span>
            <span className="detail-value">{recovery_case.risk_reason}</span>
          </div>
          <div className="detail-row">
            <span className="detail-label">Transaction ID</span>
            <span className="detail-value" style={{ fontFamily: 'var(--font-mono)' }}>{transaction.external_id}</span>
          </div>
          <div className="detail-row">
            <span className="detail-label">Customer Name</span>
            <span className="detail-value">{transaction.customer_name || '—'}</span>
          </div>
          <div className="detail-row">
            <span className="detail-label">Customer Email</span>
            <span className="detail-value" style={{ fontSize: '0.78rem' }}>{transaction.customer_email || '—'}</span>
          </div>
          <div className="detail-row">
            <span className="detail-label">Original Payment Status</span>
            <span className="detail-value"><StatusBadge status={transaction.status} /></span>
          </div>
        </div>

        {/* AI Risk Vector Analysis */}
        <div className="detail-section">
          <div className="detail-section-title">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
            Risk Engine Score & Drivers
          </div>
          {riskAssessment ? (
            <div style={{ display: 'grid', gridTemplateColumns: '110px 1fr', gap: '16px', alignItems: 'center' }}>
              <RiskGauge score={riskAssessment.risk_score} level={riskAssessment.risk_level} />
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Risk Rationale</div>
                  <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '2px' }}>{riskAssessment.reason}</div>
                </div>
                <div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Recommended Action</div>
                  <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--accent-blue)', marginTop: '2px' }}>
                    {formatActionType(riskAssessment.recommended_action)}
                  </div>
                </div>
                {stoppingRule && (
                  <div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Mandatory Stopping Rule</div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--accent-amber)', marginTop: '2px' }}>{stoppingRule}</div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="table-empty">Risk score computation pending.</div>
          )}
        </div>

        {/* AI Autonomous Decision Card */}
        {latestDecision && (
          <div className="detail-section full-width decision-card">
            <div className="detail-section-title" style={{ color: 'var(--accent-blue)' }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2a10 10 0 1 0 10 10H12V2z"/><path d="M12 2a10 10 0 0 1 10 10h-10V2z"/></svg>
              Autonomous Agent Decision Evaluation
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: '24px' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px' }}>
                  <span style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {formatActionType(latestDecision.decision)}
                  </span>
                  <span style={{ padding: '4px 12px', background: 'var(--accent-purple-bg)', color: 'var(--accent-purple)', borderRadius: '100px', fontSize: '0.75rem', fontWeight: 600, border: '1px solid rgba(139, 92, 246, 0.2)' }}>
                    Confidence {formatPercent(latestDecision.confidence)}
                  </span>
                </div>

                <div style={{ marginBottom: '20px' }}>
                  <div className="terminal-block">
                    <div className="terminal-header">
                      <div className="terminal-dot" style={{ background: '#ff5f56' }} />
                      <div className="terminal-dot" style={{ background: '#ffbd2e' }} />
                      <div className="terminal-dot" style={{ background: '#27c93f' }} />
                    </div>
                    <div style={{ color: 'var(--accent-blue)', marginBottom: '8px' }}>&gt; Agent Reasoning Evaluated:</div>
                    <p>{latestDecision.reasoning}</p>
                  </div>
                </div>

                {policies.length > 0 && (
                  <div>
                    <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '8px' }}>
                      Grounded Policies Applied
                    </div>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      {policies.map(p => (
                        <span key={p} style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-primary)', padding: '4px 10px', borderRadius: '4px', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{p}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Guardrails and Action Outcome side column */}
              <div style={{ background: 'var(--bg-card)', padding: '16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-primary)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div>
                  <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Guardrail Status</div>
                  <div style={{ marginTop: '4px' }}>
                    <span style={{ color: 'var(--accent-green)', fontWeight: 600, fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      ✓ Safety Rules Checked
                    </span>
                  </div>
                </div>

                {latestAction && (
                  <div>
                    <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Latest Execution Result</div>
                    <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                      {latestAction.result || 'Executed successfully'}
                    </div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                      Executed at: {formatDateTime(latestAction.executed_at || latestDecision.created_at)}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Payment Attempts on File */}
        {payment_attempts.length > 0 && (
          <div className="detail-section full-width">
            <div className="detail-section-title">
              Payment Attempts Before Recovery ({payment_attempts.length})
            </div>
            <div style={{ border: '1px solid var(--border-primary)', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
              <table>
                <thead>
                  <tr>
                    <th>Payment Method</th>
                    <th>Status</th>
                    <th>Failure Code</th>
                    <th>Failure Reason</th>
                    <th>Attempted At</th>
                  </tr>
                </thead>
                <tbody>
                  {payment_attempts.map(pa => (
                    <tr key={pa.id}>
                      <td style={{ textTransform: 'uppercase', fontSize: '0.78rem' }}>{pa.payment_method}</td>
                      <td><StatusBadge status={pa.status} /></td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--accent-red)' }}>
                        {pa.failure_code || '—'}
                      </td>
                      <td style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{pa.failure_reason || '—'}</td>
                      <td style={{ fontSize: '0.75rem' }}>{formatDateTime(pa.attempted_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Audit Events Visual Timeline */}
        <div className="detail-section full-width">
          <div className="detail-section-title">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            Complete Recovery Audit Trail ({audit_events.length} Events)
          </div>

          {audit_events.length === 0 ? (
            <div className="table-empty">No audit trail events recorded for this case yet.</div>
          ) : (
            <div className="timeline">
              {audit_events.map((event, idx) => (
                <div key={event.id || idx} className="timeline-item">
                  <div className="timeline-line">
                    <div className="timeline-dot" />
                    {idx < audit_events.length - 1 && <div className="timeline-connector" />}
                  </div>
                  <div className="timeline-content">
                    <div className="timeline-event-type">
                      {formatEventType(event.event_type)}
                    </div>
                    <div className="timeline-message">{event.message}</div>
                    <div className="timeline-time">{formatDateTime(event.created_at)}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  )
}
