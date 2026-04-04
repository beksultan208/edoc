// ============================================================
// ГосДок — Хук аутентификации
// Загружает текущего пользователя при старте приложения
// ============================================================

import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getMe } from '@/api/users'
import { useAuthStore } from '@/store/authStore'
import { TOKEN_KEYS } from '@/api/client'

export function useAuth() {
  const { setUser, setLoading, user, isAuthenticated } = useAuthStore()

  const hasToken = !!localStorage.getItem(TOKEN_KEYS.access)

  const { data, isLoading, error } = useQuery({
    queryKey: ['me'],
    queryFn: getMe,
    enabled: hasToken,   // запрашиваем только если есть токен
    retry: false,
    staleTime: 5 * 60 * 1000,  // 5 минут
  })

  useEffect(() => {
    if (data) {
      setUser(data)
    }
  }, [data, setUser])

  useEffect(() => {
    if (error || !hasToken) {
      setUser(null)
    }
  }, [error, hasToken, setUser])

  useEffect(() => {
    if (!hasToken) {
      setLoading(false)
    }
  }, [hasToken, setLoading])

  return { user, isAuthenticated, isLoading: hasToken ? isLoading : false }
}
