// ============================================================
// ГосДок — Бейдж статуса
// ============================================================

import { clsx } from 'clsx'
import type { DocumentStatus, TaskStatus, WorkspaceStatus } from '@/types'

type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'info' | 'neutral'

interface BadgeProps {
  children: React.ReactNode
  variant?: BadgeVariant
  className?: string
}

const variantStyles: Record<BadgeVariant, string> = {
  default: 'bg-blue-100 text-blue-800',
  success: 'bg-green-100 text-green-800',
  warning: 'bg-yellow-100 text-yellow-800',
  danger: 'bg-red-100 text-red-800',
  info: 'bg-purple-100 text-purple-800',
  neutral: 'bg-gray-100 text-gray-700',
}

export function Badge({ children, variant = 'default', className }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        variantStyles[variant],
        className
      )}
    >
      {children}
    </span>
  )
}

// ---- Утилиты для статусов сущностей ----

export function DocumentStatusBadge({ status }: { status: DocumentStatus }) {
  const config: Record<DocumentStatus, { label: string; variant: BadgeVariant }> = {
    draft: { label: 'Черновик', variant: 'neutral' },
    review: { label: 'На согласовании', variant: 'warning' },
    signed: { label: 'Подписан', variant: 'success' },
    archived: { label: 'Архив', variant: 'info' },
  }
  const { label, variant } = config[status]
  return <Badge variant={variant}>{label}</Badge>
}

export function TaskStatusBadge({ status }: { status: TaskStatus }) {
  const config: Record<TaskStatus, { label: string; variant: BadgeVariant }> = {
    pending: { label: 'Ожидает', variant: 'neutral' },
    in_progress: { label: 'В работе', variant: 'warning' },
    done: { label: 'Завершена', variant: 'success' },
    skipped: { label: 'Пропущена', variant: 'info' },
  }
  const { label, variant } = config[status]
  return <Badge variant={variant}>{label}</Badge>
}

export function WorkspaceStatusBadge({ status }: { status: WorkspaceStatus }) {
  const config: Record<WorkspaceStatus, { label: string; variant: BadgeVariant }> = {
    active: { label: 'Активен', variant: 'success' },
    archived: { label: 'Архив', variant: 'neutral' },
    closed: { label: 'Закрыт', variant: 'danger' },
  }
  const { label, variant } = config[status]
  return <Badge variant={variant}>{label}</Badge>
}
