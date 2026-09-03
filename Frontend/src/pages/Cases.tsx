import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import StatusBadge from '../components/StatusBadge'
import Pagination from '../components/Pagination'
import {
  formatCurrency,
  formatDate,
  formatPercent,
  formatActionType,
  formatNumber,
} from '../utils/format'
import type { RecoveryCaseItem, BatchRecoveryResponse } from '../types/api'

const CASE_STATUS_FILTERS = [
  { label: 'All', value: '' },
  { label: 'Open', value: 'open' },
  { label: 'Recovered', value: 'recovered' },
  { label: 'Escalated', value: 'escalated' },
  { label: 'Blocked', value: 'blocked' },
]

export default function Cases() {
  const navigate = useNavigate()
  const [cases, setCases] = useState<RecoveryCaseItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [pageSize] = useState(20)
  const [statusFilter, setStatusFilter] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Batch recovery state
  const [runningBatch, setRunningBatch] = useState(false)
  const [batchModalOpen, setBatchModalOpen] = useState(false)
  const [batchResult, setBatchResult] = useState<BatchRecoveryResponse | null>(null)
  const [batchLimit, setBatchLimit] = useState(500)
  const [batchError, setBatchError] = useState<string | null>(null)

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery)
      setPage(1)
    }, 350)
    return () => clearTimeout(timer)
  }, [searchQuery])

  const fetchCases = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.getCases(page, pageSize, statusFilter, debouncedSearch)
      setCases(res.cases)
      setTotal(res.total)
      setPages(res.pages)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load recovery cases')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCases()
  }, [page, statusFilter, debouncedSearch])

  const handleRunBatch = async () => {
    setRunningBatch(true)
    setBatchError(null)
    try {
      const result = await api.runBatchRecovery(batchLimit)
      setBatchResult(result)
      fetchCases()
    } catch (err) {
      setBatchError(err instanceof Error ? err.message : 'Batch recovery execution failed')
    } finally {
      setRunningBatch(false)
    }
  }

  return (
    <>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2>Recovery Cases</h2>
          <p>Autonomous AI policy evaluation, guardrail enforcement, and remediation cases</p>
        </div>
        <button
          onClick={() => {
            setBatchResult(null)
            setBatchError(null)
            setBatchModalOpen(true)
          }}
          className="btn-primary"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="5 3 19 12 5 21 5 3" />
          </svg>
          Run Batch Recovery
        </button>
      </div>

      <div className="table-container">
        <div className="table-toolbar">
          <div className="table-toolbar-left">
            <input
              type="text"
              className="search-input"
              placeholder="Search by TXN, customer, risk reason..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
            <div className="filter-tabs">
              {CASE_STATUS_FILTERS.map(f => (
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
            Loading cases...
          </div>
        ) : error ? (
          <div className="error-container">
            <p>{error}</p>
          </div>
        ) : cases.length === 0 ? (
          <div className="table-empty">No recovery cases found for the selected filter.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Case ID</th>
                <th>Transaction</th>
                <th>Customer</th>
                <th className="text-right">Amount At Risk</th>
                <th>Status</th>
                <th>Latest Decision</th>
                <th>Confidence</th>
                <th>Actions</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {cases.map(c => (
                <tr
                  key={c.id}
                  onClick={() => navigate(`/cases/${c.id}`)}
                  style={{ cursor: 'pointer' }}
                >
                  <td>
                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--accent-blue)' }}>
                      #{c.id}
                    </span>
                  </td>
                  <td>
                    <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', fontSize: '0.8rem' }}>
                      {c.transaction_external_id || `TXN-${c.transaction_id}`}
                    </span>
                  </td>
                  <td>
                    <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                      {c.customer_name || '—'}
                    </span>
                  </td>
                  <td className="text-right" style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                    {formatCurrency(c.amount_at_risk)}
                  </td>
                  <td>
                    <StatusBadge status={c.status} />
                  </td>
                  <td>
                    {c.decision ? (
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-primary)', fontWeight: 500 }}>
                        {formatActionType(c.decision)}
                      </span>
                    ) : (
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Pending evaluation</span>
                    )}
                  </td>
                  <td>
                    {c.confidence != null ? (
                      <span style={{ color: 'var(--accent-purple)', fontWeight: 600, fontSize: '0.8rem' }}>
                        {formatPercent(c.confidence)}
                      </span>
                    ) : (
                      <span style={{ color: 'var(--text-muted)' }}>—</span>
                    )}
                  </td>
                  <td>
                    <span
                      style={{
                        padding: '2px 8px',
                        background: 'rgba(255, 255, 255, 0.05)',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: 500,
                      }}
                    >
                      {c.action_count} executed
                    </span>
                  </td>
                  <td style={{ fontSize: '0.78rem' }}>{formatDate(c.created_at)}</td>
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

      {/* Batch Recovery Modal */}
      {batchModalOpen && (
        <div
          className="modal-overlay"
          style={{ justifyContent: 'center', alignItems: 'center' }}
          onClick={() => setBatchModalOpen(false)}
        >
          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-primary)',
              borderRadius: 'var(--radius-xl)',
              width: '100%',
              maxWidth: '650px',
              padding: '28px',
              boxShadow: 'var(--shadow-lg)',
            }}
            onClick={e => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
              <div>
                <span style={{ fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.8px', color: 'var(--accent-purple)', fontWeight: 600 }}>
                  Automated Autonomous Recovery
                </span>
                <h3 style={{ fontSize: '1.25rem', color: 'var(--text-primary)', marginTop: '2px' }}>
                  Run Batch Recovery Orchestrator
                </h3>
              </div>
              <button
                onClick={() => setBatchModalOpen(false)}
                className="btn-secondary"
                style={{ padding: '4px 10px' }}
              >
                ✕
              </button>
            </div>

            <p style={{ fontSize: '0.83rem', color: 'var(--text-secondary)', marginBottom: '20px', lineHeight: 1.5 }}>
              Executes the full recovery pipeline (Risk Engine → Policy Retriever → Decision Engine → Guardrail Safety Checks → Execution Simulation → Audit Trail) across all eligible open transactions idempotently.
            </p>

            <div style={{ marginBottom: '20px', background: 'var(--bg-primary)', padding: '16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-primary)' }}>
              <label style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                Batch Limit (Max transactions to process)
              </label>
              <input
                type="number"
                min="10"
                max="1000"
                step="10"
                value={batchLimit}
                onChange={e => setBatchLimit(Number(e.target.value))}
                style={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-primary)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '8px 12px',
                  color: 'var(--text-primary)',
                  fontSize: '0.85rem',
                  width: '120px',
                }}
              />
            </div>

            {batchError && (
              <div style={{ padding: '12px', background: 'rgba(248, 113, 113, 0.1)', color: 'var(--accent-red)', borderRadius: 'var(--radius-sm)', fontSize: '0.82rem', marginBottom: '16px' }}>
                {batchError}
              </div>
            )}

            {batchResult && (
              <div style={{ background: 'var(--bg-primary)', padding: '18px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-primary)', marginBottom: '20px' }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--accent-green)', marginBottom: '12px' }}>
                  ✓ Batch Recovery Completed
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
                  <div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Analyzed</div>
                    <div style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)' }}>{formatNumber(batchResult.transactions_analyzed)}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Candidates</div>
                    <div style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)' }}>{formatNumber(batchResult.recovery_candidates)}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Actions Run</div>
                    <div style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--accent-blue)' }}>{formatNumber(batchResult.actions_executed)}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Recovered</div>
                    <div style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--accent-green)' }}>{formatNumber(batchResult.recovered_cases)}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Escalated</div>
                    <div style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--accent-amber)' }}>{formatNumber(batchResult.escalated_cases)}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Blocked</div>
                    <div style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--accent-red)' }}>{formatNumber(batchResult.blocked_cases)}</div>
                  </div>
                  <div style={{ gridColumn: 'span 3', borderTop: '1px solid var(--border-primary)', paddingTop: '10px', marginTop: '4px', display: 'flex', justifyContent: 'space-between' }}>
                    <div>
                      <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Revenue Recovered: </span>
                      <strong style={{ color: 'var(--accent-green)', fontSize: '0.9rem' }}>{formatCurrency(batchResult.revenue_recovered)}</strong>
                    </div>
                    <div>
                      <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Recovery Rate: </span>
                      <strong style={{ color: 'var(--accent-blue)', fontSize: '0.9rem' }}>{formatPercent(batchResult.recovery_rate)}</strong>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <button
                onClick={() => setBatchModalOpen(false)}
                className="btn-secondary"
              >
                Close
              </button>
              <button
                disabled={runningBatch}
                onClick={handleRunBatch}
                className="btn-primary"
              >
                {runningBatch ? (
                  <>
                    <div className="spinner" style={{ width: 14, height: 14, borderTopColor: '#fff' }} />
                    Running Batch...
                  </>
                ) : (
                  'Start Batch Processing'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
