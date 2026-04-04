// ============================================================
// ГосДок — Главная страница (Dashboard)
// Последние документы, мои задачи, статистика
// ============================================================

import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { format } from 'date-fns'
import { ru } from 'date-fns/locale'
import { FileText, CheckSquare, FolderOpen, Clock, ArrowRight } from 'lucide-react'
import { Layout } from '@/components/layout/Layout'
import { DocumentStatusBadge, TaskStatusBadge } from '@/components/ui/Badge'
import { Spinner } from '@/components/ui/Spinner'
import { useAuthStore } from '@/store/authStore'
import { getDocuments } from '@/api/documents'
import { getTasks } from '@/api/tasks'
import { getWorkspaces } from '@/api/workspaces'

// Карточка статистики
function StatCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ElementType
  label: string
  value: number | string
  color: string
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 flex items-center gap-4">
      <div className={`p-3 rounded-xl ${color}`}>
        <Icon className="h-6 w-6 text-white" />
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
        <p className="text-sm text-gray-500">{label}</p>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { user } = useAuthStore()

  const { data: docsData, isLoading: docsLoading } = useQuery({
    queryKey: ['documents', { page: 1 }],
    queryFn: () => getDocuments({ page: 1 }),
  })

  const { data: tasksData, isLoading: tasksLoading } = useQuery({
    queryKey: ['tasks', { status: 'in_progress' }],
    queryFn: () => getTasks({ status: 'in_progress' }),
  })

  const { data: workspacesData } = useQuery({
    queryKey: ['workspaces'],
    queryFn: () => getWorkspaces(),
  })

  const recentDocs = docsData?.results?.slice(0, 5) ?? []
  const activeTasks = tasksData?.results?.slice(0, 5) ?? []

  return (
    <Layout title="Главная">
      {/* Приветствие */}
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-900">
          Добро пожаловать, {user?.full_name?.split(' ')[0]}!
        </h2>
        <p className="text-sm text-gray-500 mt-1">
          {format(new Date(), "EEEE, d MMMM yyyy", { locale: ru })}
        </p>
      </div>

      {/* Статистика */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        <StatCard
          icon={FileText}
          label="Всего документов"
          value={docsData?.count ?? '—'}
          color="bg-[#1F3864]"
        />
        <StatCard
          icon={CheckSquare}
          label="Активных задач"
          value={tasksData?.count ?? '—'}
          color="bg-amber-500"
        />
        <StatCard
          icon={FolderOpen}
          label="Кабинетов"
          value={workspacesData?.count ?? '—'}
          color="bg-emerald-600"
        />
      </div>

      {/* Основная сетка */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Последние документы */}
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
            <h3 className="font-semibold text-gray-900">Последние документы</h3>
            <Link to="/documents" className="text-sm text-[#1F3864] hover:underline flex items-center gap-1">
              Все <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          {docsLoading ? (
            <div className="flex justify-center py-8"><Spinner /></div>
          ) : recentDocs.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">Документов нет</p>
          ) : (
            <ul className="divide-y divide-gray-50">
              {recentDocs.map((doc) => (
                <li key={doc.id}>
                  <Link
                    to={`/documents/${doc.id}`}
                    className="flex items-center gap-3 px-5 py-3.5 hover:bg-gray-50 transition-colors"
                  >
                    <FileText className="h-4 w-4 text-gray-400 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{doc.title}</p>
                      <p className="text-xs text-gray-400 mt-0.5">
                        {format(new Date(doc.updated_at), 'd MMM yyyy', { locale: ru })}
                      </p>
                    </div>
                    <DocumentStatusBadge status={doc.status} />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Мои активные задачи */}
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
            <h3 className="font-semibold text-gray-900">Мои задачи</h3>
            <Link to="/tasks" className="text-sm text-[#1F3864] hover:underline flex items-center gap-1">
              Все <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          {tasksLoading ? (
            <div className="flex justify-center py-8"><Spinner /></div>
          ) : activeTasks.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">Нет активных задач</p>
          ) : (
            <ul className="divide-y divide-gray-50">
              {activeTasks.map((task) => (
                <li key={task.id} className="px-5 py-3.5">
                  <div className="flex items-start gap-3">
                    <CheckSquare className="h-4 w-4 text-gray-400 flex-shrink-0 mt-0.5" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{task.title}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <TaskStatusBadge status={task.status} />
                        {task.due_date && (
                          <span className="flex items-center gap-1 text-xs text-gray-400">
                            <Clock className="h-3 w-3" />
                            до {format(new Date(task.due_date), 'd MMM', { locale: ru })}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </Layout>
  )
}
