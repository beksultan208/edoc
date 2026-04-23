// ============================================================
// ГосДок — Страница общего AI ассистента
// ============================================================

import { useQuery } from '@tanstack/react-query'
import { Layout } from '@/components/layout/Layout'
import { GeneralChat } from '@/components/ai/GeneralChat'
import { Spinner } from '@/components/ui/Spinner'
import { getWorkspaces } from '@/api/workspaces'
import { useState } from 'react'

export default function AIChat() {
  const { data, isLoading } = useQuery({
    queryKey: ['workspaces'],
    queryFn: () => getWorkspaces(),
  })

  const workspaces = data?.results ?? []
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const workspaceId = selectedId ?? workspaces[0]?.id

  if (isLoading) {
    return (
      <Layout>
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      </Layout>
    )
  }

  if (!workspaceId) {
    return (
      <Layout>
        <div className="text-center py-16">
          <p className="text-gray-500">Нет доступных кабинетов. Создайте кабинет для использования AI ассистента.</p>
        </div>
      </Layout>
    )
  }

  return (
    <Layout noPadding>
      <div className="flex flex-col h-[calc(100vh-64px)]">
        {/* Селектор кабинета (если несколько) */}
        {workspaces.length > 1 && (
          <div className="bg-white border-b border-gray-200 px-6 py-2 flex items-center gap-3 flex-shrink-0">
            <label className="text-xs text-gray-500">Кабинет:</label>
            <select
              value={workspaceId}
              onChange={(e) => setSelectedId(e.target.value)}
              className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-[#1F3864]"
            >
              {workspaces.map((ws) => (
                <option key={ws.id} value={ws.id}>{ws.title}</option>
              ))}
            </select>
          </div>
        )}

        <GeneralChat workspaceId={workspaceId} />
      </div>
    </Layout>
  )
}
