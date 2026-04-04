// ============================================================
// ГосДок — Страница задач
// Список задач с фильтром по статусу, complete/skip
// ============================================================

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { format } from 'date-fns'
import { ru } from 'date-fns/locale'
import { CheckSquare, Clock, FileText, SkipForward } from 'lucide-react'
import { Layout } from '@/components/layout/Layout'
import { Button } from '@/components/ui/Button'
import { TaskStatusBadge } from '@/components/ui/Badge'
import { Spinner } from '@/components/ui/Spinner'
import { useTasks, useCompleteTask, useSkipTask } from '@/hooks/useTasks'
import type { TaskStatus } from '@/types'

const STATUS_OPTIONS: { value: TaskStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'Все' },
  { value: 'in_progress', label: 'В работе' },
  { value: 'pending', label: 'Ожидают' },
  { value: 'done', label: 'Завершены' },
  { value: 'skipped', label: 'Пропущены' },
]

export default function Tasks() {
  const [statusFilter, setStatusFilter] = useState<TaskStatus | 'all'>('in_progress')

  const { data, isLoading } = useTasks(
    statusFilter !== 'all' ? { status: statusFilter } : undefined
  )

  const completeMutation = useCompleteTask()
  const skipMutation = useSkipTask()

  const tasks = data?.results ?? []

  return (
    <Layout title="Мои задачи">
      {/* Фильтр по статусу */}
      <div className="flex gap-2 flex-wrap mb-6">
        {STATUS_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => setStatusFilter(opt.value)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              statusFilter === opt.value
                ? 'bg-[#1F3864] text-white'
                : 'bg-white text-gray-600 border border-gray-200 hover:border-gray-300'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Список задач */}
      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : tasks.length === 0 ? (
        <div className="text-center py-16">
          <CheckSquare className="h-12 w-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500 font-medium">Нет задач</p>
        </div>
      ) : (
        <div className="space-y-3">
          {tasks.map((task) => (
            <div
              key={task.id}
              className="bg-white rounded-xl border border-gray-200 p-5"
            >
              <div className="flex flex-col sm:flex-row sm:items-start gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
                      Шаг {task.step_order}
                    </span>
                    <TaskStatusBadge status={task.status} />
                  </div>
                  <h3 className="font-semibold text-gray-900 mt-2">{task.title}</h3>

                  {task.document_title && (
                    <Link
                      to={`/documents/${task.document}`}
                      className="flex items-center gap-1.5 text-sm text-[#1F3864] hover:underline mt-1"
                    >
                      <FileText className="h-3.5 w-3.5" />
                      {task.document_title}
                    </Link>
                  )}

                  {task.due_date && (
                    <div className="flex items-center gap-1.5 text-sm text-gray-500 mt-2">
                      <Clock className="h-3.5 w-3.5" />
                      Срок: {format(new Date(task.due_date), 'd MMMM yyyy', { locale: ru })}
                    </div>
                  )}
                </div>

                {/* Кнопки действий */}
                {task.status === 'in_progress' && (
                  <div className="flex gap-2 flex-shrink-0">
                    <Button
                      size="sm"
                      onClick={() => completeMutation.mutate(task.id)}
                      isLoading={completeMutation.isPending}
                    >
                      <CheckSquare className="h-4 w-4" />
                      Завершить
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => skipMutation.mutate(task.id)}
                      isLoading={skipMutation.isPending}
                    >
                      <SkipForward className="h-4 w-4" />
                      Пропустить
                    </Button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </Layout>
  )
}
