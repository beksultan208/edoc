// ============================================================
// ГосДок — API уведомлений (раздел 4.9 ТЗ)
// ============================================================

import apiClient from './client'
import type { Notification, PaginatedResponse } from '@/types'

// GET /api/v1/notifications/
export async function getNotifications(params?: {
  is_read?: boolean
  type?: string
  page?: number
}): Promise<PaginatedResponse<Notification>> {
  const response = await apiClient.get('/notifications/', { params })
  return response.data
}

// POST /api/v1/notifications/{id}/read/
export async function markNotificationRead(id: string): Promise<{ detail: string }> {
  const response = await apiClient.post(`/notifications/${id}/read/`)
  return response.data
}

// POST /api/v1/notifications/read-all/
export async function markAllNotificationsRead(): Promise<{ detail: string }> {
  const response = await apiClient.post('/notifications/read-all/')
  return response.data
}
