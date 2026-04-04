// ============================================================
// ГосДок — Просмотр документа
// Детали, версии, AI-diff, комментарии, подписи, workflow
// ============================================================

import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { format } from 'date-fns'
import { ru } from 'date-fns/locale'
import {
  Download, Play, PenLine, MessageSquare, History,
  Sparkles, CheckCircle, AlertCircle, ChevronDown, ChevronUp, Plus,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { Layout } from '@/components/layout/Layout'
import { Button } from '@/components/ui/Button'
import { DocumentStatusBadge } from '@/components/ui/Badge'
import { Spinner } from '@/components/ui/Spinner'
import { SignatureCanvas } from '@/components/signatures/SignatureCanvas'
import {
  getDocument,
  getDocumentVersions,
  getDocumentSignatures,
  getComments,
  createComment,
  resolveComment,
  getDocumentDownloadUrl,
  getVersionDiff,
} from '@/api/documents'
import { useStartWorkflow, useUploadVersion } from '@/hooks/useDocuments'
import type { Comment } from '@/types'

export default function DocumentView() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [signOpen, setSignOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<'info' | 'versions' | 'comments' | 'signatures'>('info')
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null)

  const { data: document, isLoading } = useQuery({
    queryKey: ['document', id],
    queryFn: () => getDocument(id!),
    enabled: !!id,
  })

  const { data: versions } = useQuery({
    queryKey: ['document-versions', id],
    queryFn: () => getDocumentVersions(id!),
    enabled: !!id && activeTab === 'versions',
  })

  const { data: signatures } = useQuery({
    queryKey: ['document-signatures', id],
    queryFn: () => getDocumentSignatures(id!),
    enabled: !!id && activeTab === 'signatures',
  })

  const { data: comments } = useQuery({
    queryKey: ['document-comments', id],
    queryFn: () => getComments(id!),
    enabled: !!id && activeTab === 'comments',
  })

  const { data: diffData } = useQuery({
    queryKey: ['version-diff', id, selectedVersionId],
    queryFn: () => getVersionDiff(id!, selectedVersionId!),
    enabled: !!selectedVersionId,
  })

  const startWorkflow = useStartWorkflow(id!)
  const uploadVersion = useUploadVersion(id!)

  const downloadMutation = useMutation({
    mutationFn: () => getDocumentDownloadUrl(id!),
    onSuccess: ({ download_url }) => {
      window.open(download_url, '_blank')
    },
    onError: () => toast.error('Не удалось получить ссылку для скачивания'),
  })

  if (isLoading) {
    return (
      <Layout>
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      </Layout>
    )
  }

  if (!document) {
    return (
      <Layout>
        <div className="text-center py-16">
          <p className="text-gray-500">Документ не найден</p>
          <Button variant="ghost" className="mt-4" onClick={() => navigate('/documents')}>
            Назад к списку
          </Button>
        </div>
      </Layout>
    )
  }

  const isLocked = document.status === 'signed' || document.status === 'archived'

  const tabs = [
    { id: 'info', label: 'Информация' },
    { id: 'versions', label: 'Версии' },
    { id: 'comments', label: 'Комментарии' },
    { id: 'signatures', label: 'Подписи' },
  ] as const

  return (
    <Layout>
      {/* Breadcrumb */}
      <button
        onClick={() => navigate(-1)}
        className="text-sm text-gray-500 hover:text-gray-700 mb-4 flex items-center gap-1"
      >
        ← Назад
      </button>

      {/* Заголовок */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <div className="flex flex-col sm:flex-row sm:items-start gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-xl font-bold text-gray-900">{document.title}</h1>
              <DocumentStatusBadge status={document.status} />
            </div>
            <div className="flex flex-wrap gap-4 mt-2 text-sm text-gray-500">
              <span>Тип: <strong className="text-gray-700 uppercase">{document.file_type}</strong></span>
              <span>Версий: <strong className="text-gray-700">{document.current_version_number ?? 1}</strong></span>
              <span>Обновлён: <strong className="text-gray-700">{format(new Date(document.updated_at), 'd MMM yyyy', { locale: ru })}</strong></span>
            </div>
          </div>

          {/* Кнопки действий */}
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => downloadMutation.mutate()}
              isLoading={downloadMutation.isPending}
            >
              <Download className="h-4 w-4" />
              Скачать
            </Button>

            {document.status === 'draft' && (
              <Button size="sm" onClick={() => startWorkflow.mutate()} isLoading={startWorkflow.isPending}>
                <Play className="h-4 w-4" />
                Запустить workflow
              </Button>
            )}

            {!isLocked && (
              <>
                <Button variant="secondary" size="sm" asChild>
                  <label className="cursor-pointer">
                    <Plus className="h-4 w-4" />
                    Новая версия
                    <input
                      type="file"
                      className="hidden"
                      accept=".pdf,.docx,.xlsx,.odt,.ods"
                      onChange={(e) => {
                        const file = e.target.files?.[0]
                        if (file) uploadVersion.mutate({ file })
                        e.target.value = ''
                      }}
                    />
                  </label>
                </Button>

                <Button
                  size="sm"
                  variant="primary"
                  onClick={() => setSignOpen(true)}
                >
                  <PenLine className="h-4 w-4" />
                  Подписать
                </Button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Табы */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-[#1F3864] text-[#1F3864]'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Содержимое вкладок */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">

        {/* Информация */}
        {activeTab === 'info' && (
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[
              { label: 'Статус', value: <DocumentStatusBadge status={document.status} /> },
              { label: 'Тип файла', value: document.file_type.toUpperCase() },
              { label: 'Загружен', value: format(new Date(document.created_at), 'd MMMM yyyy, HH:mm', { locale: ru }) },
              { label: 'Обновлён', value: format(new Date(document.updated_at), 'd MMMM yyyy, HH:mm', { locale: ru }) },
            ].map(({ label, value }) => (
              <div key={label}>
                <dt className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</dt>
                <dd className="mt-1 text-sm text-gray-900">{value}</dd>
              </div>
            ))}
          </dl>
        )}

        {/* Версии */}
        {activeTab === 'versions' && (
          <div className="space-y-3">
            {!versions ? (
              <div className="flex justify-center py-8"><Spinner /></div>
            ) : versions.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-8">Нет версий</p>
            ) : (
              versions.map((v) => (
                <div key={v.id} className="border border-gray-200 rounded-lg overflow-hidden">
                  <button
                    onClick={() =>
                      setSelectedVersionId(selectedVersionId === v.id ? null : v.id)
                    }
                    className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <span className="font-medium text-sm">Версия {v.version_number}</span>
                      {v.ai_changes_detected && (
                        <span className="flex items-center gap-1 text-xs text-purple-600 bg-purple-50 px-2 py-0.5 rounded-full">
                          <Sparkles className="h-3 w-3" />
                          AI-изменения
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 text-sm text-gray-500">
                      <span>{format(new Date(v.created_at), 'd MMM yyyy', { locale: ru })}</span>
                      {selectedVersionId === v.id ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </div>
                  </button>

                  {/* AI-diff */}
                  {selectedVersionId === v.id && v.version_number > 1 && (
                    <div className="border-t border-gray-100 px-4 py-4 bg-purple-50">
                      {!diffData ? (
                        <div className="flex justify-center py-4"><Spinner size="sm" /></div>
                      ) : (
                        <div className="space-y-2">
                          <div className="flex items-center gap-2">
                            <Sparkles className="h-4 w-4 text-purple-600" />
                            <span className="text-sm font-medium text-purple-800">AI-анализ изменений</span>
                          </div>
                          {diffData.ai_diff_summary?.summary ? (
                            <p className="text-sm text-gray-700">{diffData.ai_diff_summary.summary}</p>
                          ) : (
                            <p className="text-sm text-gray-400">Анализ ещё выполняется...</p>
                          )}
                          <div className="flex gap-4 text-xs text-gray-500 mt-2">
                            <span className="text-green-600">+{diffData.ai_diff_summary?.additions_count ?? 0} строк добавлено</span>
                            <span className="text-red-600">-{diffData.ai_diff_summary?.deletions_count ?? 0} строк удалено</span>
                          </div>
                          <p className="text-xs text-gray-400">SHA-256: {v.checksum}</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {/* Комментарии */}
        {activeTab === 'comments' && (
          <CommentSection documentId={id!} comments={comments ?? []} queryClient={queryClient} />
        )}

        {/* Подписи */}
        {activeTab === 'signatures' && (
          <div className="space-y-3">
            {!signatures ? (
              <div className="flex justify-center py-8"><Spinner /></div>
            ) : signatures.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-8">Подписей нет</p>
            ) : (
              signatures.map((sig) => (
                <div key={sig.id} className="flex items-center gap-4 p-4 border border-gray-200 rounded-lg">
                  <div className="h-10 w-10 rounded-full bg-[#1F3864] flex items-center justify-center text-white font-semibold flex-shrink-0">
                    {sig.user_name?.charAt(0) ?? '?'}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">{sig.user_name}</p>
                    <p className="text-xs text-gray-500">
                      {format(new Date(sig.signed_at), 'd MMMM yyyy, HH:mm', { locale: ru })}
                      {' · '}IP: {sig.ip_address}
                    </p>
                  </div>
                  {sig.is_valid ? (
                    <div className="flex items-center gap-1 text-green-600 text-xs">
                      <CheckCircle className="h-4 w-4" />
                      Действительна
                    </div>
                  ) : (
                    <div className="flex items-center gap-1 text-red-500 text-xs">
                      <AlertCircle className="h-4 w-4" />
                      Недействительна
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Модал подписи */}
      <SignatureCanvas
        documentId={id!}
        isOpen={signOpen}
        onClose={() => setSignOpen(false)}
        onSigned={() => queryClient.invalidateQueries({ queryKey: ['document', id] })}
      />
    </Layout>
  )
}

// ---- Секция комментариев ----
function CommentSection({
  documentId,
  comments,
  queryClient,
}: {
  documentId: string
  comments: Comment[]
  queryClient: ReturnType<typeof useQueryClient>
}) {
  const [replyTo, setReplyTo] = useState<string | null>(null)
  const { register, handleSubmit, reset } = useForm<{ content: string; parent?: string }>()

  const createMutation = useMutation({
    mutationFn: (data: { content: string; parent?: string }) =>
      createComment(documentId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['document-comments', documentId] })
      reset()
      setReplyTo(null)
      toast.success('Комментарий добавлен')
    },
  })

  const resolveMutation = useMutation({
    mutationFn: resolveComment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['document-comments', documentId] })
    },
  })

  return (
    <div className="space-y-4">
      {/* Форма нового комментария */}
      <form
        onSubmit={handleSubmit((d) =>
          createMutation.mutate({ content: d.content, parent: replyTo ?? undefined })
        )}
        className="flex gap-3"
      >
        <div className="flex-1">
          <textarea
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-[#1F3864]"
            rows={2}
            placeholder={replyTo ? 'Ответить на комментарий...' : 'Написать комментарий...'}
            {...register('content', { required: true })}
          />
          {replyTo && (
            <button
              type="button"
              onClick={() => setReplyTo(null)}
              className="text-xs text-gray-400 hover:text-gray-600 mt-1"
            >
              ✕ Отменить ответ
            </button>
          )}
        </div>
        <Button type="submit" size="sm" isLoading={createMutation.isPending}>
          <MessageSquare className="h-4 w-4" />
        </Button>
      </form>

      {/* Список комментариев */}
      {comments.length === 0 ? (
        <p className="text-sm text-gray-400 text-center py-6">Комментариев нет</p>
      ) : (
        <ul className="space-y-3">
          {comments.map((comment) => (
            <CommentItem
              key={comment.id}
              comment={comment}
              onReply={() => setReplyTo(comment.id)}
              onResolve={() => resolveMutation.mutate(comment.id)}
            />
          ))}
        </ul>
      )}
    </div>
  )
}

function CommentItem({
  comment,
  onReply,
  onResolve,
}: {
  comment: Comment
  onReply: () => void
  onResolve: () => void
}) {
  return (
    <li className={`rounded-lg border p-4 ${comment.is_resolved ? 'border-gray-100 bg-gray-50 opacity-70' : 'border-gray-200 bg-white'}`}>
      <div className="flex items-start gap-3">
        <div className="h-7 w-7 rounded-full bg-[#1F3864] flex items-center justify-center text-white text-xs font-semibold flex-shrink-0">
          {comment.author_name?.charAt(0) ?? '?'}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-900">{comment.author_name}</span>
            <span className="text-xs text-gray-400">
              {format(new Date(comment.created_at), 'd MMM, HH:mm', { locale: ru })}
            </span>
            {comment.is_resolved && (
              <span className="text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded-full">Закрыт</span>
            )}
          </div>
          <p className="text-sm text-gray-700 mt-1">{comment.content}</p>

          {!comment.is_resolved && (
            <div className="flex gap-3 mt-2">
              <button onClick={onReply} className="text-xs text-gray-400 hover:text-[#1F3864]">
                Ответить
              </button>
              <button onClick={onResolve} className="text-xs text-gray-400 hover:text-green-600">
                Закрыть
              </button>
            </div>
          )}

          {/* Ответы */}
          {comment.replies && comment.replies.length > 0 && (
            <ul className="mt-3 space-y-2 pl-4 border-l-2 border-gray-100">
              {comment.replies.map((reply) => (
                <li key={reply.id} className="text-sm">
                  <span className="font-medium text-gray-700">{reply.author_name}: </span>
                  <span className="text-gray-600">{reply.content}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </li>
  )
}
