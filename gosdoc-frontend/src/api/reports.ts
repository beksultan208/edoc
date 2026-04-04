// ============================================================
// ГосДок — API отчётов (раздел 4.10 ТЗ)
// ============================================================

import apiClient from './client'
import type { MonthlyReport, PaginatedResponse } from '@/types'

// GET /api/v1/reports/
export async function getReports(params?: { page?: number }): Promise<PaginatedResponse<MonthlyReport>> {
  const response = await apiClient.get('/reports/', { params })
  return response.data
}

// POST /api/v1/reports/generate/
export async function generateReport(data: {
  period_year: number
  period_month: number
  organization: string
}): Promise<MonthlyReport> {
  const response = await apiClient.post('/reports/generate/', data)
  return response.data
}

// GET /api/v1/reports/{id}/
export async function getReport(id: string): Promise<MonthlyReport> {
  const response = await apiClient.get(`/reports/${id}/`)
  return response.data
}

// GET /api/v1/reports/{id}/export/?format=pdf|xlsx
export async function exportReport(id: string, format: 'pdf' | 'xlsx'): Promise<Blob> {
  const response = await apiClient.get(`/reports/${id}/export/`, {
    params: { format },
    responseType: 'blob',
  })
  return response.data
}

// Утилита: скачать blob как файл
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
