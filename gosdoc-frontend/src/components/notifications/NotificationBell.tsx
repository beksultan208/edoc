// ============================================================
// ГосДок — Колокольчик уведомлений с дропдауном
// ============================================================

import { useState, useRef, useEffect } from 'react'
import { Bell } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { formatDistanceToNow } from 'date-fns'
import { ru } from 'date-fns/locale'
import { getNotifications, markAllNotificationsRead, markNotificationRead } from '@/api/notifications'
import { useNotificationStore } from '@/store/notificationStore'
import { clsx } from 'clsx'
import type { Notification } from '@/types'

// Иконки и цвета по типу уведомления
function notificationIcon(type: Notification['type']) {
  const map: Record<Notification['type'], string> = {
    task_assigned: '📋',
    step_completed: '✅',
    document_signed: '✍️',
    new_comment: '💬',
    deadline_approaching: '⏰',
    document_rejected: '❌',
  }
  return map[type] || '🔔'
}

export function NotificationBell() {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const queryClient = useQueryClient()
  const { unreadCount, setNotifications, markAllRead, markRead } = useNotificationStore()

  // Загружаем уведомления при монтировании и раз в 30 сек
  const { data } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => getNotifications({ page: 1 }),
    refetchInterval: 30_000,
    staleTime: 15_000,
  })

  // Синхронизируем со store при получении данных
  useEffect(() => {
    if (data?.results) {
      setNotifications(data.results)
    }
  }, [data, setNotifications])

  const markAllMutation = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: () => {
      markAllRead()
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })

  const markOneMutation = useMutation({
    mutationFn: markNotificationRead,
    onSuccess: (_, id) => {
      markRead(id)
    },
  })

  // Закрытие по клику вне
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const notifications = data?.results ?? []

  return (
    <div className="relative" ref={ref}>
      {/* Кнопка-колокольчик */}
      <button
        onClick={() => setOpen(!open)}
        className="relative p-2 text-gray-500 hover:text-[#1F3864] hover:bg-gray-100 rounded-lg transition-colors"
        aria-label="Уведомления"
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {/* Дропдаун */}
      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 sm:w-96 bg-white rounded-xl shadow-xl border border-gray-200 z-50 overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
            <h3 className="font-semibold text-gray-900">Уведомления</h3>
            {unreadCount > 0 && (
              <button
                onClick={() => markAllMutation.mutate()}
                className="text-xs text-[#1F3864] hover:underline"
              >
                Прочитать все
              </button>
            )}
          </div>

          {/* Список */}
          <div className="max-h-96 overflow-y-auto divide-y divide-gray-50">
            {notifications.length === 0 ? (
              <div className="px-4 py-8 text-center text-sm text-gray-400">
                Нет уведомлений
              </div>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  onClick={() => !n.is_read && markOneMutation.mutate(n.id)}
                  className={clsx(
                    'flex gap-3 px-4 py-3 cursor-pointer transition-colors',
                    n.is_read ? 'bg-white hover:bg-gray-50' : 'bg-blue-50 hover:bg-blue-100'
                  )}
                >
                  <span className="text-lg flex-shrink-0 mt-0.5">{notificationIcon(n.type)}</span>
                  <div className="flex-1 min-w-0">
                    <p className={clsx('text-sm font-medium truncate', !n.is_read && 'text-[#1F3864]')}>
                      {n.title}
                    </p>
                    {n.message && (
                      <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{n.message}</p>
                    )}
                    <p className="text-xs text-gray-400 mt-1">
                      {formatDistanceToNow(new Date(n.created_at), { addSuffix: true, locale: ru })}
                    </p>
                  </div>
                  {!n.is_read && (
                    <div className="w-2 h-2 rounded-full bg-[#1F3864] flex-shrink-0 mt-2" />
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
