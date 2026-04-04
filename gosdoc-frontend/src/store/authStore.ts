// ============================================================
// ГосДок — Zustand store аутентификации
// ============================================================

import { create } from 'zustand'
import { TOKEN_KEYS } from '@/api/client'
import type { User } from '@/types'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean

  setUser: (user: User | null) => void
  setLoading: (loading: boolean) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  // Считаем пользователя аутентифицированным, если есть access-токен
  user: null,
  isAuthenticated: !!localStorage.getItem(TOKEN_KEYS.access),
  isLoading: true,

  setUser: (user) =>
    set({
      user,
      isAuthenticated: !!user,
      isLoading: false,
    }),

  setLoading: (isLoading) => set({ isLoading }),

  logout: () => {
    localStorage.removeItem(TOKEN_KEYS.access)
    localStorage.removeItem(TOKEN_KEYS.refresh)
    set({ user: null, isAuthenticated: false, isLoading: false })
  },
}))
