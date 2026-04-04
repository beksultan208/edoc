// ============================================================
// ГосДок — Страница кабинетов (список, создание, участники)
// ============================================================

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { format } from 'date-fns'
import { ru } from 'date-fns/locale'
import { Plus, Users, FolderOpen, ArrowRight, Trash2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { Layout } from '@/components/layout/Layout'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Modal } from '@/components/ui/Modal'
import { WorkspaceStatusBadge } from '@/components/ui/Badge'
import { Spinner } from '@/components/ui/Spinner'
import {
  getWorkspaces,
  createWorkspace,
  getWorkspaceMembers,
  addWorkspaceMember,
  removeWorkspaceMember,
} from '@/api/workspaces'
import { getUsers } from '@/api/users'
import type { WorkspaceListItem, WorkspaceMemberRole } from '@/types'

// ---- Схема создания кабинета ----
const createSchema = z.object({
  title: z.string().min(1, 'Введите название'),
  type: z.enum(['individual', 'corporate']),
  description: z.string().optional(),
  deadline: z.string().optional(),
})
type CreateForm = z.infer<typeof createSchema>

// ---- Схема добавления участника ----
const memberSchema = z.object({
  user_id: z.string().uuid('Выберите пользователя'),
  role: z.enum(['owner', 'editor', 'signer', 'viewer']),
  step_order: z.coerce.number().int().positive().optional().or(z.literal('')),
})
type MemberForm = z.infer<typeof memberSchema>

