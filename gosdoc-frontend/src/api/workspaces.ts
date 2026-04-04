// ============================================================
// ГосДок — API рабочих кабинетов (раздел 4.4 ТЗ)
// ============================================================

import apiClient from './client'
import type {
  PaginatedResponse,
  Workspace,
  WorkspaceListItem,
  WorkspaceMember,
  WorkspaceMemberRole,
  WorkspaceStatus,
  WorkspaceType,
} from '@/types'

// ---- Кабинеты ----

export interface CreateWorkspaceData {
  title: string
  type: WorkspaceType
  organization?: string
  description?: string
  deadline?: string
}

export interface UpdateWorkspaceData {
  title?: string
  description?: string
  deadline?: string
  status?: WorkspaceStatus
}

// GET /api/v1/workspaces/
export async function getWorkspaces(params?: {
  status?: WorkspaceStatus
  type?: WorkspaceType
  page?: number
}): Promise<PaginatedResponse<WorkspaceListItem>> {
  const response = await apiClient.get('/workspaces/', { params })
  return response.data
}

// POST /api/v1/workspaces/
export async function createWorkspace(data: CreateWorkspaceData): Promise<Workspace> {
  const response = await apiClient.post('/workspaces/', data)
  return response.data
}

// GET /api/v1/workspaces/{id}/
export async function getWorkspace(id: string): Promise<Workspace> {
  const response = await apiClient.get(`/workspaces/${id}/`)
  return response.data
}

// PATCH /api/v1/workspaces/{id}/
export async function updateWorkspace(id: string, data: UpdateWorkspaceData): Promise<Workspace> {
  const response = await apiClient.patch(`/workspaces/${id}/`, data)
  return response.data
}

// DELETE /api/v1/workspaces/{id}/
export async function deleteWorkspace(id: string): Promise<void> {
  await apiClient.delete(`/workspaces/${id}/`)
}

// ---- Участники ----

export interface AddMemberData {
  user_id: string
  role: WorkspaceMemberRole
  step_order?: number | null
}

export interface UpdateMemberData {
  role?: WorkspaceMemberRole
  step_order?: number | null
}

// GET /api/v1/workspaces/{id}/members/
export async function getWorkspaceMembers(workspaceId: string): Promise<WorkspaceMember[]> {
  const response = await apiClient.get(`/workspaces/${workspaceId}/members/`)
  return response.data
}

// POST /api/v1/workspaces/{id}/members/
export async function addWorkspaceMember(
  workspaceId: string,
  data: AddMemberData
): Promise<WorkspaceMember> {
  const response = await apiClient.post(`/workspaces/${workspaceId}/members/`, data)
  return response.data
}

// PATCH /api/v1/workspaces/{id}/members/{uid}/
export async function updateWorkspaceMember(
  workspaceId: string,
  userId: string,
  data: UpdateMemberData
): Promise<WorkspaceMember> {
  const response = await apiClient.patch(`/workspaces/${workspaceId}/members/${userId}/`, data)
  return response.data
}

// DELETE /api/v1/workspaces/{id}/members/{uid}/
export async function removeWorkspaceMember(workspaceId: string, userId: string): Promise<void> {
  await apiClient.delete(`/workspaces/${workspaceId}/members/${userId}/`)
}
