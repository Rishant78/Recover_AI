import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import StatusBadge from '../components/StatusBadge'
import Pagination from '../components/Pagination'
import RiskGauge from '../components/RiskGauge'
import {
  formatCurrency,
  formatDate,
  formatDateTime,
  formatActionType,
} from '../utils/format'
import type {
  TransactionItem,
  TransactionDetail,
  RiskAssessment,
  RecoveryWorkflowResponse,
} from '../types/api'

const STATUS_FILTERS = [
  { label: 'All', value: '' },
  { label: 'Failed', value: 'failed' },
  { label: 'Overdue', value: 'overdue' },
  { label: 'Abandoned', value: 'abandoned' },
  { label: 'Successful', value: 'successful' },
]

export default function Transactions() {
  const [transactions, setTransactions] = useState<TransactionItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [pageSize] = useState(20)
  const [statusFilter, setStatusFilter] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Drawer / modal state for single transaction inspection
  const [selectedTxnId, setSelectedTxnId] = useState<number | null>(null)
  const [txnDetail, setTxnDetail] = useState<TransactionDetail | null>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)

  // On-demand AI Risk Assessment
  const [riskAssessment, setRiskAssessment] = useState<RiskAssessment | null>(null)
  const [loadingRisk, setLoadingRisk] = useState(false)

  // Action execution state
  const [runningRecovery, setRunningRecovery] = useState(false)
  const [recoveryResult, setRecoveryResult] = useState<RecoveryWorkflowResponse | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery)
      setPage(1)
    }, 350)
    return () => clearTimeout(timer)
  }, [searchQuery])

  const fetchTransactions = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.getTransactions(page, pageSize, statusFilter, debouncedSearch)
      setTransactions(res.transactions)
      setTotal(res.total)
      setPages(res.pages)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load transactions')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTransactions()
  }, [page, statusFilter, debouncedSearch])

  // Open detail modal
  const handleSelectTransaction = async (id: number) => {
    setSelectedTxnId(id)
    setTxnDetail(null)
    setRiskAssessment(null)
    setRecoveryResult(null)
    setActionError(null)
    setLoadingDetail(true)

    try {
      const detail = await api.getTransactionDetail(id)
      setTxnDetail(detail)

      // Also auto-fetch risk assessment
      setLoadingRisk(true)
      try {
        const risk = await api.analyzeTransaction(id)
        setRiskAssessment(risk)
      } catch {
        // Soft fail on risk analysis
      } finally {
        setLoadingRisk(false)
      }
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to fetch transaction details')
    } finally {
      setLoadingDetail(false)
    }
  }

  const handleRunRecovery = async (transactionId: number) => {
    setRunningRecovery(true)
    setActionError(null)
    try {
      const res = await api.runSingleRecovery(transactionId)
      setRecoveryResult(res)
      // Refresh list to update status
      fetchTransactions()
      // Refresh details
      const detail = await api.getTransactionDetail(transactionId)
      setTxnDetail(detail)
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Recovery execution failed')
    } finally {
      setRunningRecovery(false)
    }
  }

  return (
    <>
      <div className="page-header">
        <h2>Transactions</h2>
        <p>Real-time payment transaction ledger and risk monitoring</p>
      </div>

      <div className="table-container">
        <div className="table-toolbar">
          <div className="table-toolbar-left">
            <input
              type="text"
              className="search-input"
              placeholder="Search by ID, customer, email..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
            <div className="filter-tabs">
              {STATUS_FILTERS.map(f => (
                <button
                  key={f.value}
                  className={`filter-tab ${statusFilter === f.value ? 'active' : ''}`}
                  onClick={() => {
                    setStatusFilter(f.value)
                    setPage(1)
                  }}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {loading ? (
          <div className="loading-container">
            <div className="spinner" />
            Loading transactions...
          </div>
        ) : error ? (
          <div className="error-container">
            <p>{error}</p>
          </div>
        ) : transactions.length === 0 ? (
          <div className="table-empty">No transactions match the selected criteria.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Transaction ID</th>
                <th>Customer</th>
                <th className="text-right">Amount</th>
                <th>Status</th>
                <th>Recovery</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map(t => (
                <tr key={t.id} onClick={() => handleSelectTransaction(t.id)}>
                  <td>
                    <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', fontWeight: 500 }}>
                      {t.external_id}
                    </span>
                  </td>
                  <td>
                    <div style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{t.customer_name || '—'}</div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{t.customer_email || '—'}</div>
                  </td>
                  <td className="text-right" style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                    {formatCurrency(t.amount, t.currency)}
                  </td>
                  <td>
                    <StatusBadge status={t.status} />
                  </td>
                  <td>
                    {t.has_recovery_case ? (
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                        <StatusBadge status={t.recovery_status || 'open'} />
                        <Link
                          to={`/cases/${t.recovery_case_id}`}
                          onClick={e => e.stopPropagation()}
                          style={{ fontSize: '0.75rem', color: 'var(--accent-blue)' }}
                        >
                          View Case →
                        </Link>
                      </span>
                    ) : (
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>No case</span>
                    )}
                  </td>
                  <td style={{ fontSize: '0.78rem' }}>{formatDate(t.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <Pagination
          page={page}
          pages={pages}
          total={total}
          pageSize={pageSize}
          onPageChange={p => setPage(p)}
        />
      </div>

      {/* Transaction Inspection Drawer */}
      {selectedTxnId && (
        <div
          className="modal-overlay"
          onClick={() => setSelectedTxnId(null)}
        >
          <div
            className="drawer"
            onClick={e => e.stopPropagation()}
          >
            <div className="drawer-header">
              <div>
                <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--text-muted)', fontWeight: 600 }}>
                  Transaction Inspection
                </span>
                <h3 style={{ fontSize: '1.25rem', color: 'var(--text-primary)', marginTop: '2px', fontWeight: 600 }}>
                  {txnDetail?.external_id || `Transaction #${selectedTxnId}`}
                </h3>
              </div>
              <button
                onClick={() => setSelectedTxnId(null)}
                className="btn-secondary"
                style={{ padding: '6px 12px', fontSize: '0.85rem' }}
              >
                ✕ Close
              </button>
            </div>

            <div className="drawer-content">
              {loadingDetail ? (
                <div className="loading-container">
                  <div className="spinner" />
                  Loading transaction details...
                </div>
              ) : txnDetail ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                  {/* Top Metrics Row */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
                    <div style={{ background: 'var(--bg-primary)', padding: '16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-primary)' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Amount</div>
                      <div style={{ fontSize: '1.2rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '4px' }}>
                        {formatCurrency(txnDetail.amount, txnDetail.currency)}
                      </div>
                    </div>
                    <div style={{ background: 'var(--bg-primary)', padding: '16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-primary)' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Status</div>
                      <div style={{ marginTop: '6px' }}>
                        <StatusBadge status={txnDetail.status} />
                      </div>
                    </div>
                    <div style={{ background: 'var(--bg-primary)', padding: '16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-primary)' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Customer</div>
                      <div style={{ fontSize: '0.9rem', fontWeight: 500, color: 'var(--text-primary)', marginTop: '4px' }}>
                        {txnDetail.customer?.name || '—'}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{txnDetail.customer?.email}</div>
                    </div>
                    <div style={{ background: 'var(--bg-primary)', padding: '16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-primary)' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Created At</div>
                      <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '6px' }}>
                        {formatDateTime(txnDetail.created_at)}
                      </div>
                    </div>
                  </div>

                  {/* AI Risk Engine Section */}
                  <div style={{ background: 'var(--bg-primary)', padding: '24px', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-primary)', boxShadow: 'var(--shadow-sm)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                      <span style={{ fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="var(--accent-blue)" strokeWidth="2" strokeLinecap="round"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" /></svg>
                        AI Risk Engine Assessment
                      </span>
                    </div>

                    {loadingRisk ? (
                      <div className="loading-container" style={{ padding: '20px' }}>
                        <div className="spinner" /> Analyzing risk vectors...
                      </div>
                    ) : riskAssessment ? (
                      <div style={{ display: 'grid', gridTemplateColumns: '100px 1fr', gap: '24px', alignItems: 'center' }}>
                        <RiskGauge score={riskAssessment.risk_score} level={riskAssessment.risk_level} />
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                          <div>
                            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '2px' }}>Reasoning: </span>
                            <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>{riskAssessment.reason}</span>
                          </div>
                          <div style={{ display: 'flex', gap: '24px' }}>
                            <div>
                              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '2px' }}>Recommended Action: </span>
                              <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--accent-blue)' }}>
                                {formatActionType(riskAssessment.recommended_action)}
                              </span>
                            </div>
                            <div>
                              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '2px' }}>Stopping Rule: </span>
                              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{riskAssessment.stopping_rule}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Risk analysis not available for this transaction.</div>
                    )}
                  </div>

                  {/* Payment Attempts */}
                  {txnDetail.payment_attempts.length > 0 && (
                    <div>
                      <span style={{ fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--text-primary)', marginBottom: '12px', display: 'block' }}>
                        Payment Attempts ({txnDetail.payment_attempts.length})
                      </span>
                      <div className="table-container">
                        <table>
                          <thead>
                            <tr>
                              <th>Method</th>
                              <th>Status</th>
                              <th>Failure Code</th>
                              <th>Reason</th>
                              <th>Time</th>
                            </tr>
                          </thead>
                          <tbody>
                            {txnDetail.payment_attempts.map(pa => (
                              <tr key={pa.id}>
                                <td style={{ textTransform: 'uppercase' }}>{pa.payment_method}</td>
                                <td><StatusBadge status={pa.status} /></td>
                                <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-red)' }}>
                                  {pa.failure_code || '—'}
                                </td>
                                <td>{pa.failure_reason || '—'}</td>
                                <td>{formatDateTime(pa.attempted_at)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Recovery Action / Execution Panel */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '20px', borderTop: '1px solid var(--border-primary)' }}>
                    <div>
                      {txnDetail.recovery_case ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                          <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Case #{txnDetail.recovery_case.id}:</span>
                          <StatusBadge status={txnDetail.recovery_case.status} />
                          <Link
                            to={`/cases/${txnDetail.recovery_case.id}`}
                            style={{ fontSize: '0.85rem', fontWeight: 500, color: 'var(--accent-blue)', marginLeft: '8px', display: 'flex', alignItems: 'center', gap: '4px' }}
                          >
                            Open Full Audit Trail <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polyline points="9 18 15 12 9 6" /></svg>
                          </Link>
                        </div>
                      ) : (
                        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>No recovery case initiated yet</span>
                      )}
                    </div>

                    {txnDetail.status !== 'successful' && (
                      <button
                        className="btn-primary"
                        disabled={runningRecovery || txnDetail.recovery_case?.status === 'recovered'}
                        onClick={() => handleRunRecovery(txnDetail.id)}
                      >
                        {runningRecovery ? (
                          <>
                            <div className="spinner" style={{ width: 16, height: 16, borderTopColor: '#fff', borderWidth: '2px' }} />
                            Running Recovery...
                          </>
                        ) : (
                          'Trigger Recovery Workflow'
                        )}
                      </button>
                    )}
                  </div>

                  {/* Feedback message on recovery execution */}
                  {recoveryResult && (
                    <div
                      style={{
                        background: 'var(--accent-green-bg)',
                        border: '1px solid rgba(16, 185, 129, 0.2)',
                        borderRadius: 'var(--radius-md)',
                        padding: '16px',
                        color: 'var(--accent-green)',
                        fontSize: '0.85rem',
                      }}
                    >
                      <strong>Recovery executed: </strong> {recoveryResult.message} (Action: {recoveryResult.action}, Status: {recoveryResult.status})
                    </div>
                  )}

                  {actionError && (
                    <div
                      style={{
                        background: 'var(--accent-red-bg)',
                        border: '1px solid rgba(239, 68, 68, 0.2)',
                        borderRadius: 'var(--radius-md)',
                        padding: '16px',
                        color: 'var(--accent-red)',
                        fontSize: '0.85rem',
                      }}
                    >
                      {actionError}
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
