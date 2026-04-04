// ============================================================
// ГосДок — Верхняя шапка
// ============================================================

import { Menu } from 'lucide-react'
import { NotificationBell } from '@/components/notifications/NotificationBell'
import { useAuthStore } from '@/store/authStore'

interface HeaderProps {
  onMenuClick: () => void
  title?: string
}

export function Header({ onMenuClick, title }: HeaderProps) {
  const { user } = useAuthStore()

  return (
    <header className="sticky top-0 z-10 bg-white border-b border-gray-200 px-4 sm:px-6 py-3">
      <div className="flex items-center gap-4">
        {/* Бургер для мобильных */}
        <button
          onClick={onMenuClick}
          className="lg:hidden text-gray-500 hover:text-gray-700 p-1 rounded-md"
        >
          <Menu className="h-6 w-6" />
        </button>

        {/* Заголовок страницы */}
        {title && (
          <h1 className="text-lg font-semibold text-gray-900 flex-1">{title}</h1>
        )}

        {/* Правая часть */}
        <div className="ml-auto flex items-center gap-3">
          <NotificationBell />

          {/* Аватар пользователя */}
          {user && (
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-full bg-[#1F3864] flex items-center justify-center text-white text-sm font-semibold flex-shrink-0">
                {user.full_name.charAt(0).toUpperCase()}
              </div>
              <span className="hidden sm:block text-sm font-medium text-gray-700 max-w-[120px] truncate">
                {user.full_name}
              </span>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
