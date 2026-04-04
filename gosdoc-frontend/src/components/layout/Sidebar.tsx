// ============================================================
// ГосДок — Боковая навигация
// ============================================================

import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  FolderOpen,
  FileText,
  CheckSquare,
  BarChart2,
  LogOut,
  X,
} from 'lucide-react'
import { clsx } from 'clsx'
import { useMutation } from '@tanstack/react-query'
import { logout } from '@/api/auth'
import { useAuthStore } from '@/store/authStore'
import toast from 'react-hot-toast'

const NAV_ITEMS = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Главная' },
  { to: '/workspaces', icon: FolderOpen, label: 'Кабинеты' },
  { to: '/documents', icon: FileText, label: 'Документы' },
  { to: '/tasks', icon: CheckSquare, label: 'Задачи' },
  { to: '/reports', icon: BarChart2, label: 'Отчёты' },
]

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const navigate = useNavigate()
  const { user, logout: storeLogout } = useAuthStore()

  const logoutMutation = useMutation({
    mutationFn: logout,
    onSuccess: () => {
      storeLogout()
      navigate('/login')
    },
    onError: () => {
      // Даже при ошибке — разлогиниваем локально
      storeLogout()
      navigate('/login')
      toast.error('Ошибка при выходе')
    },
  })

  return (
    <>
      {/* Overlay для мобильных */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/30 z-20 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          'fixed top-0 left-0 h-full w-64 bg-[#1F3864] text-white flex flex-col z-30',
          'transition-transform duration-300 ease-in-out',
          'lg:translate-x-0 lg:static lg:z-auto',
          isOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Логотип */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-white/10">
          <div>
            <h1 className="text-xl font-bold tracking-wide">ГосДок</h1>
            <p className="text-xs text-blue-200 mt-0.5">Документооборот</p>
          </div>
          <button onClick={onClose} className="lg:hidden text-white/60 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Навигация */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              onClick={onClose}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-white/20 text-white'
                    : 'text-blue-100 hover:bg-white/10 hover:text-white'
                )
              }
            >
              <Icon className="h-5 w-5 flex-shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Профиль + выход */}
        <div className="px-3 py-4 border-t border-white/10">
          {user && (
            <div className="px-4 py-2 mb-2">
              <p className="text-sm font-medium text-white truncate">{user.full_name}</p>
              <p className="text-xs text-blue-200 truncate">{user.email}</p>
            </div>
          )}
          <button
            onClick={() => logoutMutation.mutate()}
            disabled={logoutMutation.isPending}
            className="flex items-center gap-3 w-full px-4 py-2.5 rounded-lg text-sm font-medium text-blue-100 hover:bg-white/10 hover:text-white transition-colors"
          >
            <LogOut className="h-5 w-5" />
            Выйти
          </button>
        </div>
      </aside>
    </>
  )
}
