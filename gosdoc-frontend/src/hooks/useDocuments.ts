// ============================================================
// ГосДок — Хуки для работы с документами (React Query)
// ============================================================

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  getDocuments,
  getDocument,
  requestDocumentUpload,
  uploadFileToS3,
  confirmDocumentUpload,
  getDocumentVersions,
  requestVersionUpload,
  confirmVersionUpload,
  startWorkflow,
} from '@/api/documents'

// Список документов
export function useDocuments(params?: { status?: string; workspace?: string; page?: number }) {
  return useQuery({
    queryKey: ['documents', params],
    queryFn: () => getDocuments(params),
  })
}

// Один документ
export function useDocument(id: string) {
  return useQuery({
    queryKey: ['document', id],
    queryFn: () => getDocument(id),
    enabled: !!id,
  })
}

// История версий
export function useDocumentVersions(documentId: string) {
  return useQuery({
    queryKey: ['document-versions', documentId],
    queryFn: () => getDocumentVersions(documentId),
    enabled: !!documentId,
  })
}

// Загрузка нового документа (трёхшаговый процесс)
export function useUploadDocument() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      workspaceId,
      title,
      file,
      onProgress,
    }: {
      workspaceId: string
      title: string
      file: File
      onProgress?: (pct: number) => void
    }) => {
      // Шаг 1: presigned URL
      const presigned = await requestDocumentUpload({
        workspace: workspaceId,
        title,
        file_name: file.name,
        file_size: file.size,
      })

      // Шаг 2: загрузка в S3
      await uploadFileToS3(presigned.upload_url, presigned.upload_fields, file, onProgress)

      // Шаг 3: подтверждение
      return confirmDocumentUpload({
        workspace: workspaceId,
        title,
        file_name: file.name,
        storage_key: presigned.storage_key,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      toast.success('Документ успешно загружен')
    },
    onError: (error: Error) => {
      toast.error(`Ошибка загрузки: ${error.message}`)
    },
  })
}

// Загрузка новой версии документа
export function useUploadVersion(documentId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      file,
      onProgress,
    }: {
      file: File
      onProgress?: (pct: number) => void
    }) => {
      const presigned = await requestVersionUpload(documentId, {
        file_name: file.name,
        file_size: file.size,
      })
      await uploadFileToS3(presigned.upload_url, presigned.upload_fields, file, onProgress)
      return confirmVersionUpload(documentId, {
        storage_key: presigned.storage_key,
        file_name: file.name,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['document', documentId] })
      queryClient.invalidateQueries({ queryKey: ['document-versions', documentId] })
      toast.success('Новая версия загружена. AI-анализ запущен в фоне.')
    },
    onError: (error: Error) => {
      toast.error(`Ошибка загрузки версии: ${error.message}`)
    },
  })
}

// Запуск workflow
export function useStartWorkflow(documentId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => startWorkflow(documentId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['document', documentId] })
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      toast.success(`Workflow запущен. Создано задач: ${data.tasks_created}`)
    },
    onError: () => {
      toast.error('Не удалось запустить workflow')
    },
  })
}
