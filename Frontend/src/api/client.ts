/* ============================================================
   Centralized API client for all backend calls
   ============================================================ */

import type {
  DashboardSummary,
  TransactionListResponse,
  TransactionDetail,
  CaseListResponse,
  CaseDetail,
  RiskAssessment,
  RecoveryWorkflowResponse,
  BatchRecoveryResponse,
} from '../types/api'

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001'

async function fetchJSON<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(error.detail || `API error ${res.status}`)
  }
  return res.json()
}

export const api = {
  getDashboard(): Promise<DashboardSummary> {
    return fetchJSON('/api/v1/recovery/dashboard')
  },

  getTransactions(
    page = 1,
    pageSize = 20,
    status?: string,
    search?: string
  ): Promise<TransactionListResponse> {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    })
    if (status) params.set('status', status)
    if (search) params.set('search', search)
    return fetchJSON(`/api/v1/recovery/transactions?${params}`)
  },

  getTransactionDetail(transactionId: number): Promise<TransactionDetail> {
    return fetchJSON(`/api/v1/recovery/transactions/${transactionId}`)
  },

  getCases(
    page = 1,
    pageSize = 20,
    status?: string,
    search?: string,
    sortBy?: string
  ): Promise<CaseListResponse> {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    })
    if (status) params.set('status', status)
    if (search) params.set('search', search)
    if (sortBy) params.set('sort_by', sortBy)
    return fetchJSON(`/api/v1/recovery/cases?${params}`)
  },

  getCaseDetail(caseId: number): Promise<CaseDetail> {
    return fetchJSON(`/api/v1/recovery/cases/${caseId}`)
  },

  analyzeTransaction(transactionId: number): Promise<RiskAssessment> {
    return fetchJSON(`/api/v1/recovery/analyze/${transactionId}`)
  },

  runSingleRecovery(transactionId: number): Promise<RecoveryWorkflowResponse> {
    return fetchJSON(`/api/v1/recovery/run/${transactionId}`, {
      method: 'POST',
    })
  },

  runBatchRecovery(limit = 500): Promise<BatchRecoveryResponse> {
    return fetchJSON(`/api/v1/recovery/run?limit=${limit}`, {
      method: 'POST',
    })
  },

  async importCsv(file: File): Promise<{ received: number; imported: number; rejected: number; errors: string[] }> {
    const formData = new FormData()
    formData.append('file', file)

    const res = await fetch(`${API_BASE}/api/v1/recovery/import`, {
      method: 'POST',
      body: formData,
    })

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(error.detail || `API error ${res.status}`)
    }
    return res.json()
  },
}
