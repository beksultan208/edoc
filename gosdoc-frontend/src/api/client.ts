// ============================================================
// ГосДок — Axios instance с JWT interceptor
// Автоматический refresh токена при 401
// ============================================================

import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'

const BASE_URL = '/api/v1'

// Ключи хранения токенов в localStorage
export const TOKEN_KEYS = {
  access: 'gosdoc_access_token',
  refresh: 'gosdoc_refresh_token',
}

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30_000,
})

// ---- Request interceptor: добавляем Authorization header ----
// Не отправляем токен на публичные auth-эндпоинты (register, login, verify-email и т.д.)
const PUBLIC_AUTH_PATHS = ['/auth/register/', '/auth/login/', '/auth/verify-email/', '/auth/resend-code/', '/auth/password/reset/', '/auth/password/reset/confirm/']

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const isPublicAuth = PUBLIC_AUTH_PATHS.some((p) => config.url?.includes(p))
  const token = localStorage.getItem(TOKEN_KEYS.access)
  if (token && config.headers && !isPublicAuth) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ---- Response interceptor: при 401 пробуем обновить токен ----
let isRefreshing = false
// Очередь запросов, ожидающих обновления токена
let failedQueue: Array<{
  resolve: (token: string) => void
  reject: (error: unknown) => void
}> = []

function processQueue(error: unknown, token: string | null = null) {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error)
    } else {
      resolve(token!)
    }
  })
  failedQueue = []
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error)
    }

    // Не пытаемся рефрешить сам запрос на рефреш (избегаем бесконечного цикла)
    if (originalRequest.url?.includes('/auth/refresh/')) {
      // Refresh провалился — разлогиниваем
      localStorage.removeItem(TOKEN_KEYS.access)
      localStorage.removeItem(TOKEN_KEYS.refresh)
      window.location.href = '/login'
      return Promise.reject(error)
    }

    if (isRefreshing) {
      // Ставим запрос в очередь до окончания рефреша
      return new Promise<string>((resolve, reject) => {
        failedQueue.push({ resolve, reject })
      }).then((token) => {
        originalRequest.headers.Authorization = `Bearer ${token}`
        return apiClient(originalRequest)
      })
    }

    originalRequest._retry = true
    isRefreshing = true

    const refreshToken = localStorage.getItem(TOKEN_KEYS.refresh)

    if (!refreshToken) {
      isRefreshing = false
      window.location.href = '/login'
      return Promise.reject(error)
    }

    try {
      const { data } = await axios.post(`${BASE_URL}/auth/refresh/`, {
        refresh: refreshToken,
      })

      const newAccessToken: string = data.access
      localStorage.setItem(TOKEN_KEYS.access, newAccessToken)
      // Если backend вернул новый refresh (ROTATE_REFRESH_TOKENS=True)
      if (data.refresh) {
        localStorage.setItem(TOKEN_KEYS.refresh, data.refresh)
      }

      apiClient.defaults.headers.common.Authorization = `Bearer ${newAccessToken}`
      originalRequest.headers.Authorization = `Bearer ${newAccessToken}`

      processQueue(null, newAccessToken)
      return apiClient(originalRequest)
    } catch (refreshError) {
      processQueue(refreshError, null)
      localStorage.removeItem(TOKEN_KEYS.access)
      localStorage.removeItem(TOKEN_KEYS.refresh)
      window.location.href = '/login'
      return Promise.reject(refreshError)
    } finally {
      isRefreshing = false
    }
  }
)

export default apiClient
