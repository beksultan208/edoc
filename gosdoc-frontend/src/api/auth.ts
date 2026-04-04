// ============================================================
// ГосДок — API аутентификации (раздел 4.1 ТЗ)
// ============================================================

import apiClient, { TOKEN_KEYS } from './client'
import type { TokenPair, User } from '@/types'

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  full_name: string
  password: string
  password_confirm: string
  phone?: string
}

export interface ChangePasswordRequest {
  old_password: string
  new_password: string
}

export interface ResetPasswordRequest {
  email: string
}

// POST /api/v1/auth/login/
export async function login(data: LoginRequest): Promise<TokenPair & { user: User }> {
  const response = await apiClient.post('/auth/login/', data)
  const { access, refresh, user } = response.data

  localStorage.setItem(TOKEN_KEYS.access, access)
  localStorage.setItem(TOKEN_KEYS.refresh, refresh)

  return { access, refresh, user }
}

// POST /api/v1/auth/register/
export async function register(data: RegisterRequest): Promise<{ detail: string; email: string }> {
  const response = await apiClient.post('/auth/register/', data)
  return response.data
}

// POST /api/v1/auth/resend-code/ — повторная отправка кода
export async function resendCode(data: { email: string; purpose: 'registration' | 'password_reset' }): Promise<{ detail: string }> {
  const response = await apiClient.post('/auth/resend-code/', data)
  return response.data
}

// POST /api/v1/auth/verify-email/
export async function verifyEmail(data: { email: string; code: string }): Promise<{ detail: string; access: string; refresh: string; user: User }> {
  const response = await apiClient.post('/auth/verify-email/', data)
  return response.data
}

// POST /api/v1/auth/password/reset/confirm/
export async function resetPasswordConfirm(data: { email: string; code: string; new_password: string }): Promise<{ detail: string }> {
  const response = await apiClient.post('/auth/password/reset/confirm/', data)
  return response.data
}

// POST /api/v1/auth/logout/
export async function logout(): Promise<void> {
  const refresh = localStorage.getItem(TOKEN_KEYS.refresh)
  try {
    await apiClient.post('/auth/logout/', { refresh })
  } finally {
    localStorage.removeItem(TOKEN_KEYS.access)
    localStorage.removeItem(TOKEN_KEYS.refresh)
  }
}

// POST /api/v1/auth/password/change/
export async function changePassword(data: ChangePasswordRequest): Promise<void> {
  await apiClient.post('/auth/password/change/', data)
}

// POST /api/v1/auth/password/reset/
export async function resetPassword(data: ResetPasswordRequest): Promise<void> {
  await apiClient.post('/auth/password/reset/', data)
}
