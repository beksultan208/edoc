// ============================================================
// ГосДок — Список документов с загрузкой нового
// ============================================================

import { useState, useRef } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { format } from 'date-fns'
import { ru } from 'date-fns/locale'
import { FileText, Plus, Upload, ArrowRight } from 'lucide-react'
import { Layout } from '@/components/layout/Layout'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Modal } from '@/components/ui/Modal'
import { DocumentStatusBadge } from '@/components/ui/Badge'
import { Spinner } from '@/components/ui/Spinner'
import { getDocuments } from '@/api/documents'
import { getWorkspaces } from '@/api/workspaces'
import { useUploadDocument } from '@/hooks/useDocuments'
import type { DocumentStatus } from '@/types'

const uploadSchema = z.object({
  title: z.string().min(1, 'Введите название документа'),
  workspace: z.string().min(1, 'Выберите кабинет'),
})
type UploadForm = z.infer<typeof uploadSchema>

const STATUS_FILTERS: { value: DocumentStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'Все' },
  { value: 'draft', label: 'Черновики' },
  { value: 'review', label: 'На согласовании' },
  { value: 'signed', label: 'Подписаны' },
  { value: 'archived', label: 'Архив' },
]

export default function Documents() {
  const [searchParams] = useSearchParams()
  const workspaceParam = searchParams.get('workspace')
  const [statusFilter, setStatusFilter] = useState<DocumentStatus | 'all'>('all')
  const [uploadOpen, setUploadOpen] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  const fileRef = useRef<HTMLInputElement>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['documents', { status: statusFilter !== 'all' ? statusFilter : undefined, workspace: workspaceParam ?? undefined }],
    queryFn: () => getDocuments({
      status: statusFilter !== 'all' ? statusFilter : undefined,
      workspace: workspaceParam ?? undefined,
    }),
  })

  const { data: workspacesData } = useQuery({
    queryKey: ['workspaces'],
    queryFn: () => getWorkspaces(),
    enabled: uploadOpen,
  })

  const uploadMutation = useUploadDocument()

  const { register, handleSubmit, reset, formState: { errors } } = useForm<UploadForm>({
    resolver: zodResolver(uploadSchema),
    defaultValues: { workspace: workspaceParam ?? '' },
  })

  const onSubmit = async (data: UploadForm) => {
    if (!selectedFile) return
    await uploadMutation.mutateAsync({
      workspaceId: data.workspace,
      title: data.title,
      file: selectedFile,
      onProgress: setUploadProgress,
    })
    setUploadOpen(false)
    setSelectedFile(null)
    setUploadProgress(0)
    reset()
  }

  const documents = data?.results ?? []

  return (
    <Layout title="Документы">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        {/* Фильтр */}
        <div className="flex gap-2 flex-wrap">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setStatusFilter(f.value)}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                statusFilter === f.value
                  ? 'bg-[#1F3864] text-white'
                  : 'bg-white text-gray-600 border border-gray-200 hover:border-gray-300'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        <Button onClick={() => setUploadOpen(true)}>
          <Plus className="h-4 w-4" />
          Загрузить документ
        </Button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : documents.length === 0 ? (
        <div className="text-center py-16">
          <FileText className="h-12 w-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500 font-medium">Документов нет</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <ul className="divide-y divide-gray-100">
            {documents.map((doc) => (
              <li key={doc.id}>
                <Link
                  to={`/documents/${doc.id}`}
                  className="flex items-center gap-4 px-5 py-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center justify-center h-10 w-10 rounded-lg bg-blue-50 flex-shrink-0">
                    <FileText className="h-5 w-5 text-[#1F3864]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{doc.title}</p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {doc.file_type.toUpperCase()} ·{' '}
                      {format(new Date(doc.updated_at), 'd MMM yyyy', { locale: ru })}
                    </p>
                  </div>
                  <DocumentStatusBadge status={doc.status} />
                  <ArrowRight className="h-4 w-4 text-gray-300 flex-shrink-0" />
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Модал загрузки */}
      <Modal
        isOpen={uploadOpen}
        onClose={() => { setUploadOpen(false); setSelectedFile(null); reset() }}
        title="Загрузить документ"
        size="md"
        footer={
          <>
            <Button variant="secondary" onClick={() => setUploadOpen(false)}>Отмена</Button>
            <Button
              onClick={handleSubmit(onSubmit)}
              isLoading={uploadMutation.isPending}
              disabled={!selectedFile}
            >
              Загрузить
            </Button>
          </>
        }
      >
        <form className="space-y-4">
          <Input
            label="Название документа"
            placeholder="Договор поставки №123"
            required
            error={errors.title?.message}
            {...register('title')}
          />

          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium text-gray-700">
              Кабинет <span className="text-red-500">*</span>
            </label>
            <select
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1F3864]"
              {...register('workspace')}
            >
              <option value="">Выберите кабинет...</option>
              {(workspacesData?.results ?? []).map((w) => (
                <option key={w.id} value={w.id}>{w.title}</option>
              ))}
            </select>
            {errors.workspace && <p className="text-xs text-red-600">{errors.workspace.message}</p>}
          </div>

          {/* Выбор файла */}
          <div>
            <label className="text-sm font-medium text-gray-700">
              Файл <span className="text-red-500">*</span>
            </label>
            <div
              onClick={() => fileRef.current?.click()}
              className="mt-1 border-2 border-dashed border-gray-300 rounded-xl p-6 text-center cursor-pointer hover:border-[#1F3864] transition-colors"
            >
              <Upload className="h-8 w-8 text-gray-400 mx-auto mb-2" />
              {selectedFile ? (
                <p className="text-sm font-medium text-[#1F3864]">{selectedFile.name}</p>
              ) : (
                <>
                  <p className="text-sm text-gray-500">Нажмите для выбора файла</p>
                  <p className="text-xs text-gray-400 mt-1">PDF, DOCX, XLSX, ODT, ODS · до 100 МБ</p>
                </>
              )}
              <input
                ref={fileRef}
                type="file"
                className="hidden"
                accept=".pdf,.docx,.xlsx,.odt,.ods"
                onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
              />
            </div>
          </div>

          {/* Прогресс загрузки */}
          {uploadMutation.isPending && uploadProgress > 0 && (
            <div>
              <div className="flex justify-between text-xs text-gray-500 mb-1">
                <span>Загрузка в S3...</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-[#1F3864] rounded-full transition-all"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}
        </form>
      </Modal>
    </Layout>
  )
}
