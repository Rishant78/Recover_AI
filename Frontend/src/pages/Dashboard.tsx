import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { useApi } from '../hooks/useApi'
import { formatCurrency, formatPercent, formatNumber, formatActionType, formatDate } from '../utils/format'
import StatusBadge from '../components/StatusBadge'
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Legend
} from 'recharts'
import type { RecoveryCaseItem } from '../types/api'

const CHART_COLORS = {
  recovered: '#EDEDED',
  escalated: '#71717A',
  blocked: '#3F3F46',
  open: '#A1A1AA',
}

export default function Dashboard() {
  const { data, loading, error } = useApi(() => api.getDashboard(), [])
  const [recentCases, setRecentCases] = useState<RecoveryCaseItem[]>([])
  const [casesLoading, setCasesLoading] = useState(true)
  const [importing, setImporting] = useState(false)
  const [batchRunning, setBatchRunning] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const fetchDashboardData = async () => {
    try {
      const dashboardRes = await api.getDashboard()
      // This is handled by useApi internally, but since we are manually refreshing:
      // Wait, useApi doesn't expose a reload method. I'll just reload the page on success to keep it simple and ensure all child components (if any) get updated state.
      window.location.reload()
    } catch (e) {
      console.error(e)
    }
  }

  const handleBatchRecovery = async () => {
    setBatchRunning(true)
    try {
      await api.runBatchRecovery(100) // run a small batch for demo speed
      alert('Batch recovery completed successfully.')
      fetchDashboardData()
    } catch (err: any) {
      alert(`Batch recovery failed: ${err.message}`)
      setBatchRunning(false)
    }
  }

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setImporting(true)
    try {
      const res = await api.importCsv(file)
      alert(`Import complete!\nReceived: ${res.received}\nImported: ${res.imported}\nRejected: ${res.rejected}`)
      fetchDashboardData()
    } catch (err: any) {
      alert(`Import failed: ${err.message}`)
      setImporting(false)
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  useEffect(() => {
    // Fetch recent cases ordered by activity for the AI Activity Log
    api.getCases(1, 8, '', '', 'activity').then(res => {
      setRecentCases(res.cases)
      setCasesLoading(false)
    }).catch(() => setCasesLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="loading-container" style={{ minHeight: '60vh', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        <div className="spinner" />
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', marginTop: '16px', color: 'var(--text-muted)' }}>SYS_INIT :: LOADING_ANALYTICS...</div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="error-container">
        <p>Failed to load dashboard</p>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>{error}</p>
      </div>
    )
  }

  const revenueAtRisk = Number(data.revenue_at_risk)
  const revenueRecovered = Number(data.revenue_recovered)
  const recoveryRate = Number(data.recovery_rate)

  const statusData = [
    { name: 'Open', value: data.open_cases, color: CHART_COLORS.open },
    { name: 'Recovered', value: data.recovered_cases, color: CHART_COLORS.recovered },
    { name: 'Escalated', value: data.escalated_cases, color: CHART_COLORS.escalated },
    { name: 'Blocked', value: data.blocked_cases, color: CHART_COLORS.blocked },
  ].filter(d => d.value > 0)

  const revenueData = [
    { name: 'At Risk', value: revenueAtRisk, fill: '#3F3F46' },
    { name: 'Recovered', value: revenueRecovered, fill: '#EDEDED' },
  ]

  // Filter highest value cases
  const highValueCases = [...recentCases]
    .filter(c => c.status === 'open')
    .sort((a, b) => b.amount_at_risk - a.amount_at_risk)
    .slice(0, 5)

  // Recent AI activity (all resolved or actively processed cases)
  const aiActivity = [...recentCases]
    .filter(c => c.decision)
    .slice(0, 4)

  return (
    <>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', paddingBottom: '32px' }}>
        <div>
          <h2>Recovery Overview</h2>
          <p>AI Infrastructure & Revenue Operations Control Center</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--accent-green)', boxShadow: '0 0 10px var(--accent-green)' }} />
            SYSTEM_ONLINE
          </div>
          <button className="btn-secondary" onClick={() => fetchDashboardData()} style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)' }}>
            [ REFRESH_DATA ]
          </button>
        </div>
      </div>

      {/* Judge Tools Panel */}
      <div className="card" style={{ marginBottom: '24px', padding: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', border: '1px solid var(--border)' }}>
        <div>
          <h3 style={{ margin: '0 0 4px 0', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
            Judge Tools (Demo Controls)
          </h3>
          <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-muted)' }}>Trigger AI recovery workflows or load custom evaluation data.</p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button 
            className="btn-primary" 
            onClick={handleBatchRecovery} 
            disabled={batchRunning}
            style={{ fontSize: '0.85rem' }}
          >
            {batchRunning ? 'Running Batch...' : '▶ Run Batch Recovery'}
          </button>
          
          <input 
            type="file" 
            accept=".csv" 
            style={{ display: 'none' }} 
            ref={fileInputRef} 
            onChange={handleImport} 
          />
          <button 
            className="btn-secondary" 
            onClick={() => fileInputRef.current?.click()} 
            disabled={importing}
            style={{ fontSize: '0.85rem' }}
          >
            {importing ? 'Importing...' : 'Upload Custom CSV'}
          </button>
          <a href="/data/realistic_transactions.csv" download className="btn-secondary" style={{ fontSize: '0.85rem', textDecoration: 'none', display: 'flex', alignItems: 'center' }}>
            Template CSV
          </a>
        </div>
      </div>

      {/* KPI Grid - Full Width, Upscaled */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-header">
            <div className="kpi-label">Revenue at Risk</div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>METRIC_01</div>
          </div>
          <div className="kpi-value">{formatCurrency(revenueAtRisk)}</div>
          <div className="kpi-sub">VOL: {formatNumber(data.recovery_candidates)} CANDIDATES</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <div className="kpi-label">Revenue Recovered</div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>METRIC_02</div>
          </div>
          <div className="kpi-value" style={{ color: 'var(--text-primary)', textShadow: '0 0 20px rgba(255,255,255,0.1)' }}>{formatCurrency(revenueRecovered)}</div>
          <div className="kpi-sub" style={{ color: 'var(--accent-green)' }}>YIELD: {formatPercent(recoveryRate)}</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <div className="kpi-label">Total Analyzed</div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>METRIC_03</div>
          </div>
          <div className="kpi-value">{formatNumber(data.transactions_analyzed)}</div>
          <div className="kpi-sub">ACT: {formatNumber(data.actions_executed)} EXECUTED</div>
        </div>
      </div>

      {/* Charts Section - Much larger */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(500px, 1fr))', gap: '32px', marginBottom: '48px' }}>
        <div className="kpi-card" style={{ padding: '32px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '32px' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>Recovery Pipeline Status</h3>
            <span style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>VIZ_DISTRIBUTION</span>
          </div>
          <div style={{ height: 350 }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={statusData}
                  cx="50%"
                  cy="50%"
                  innerRadius={90}
                  outerRadius={130}
                  paddingAngle={2}
                  dataKey="value"
                  stroke="none"
                >
                  {statusData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-primary)', borderRadius: 'var(--radius-sm)' }}
                  itemStyle={{ color: 'var(--text-primary)', fontSize: '0.85rem' }}
                />
                <Legend iconType="circle" wrapperStyle={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="kpi-card" style={{ padding: '32px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '32px' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>Revenue Impact</h3>
            <span style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>VIZ_IMPACT</span>
          </div>
          <div style={{ height: 350 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={revenueData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <XAxis dataKey="name" stroke="var(--border-primary)" tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
                <YAxis stroke="var(--border-primary)" tick={{ fill: 'var(--text-muted)', fontSize: 12 }} tickFormatter={(val) => `${val / 1000}k`} />
                <Tooltip 
                  cursor={{ fill: 'var(--bg-surface)' }}
                  contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-primary)', borderRadius: 'var(--radius-sm)' }}
                  formatter={(val: any) => formatCurrency(Number(val) || 0)}
                />
                <Bar dataKey="value" radius={[4, 4, 0, 0]} barSize={80} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Operational Area */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(500px, 1fr))', gap: '32px' }}>
        
        {/* Highest Value Open Cases */}
        <div className="kpi-card" style={{ padding: '32px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>Highest-Value Open Cases</h3>
            <Link to="/cases" style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--accent-blue)' }}>VIEW_ALL →</Link>
          </div>
          
          {casesLoading ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>Fetching cases...</div>
          ) : highValueCases.length === 0 ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>No open cases.</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th style={{ padding: '12px 0', borderBottom: '1px solid var(--border-primary)', fontSize: '0.75rem', color: 'var(--text-muted)', textAlign: 'left' }}>CASE_ID</th>
                  <th style={{ padding: '12px 0', borderBottom: '1px solid var(--border-primary)', fontSize: '0.75rem', color: 'var(--text-muted)', textAlign: 'left' }}>CUSTOMER</th>
                  <th style={{ padding: '12px 0', borderBottom: '1px solid var(--border-primary)', fontSize: '0.75rem', color: 'var(--text-muted)', textAlign: 'right' }}>AMOUNT</th>
                </tr>
              </thead>
              <tbody>
                {highValueCases.map(c => (
                  <tr key={c.id} style={{ borderBottom: '1px solid var(--border-primary)' }}>
                    <td style={{ padding: '16px 0', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
                      <Link to={`/cases/${c.id}`}>#{c.id}</Link>
                    </td>
                    <td style={{ padding: '16px 0', fontSize: '0.85rem' }}>
                      <div style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{c.customer_name || 'Unknown'}</div>
                    </td>
                    <td style={{ padding: '16px 0', textAlign: 'right', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {formatCurrency(c.amount_at_risk)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* AI Recovery Activity Timeline */}
        <div className="kpi-card" style={{ padding: '32px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>AI Agent Activity Log</h3>
            <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>LIVE_FEED</span>
          </div>

          {casesLoading ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>Fetching activity...</div>
          ) : aiActivity.length === 0 ? (
            <div style={{ padding: '32px 0', textAlign: 'center', color: 'var(--text-muted)' }}>
              No recent AI activity. Run a batch recovery to see results.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              {aiActivity.map(c => (
                <div key={c.id} style={{ display: 'flex', gap: '16px', paddingBottom: '24px', borderBottom: '1px solid var(--border-primary)' }}>
                  <div style={{ width: '2px', background: 'var(--border-primary)', position: 'relative' }}>
                    <div style={{ position: 'absolute', top: 0, left: -4, width: 10, height: 10, borderRadius: '50%', background: 'var(--accent-blue)', boxShadow: '0 0 10px var(--accent-blue)' }} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        CASE_{c.id} • TXN_{c.transaction_external_id}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{formatDate(c.created_at)}</div>
                    </div>
                    
                    <div style={{ fontSize: '0.9rem', color: 'var(--text-primary)', marginBottom: '8px', lineHeight: 1.4 }}>
                      AI Agent assessed risk (<span style={{ color: 'var(--accent-amber)' }}>{c.risk_reason}</span>) 
                      and decided to execute <strong style={{ color: 'var(--text-primary)' }}>{c.decision ? formatActionType(c.decision) : 'action'}</strong>.
                    </div>
                    
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <StatusBadge status={c.status} />
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        Confidence: {formatPercent(c.confidence || 0)}
                      </span>
                    </div>
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
