// ============================================================
// ГосДок — API пользователей (раздел 4.2 ТЗ)
// ============================================================

import apiClient from './client'
import type { PaginatedResponse, User } from '@/types'

// GET /api/v1/users/me/
export async function getMe(): Promise<User> {
  const response = await apiClient.get('/users/me/')
  return response.data
}

// GET /api/v1/users/
export async function getUsers(params?: { page?: number }): Promise<PaginatedResponse<User>> {
  const response = await apiClient.get('/users/', { params })
  return response.data
}

// GET /api/v1/users/{id}/
export async function getUser(id: string): Promise<User> {
  const response = await apiClient.get(`/users/${id}/`)
  return response.data
}

// PATCH /api/v1/users/{id}/
export async function updateUser(
  id: string,
  data: Partial<Pick<User, 'full_name' | 'phone'>>
): Promise<User> {
  const response = await apiClient.patch(`/users/${id}/`, data)
  return response.data
}
