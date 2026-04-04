// ============================================================
// ГосДок — API задач (раздел 4.6 ТЗ)
// ============================================================

import apiClient from './client'
import type { PaginatedResponse, Task, TaskStatus } from '@/types'

// GET /api/v1/tasks/
export async function getTasks(params?: {
  status?: TaskStatus
  workspace?: string
  page?: number
}): Promise<PaginatedResponse<Task>> {
  const response = await apiClient.get('/tasks/', { params })
  return response.data
}

// GET /api/v1/tasks/{id}/
export async function getTask(id: string): Promise<Task> {
  const response = await apiClient.get(`/tasks/${id}/`)
  return response.data
}

// POST /api/v1/tasks/{id}/complete/
export async function completeTask(id: string): Promise<{
  detail: string
  next_task: Task | null
}> {
  const response = await apiClient.post(`/tasks/${id}/complete/`)
  return response.data
}

// POST /api/v1/tasks/{id}/skip/
export async function skipTask(id: string): Promise<{ detail: string }> {
  const response = await apiClient.post(`/tasks/${id}/skip/`)
  return response.data
}