export default function Workspaces() {
  const queryClient = useQueryClient()
  const [createOpen, setCreateOpen] = useState(false)
  const [membersOpen, setMembersOpen] = useState<string | null>(null)

  // Список кабинетов
  const { data, isLoading } = useQuery({
    queryKey: ['workspaces'],
    queryFn: () => getWorkspaces(),
  })

  // Участники выбранного кабинета
  const { data: members, isLoading: membersLoading } = useQuery({
    queryKey: ['workspace-members', membersOpen],
    queryFn: () => getWorkspaceMembers(membersOpen!),
    enabled: !!membersOpen,
  })

  // Список всех пользователей для добавления
  const { data: usersData } = useQuery({
    queryKey: ['users'],
    queryFn: () => getUsers(),
    enabled: !!membersOpen,
  })

  // Создать кабинет
  const createMutation = useMutation({
    mutationFn: createWorkspace,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspaces'] })
      setCreateOpen(false)
      createReset()
      toast.success('Кабинет создан')
    },
    onError: () => toast.error('Не удалось создать кабинет'),
  })

  // Добавить участника
  const addMemberMutation = useMutation({
    mutationFn: ({ workspaceId, data }: { workspaceId: string; data: MemberForm }) =>
      addWorkspaceMember(workspaceId, {
        user_id: data.user_id,
        role: data.role as WorkspaceMemberRole,
        step_order: data.step_order ? Number(data.step_order) : undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-members', membersOpen] })
      memberReset()
      toast.success('Участник добавлен')
    },
    onError: () => toast.error('Не удалось добавить участника'),
  })

  // Удалить участника
  const removeMemberMutation = useMutation({
    mutationFn: ({ workspaceId, userId }: { workspaceId: string; userId: string }) =>
      removeWorkspaceMember(workspaceId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-members', membersOpen] })
      toast.success('Участник удалён')
    },
    onError: () => toast.error('Не удалось удалить участника'),
  })

  const {
    register: createRegister,
    handleSubmit: createHandleSubmit,
    reset: createReset,
    formState: { errors: createErrors },
  } = useForm<CreateForm>({ resolver: zodResolver(createSchema) })

  const {
    register: memberRegister,
    handleSubmit: memberHandleSubmit,
    reset: memberReset,
    formState: { errors: memberErrors },
  } = useForm<MemberForm>({ resolver: zodResolver(memberSchema) })

  const workspaces = data?.results ?? []
  const userOptions = (usersData?.results ?? []).map((u) => ({
    value: u.id,
    label: `${u.full_name} (${u.email})`,
  }))

  const roleLabels: Record<WorkspaceMemberRole, string> = {
    owner: 'Владелец',
    editor: 'Редактор',
    signer: 'Подписант',
    viewer: 'Наблюдатель',
  }

  return (
    <Layout title="Рабочие кабинеты">
      {/* Кнопка создания */}
      <div className="flex justify-end mb-6">
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="h-4 w-4" />
          Создать кабинет
        </Button>
      </div>

      {/* Список кабинетов */}
      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : workspaces.length === 0 ? (
        <div className="text-center py-16">
          <FolderOpen className="h-12 w-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500 font-medium">Нет кабинетов</p>
          <p className="text-sm text-gray-400 mt-1">Создайте первый рабочий кабинет</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {workspaces.map((ws) => (
            <WorkspaceCard
              key={ws.id}
              workspace={ws}
              onManageMembers={() => setMembersOpen(ws.id)}
            />
          ))}
        </div>
      )}

      {/* Модал: создать кабинет */}
      <Modal
        isOpen={createOpen}
        onClose={() => { setCreateOpen(false); createReset() }}
        title="Создать кабинет"
        size="md"
        footer={
          <>
            <Button variant="secondary" onClick={() => setCreateOpen(false)}>Отмена</Button>
            <Button
              onClick={createHandleSubmit((d) => createMutation.mutate(d))}
              isLoading={createMutation.isPending}
            >
              Создать
            </Button>
          </>
        }
      >
        <form className="space-y-4">
          <Input
            label="Название"
            placeholder="Кабинет согласования договоров"
            required
            error={createErrors.title?.message}
            {...createRegister('title')}
          />
          <Select
            label="Тип"
            required
            options={[
              { value: 'individual', label: 'Индивидуальный (до 20 пользователей)' },
              { value: 'corporate', label: 'Корпоративный (неограниченно)' },
            ]}
            error={createErrors.type?.message}
            {...createRegister('type')}
          />
          <div>
            <label className="text-sm font-medium text-gray-700">Описание</label>
            <textarea
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1F3864]"
              rows={3}
              placeholder="Описание кабинета (необязательно)"
              {...createRegister('description')}
            />
          </div>
          <Input
            label="Срок (дедлайн)"
            type="date"
            error={createErrors.deadline?.message}
            {...createRegister('deadline')}
          />
        </form>
      </Modal>

      {/* Модал: управление участниками */}
      <Modal
        isOpen={!!membersOpen}
        onClose={() => setMembersOpen(null)}
        title="Участники кабинета"
        size="lg"
      >
        {/* Форма добавления */}
        <div className="mb-6 bg-gray-50 rounded-lg p-4">
          <p className="text-sm font-medium text-gray-700 mb-3">Добавить участника</p>
          <form
            onSubmit={memberHandleSubmit((d) =>
              membersOpen && addMemberMutation.mutate({ workspaceId: membersOpen, data: d })
            )}
            className="grid grid-cols-1 sm:grid-cols-2 gap-3"
          >
            <Select
              label="Пользователь"
              required
              options={[{ value: '', label: 'Выберите...' }, ...userOptions]}
              error={memberErrors.user_id?.message}
              {...memberRegister('user_id')}
            />
            <Select
              label="Роль"
              required
              options={[
                { value: 'editor', label: 'Редактор' },
                { value: 'signer', label: 'Подписант' },
                { value: 'viewer', label: 'Наблюдатель' },
                { value: 'owner', label: 'Владелец' },
              ]}
              error={memberErrors.role?.message}
              {...memberRegister('role')}
            />
            <Input
              label="Порядок шага (step_order)"
              type="number"
              min={1}
              placeholder="1, 2, 3..."
              hint="Пропустите, если участник не в workflow"
              error={memberErrors.step_order?.message}
              {...memberRegister('step_order')}
            />
            <div className="flex items-end">
              <Button type="submit" isLoading={addMemberMutation.isPending} className="w-full">
                Добавить
              </Button>
            </div>
          </form>
        </div>

        {/* Список участников */}
        {membersLoading ? (
          <div className="flex justify-center py-6"><Spinner /></div>
        ) : (
          <ul className="divide-y divide-gray-100">
            {(members ?? []).map((m) => (
              <li key={m.id} className="flex items-center gap-3 py-3">
                <div className="h-8 w-8 rounded-full bg-[#1F3864] flex items-center justify-center text-white text-sm font-semibold flex-shrink-0">
                  {m.user_name.charAt(0)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900">{m.user_name}</p>
                  <p className="text-xs text-gray-500">{m.user_email}</p>
                </div>
                <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
                  {roleLabels[m.role]}
                </span>
                {m.step_order && (
                  <span className="text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded-full">
                    шаг {m.step_order}
                  </span>
                )}
                <button
                  onClick={() =>
                    membersOpen &&
                    removeMemberMutation.mutate({ workspaceId: membersOpen, userId: m.user })
                  }
                  className="text-gray-400 hover:text-red-500 transition-colors p-1"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </Modal>
    </Layout>
  )
}

// ---- Карточка кабинета ----
function WorkspaceCard({
  workspace,
  onManageMembers,
}: {
  workspace: WorkspaceListItem
  onManageMembers: () => void
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 flex flex-col gap-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-semibold text-gray-900 line-clamp-2">{workspace.title}</h3>
        <WorkspaceStatusBadge status={workspace.status} />
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
          {workspace.type === 'individual' ? 'Индивидуальный' : 'Корпоративный'}
        </span>
        {workspace.user_role && (
          <span className="text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded-full">
            {workspace.user_role === 'owner' ? 'Владелец' :
             workspace.user_role === 'editor' ? 'Редактор' :
             workspace.user_role === 'signer' ? 'Подписант' : 'Наблюдатель'}
          </span>
        )}
      </div>

      {workspace.deadline && (
        <p className="text-xs text-gray-400">
          Срок: {format(new Date(workspace.deadline), 'd MMMM yyyy', { locale: ru })}
        </p>
      )}

      <div className="flex gap-2 mt-auto pt-2 border-t border-gray-100">
        <button
          onClick={onManageMembers}
          className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-[#1F3864] transition-colors"
        >
          <Users className="h-3.5 w-3.5" />
          Участники
        </button>
        <Link
          to={`/documents?workspace=${workspace.id}`}
          className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-[#1F3864] transition-colors ml-auto"
        >
          Документы <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    </div>
  )
}
