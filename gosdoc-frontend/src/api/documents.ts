// ============================================================
// ГосДок — API документов, версий, комментариев, подписей (разделы 4.5, 4.7, 4.8 ТЗ)
// ============================================================

import apiClient from './client'
import type {
  Comment,
  Document,
  DocumentListItem,
  DocumentVersion,
  PaginatedResponse,
  PresignedUploadResponse,
  Signature,
  SignatureVerification,
} from '@/types'

// ============================================================
// Документы (4.5)
// ============================================================

// GET /api/v1/documents/
export async function getDocuments(params?: {
  status?: string
  workspace?: string
  page?: number
}): Promise<PaginatedResponse<DocumentListItem>> {
  const response = await apiClient.get('/documents/', { params })
  return response.data
}

// GET /api/v1/documents/{id}/
export async function getDocument(id: string): Promise<Document> {
  const response = await apiClient.get(`/documents/${id}/`)
  return response.data
}

// PATCH /api/v1/documents/{id}/
export async function updateDocument(id: string, data: { title?: string }): Promise<Document> {
  const response = await apiClient.patch(`/documents/${id}/`, data)
  return response.data
}

// DELETE /api/v1/documents/{id}/
export async function deleteDocument(id: string): Promise<void> {
  await apiClient.delete(`/documents/${id}/`)
}

// ---- Шаг 1: получить presigned URL для загрузки ----
// POST /api/v1/documents/request-upload/
export async function requestDocumentUpload(data: {
  workspace: string
  title: string
  file_name: string
  file_size: number
}): Promise<PresignedUploadResponse> {
  const response = await apiClient.post('/documents/request-upload/', data)
  return response.data
}

// ---- Шаг 2: загрузить файл напрямую в S3 ----
export async function uploadFileToS3(
  uploadUrl: string,
  uploadFields: Record<string, string>,
  file: File,
  onProgress?: (percent: number) => void
): Promise<void> {
  const formData = new FormData()
  // Поля S3 должны идти ПЕРЕД файлом
  Object.entries(uploadFields).forEach(([key, value]) => {
    formData.append(key, value)
  })
  formData.append('file', file)

  await new Promise<void>((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', uploadUrl)

    if (onProgress) {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
          onProgress(Math.round((e.loaded / e.total) * 100))
        }
      }
    }

    xhr.onload = () => {
      // S3 возвращает 204 при успехе
      if (xhr.status === 204 || xhr.status === 200) {
        resolve()
      } else {
        reject(new Error(`S3 upload failed: ${xhr.status} ${xhr.responseText}`))
      }
    }
    xhr.onerror = () => reject(new Error('S3 upload network error'))
    xhr.send(formData)
  })
}

// ---- Шаг 3: подтвердить загрузку в Django ----
// POST /api/v1/documents/
export async function confirmDocumentUpload(data: {
  workspace: string
  title: string
  file_name: string
  storage_key: string
}): Promise<Document> {
  const response = await apiClient.post('/documents/', data)
  return response.data
}

// GET /api/v1/documents/{id}/download/
export async function getDocumentDownloadUrl(id: string): Promise<{
  download_url: string
  expires_in: number
  file_name: string
  file_type: string
}> {
  const response = await apiClient.get(`/documents/${id}/download/`)
  return response.data
}

// POST /api/v1/documents/{id}/workflow/start/
export async function startWorkflow(id: string): Promise<{
  detail: string
  status: string
  tasks_created: number
}> {
  const response = await apiClient.post(`/documents/${id}/workflow/start/`)
  return response.data
}

// ============================================================
// Версии документов
// ============================================================

// GET /api/v1/documents/{id}/versions/
export async function getDocumentVersions(documentId: string): Promise<DocumentVersion[]> {
  const response = await apiClient.get(`/documents/${documentId}/versions/`)
  return response.data
}

// POST /api/v1/documents/{id}/versions/request-upload/ — шаг 1 новой версии
export async function requestVersionUpload(
  documentId: string,
  data: { file_name: string; file_size: number }
): Promise<PresignedUploadResponse> {
  const response = await apiClient.post(`/documents/${documentId}/versions/request-upload/`, data)
  return response.data
}

// POST /api/v1/documents/{id}/versions/ — шаг 3 новой версии
export async function confirmVersionUpload(
  documentId: string,
  data: { storage_key: string; file_name: string }
): Promise<DocumentVersion> {
  const response = await apiClient.post(`/documents/${documentId}/versions/`, data)
  return response.data
}

// GET /api/v1/documents/{id}/versions/{vid}/diff/
export async function getVersionDiff(documentId: string, versionId: string): Promise<{
  version_id: string
  version_number: number
  ai_changes_detected: boolean
  ai_diff_summary: import('@/types').AiDiffSummary | null
  checksum: string
  created_at: string
}> {
  const response = await apiClient.get(`/documents/${documentId}/versions/${versionId}/diff/`)
  return response.data
}

// ============================================================
// Подписи (4.7)
// ============================================================

// POST /api/v1/documents/{id}/sign/
export async function signDocument(
  documentId: string,
  data: { signature_data: string; certificate_id?: string }
): Promise<{ signature: Signature; document_fully_signed: boolean }> {
  const response = await apiClient.post(`/documents/${documentId}/sign/`, data)
  return response.data
}

// GET /api/v1/documents/{id}/signatures/
export async function getDocumentSignatures(documentId: string): Promise<Signature[]> {
  const response = await apiClient.get(`/documents/${documentId}/signatures/`)
  return response.data
}

// GET /api/v1/signatures/{id}/verify/
export async function verifySignature(signatureId: string): Promise<SignatureVerification> {
  const response = await apiClient.get(`/signatures/${signatureId}/verify/`)
  return response.data
}

// ============================================================
// Комментарии (4.8)
// ============================================================

// GET /api/v1/documents/{id}/comments/
export async function getComments(documentId: string): Promise<Comment[]> {
  const response = await apiClient.get(`/documents/${documentId}/comments/`)
  return response.data
}

// POST /api/v1/documents/{id}/comments/
export async function createComment(
  documentId: string,
  data: { content: string; parent?: string }
): Promise<Comment> {
  const response = await apiClient.post(`/documents/${documentId}/comments/`, data)
  return response.data
}

// PATCH /api/v1/comments/{id}/
export async function updateComment(id: string, data: { content: string }): Promise<Comment> {
  const response = await apiClient.patch(`/comments/${id}/`, data)
  return response.data
}

// DELETE /api/v1/comments/{id}/
export async function deleteComment(id: string): Promise<void> {
  await apiClient.delete(`/comments/${id}/`)
}

// POST /api/v1/comments/{id}/resolve/
export async function resolveComment(id: string): Promise<{ detail: string }> {
  const response = await apiClient.post(`/comments/${id}/resolve/`)
  return response.data
}
