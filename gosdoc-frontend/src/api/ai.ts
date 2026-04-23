// ============================================================
// ГосДок — API AI-сервиса (чат, генерация, поиск, резюме)
// ============================================================

import apiClient from './client'

// ---- Типы ----

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface ContextChunk {
  chunk_text: string
  chunk_index: number
}

export interface SearchSource {
  document_id: string
  title: string
  chunk_text: string
  score: number
}

// ---- Чат с документом ----

// POST /api/v1/ai/chat/document/
export async function chatWithDocument(
  document_id: string,
  message: string
): Promise<{ reply: string; context_chunks: ContextChunk[] }> {
  const response = await apiClient.post('/ai/chat/document/', {
    document_id,
    message,
  })
  return response.data
}

// ---- Общий AI ассистент ----

// POST /api/v1/ai/chat/general/
export async function generalChat(
  message: string,
  workspace_id: string
): Promise<{ reply: string; sources: SearchSource[] }> {
  const response = await apiClient.post('/ai/chat/general/', {
    message,
    workspace_id,
  })
  return response.data
}

// ---- История чата ----

// GET /api/v1/ai/chat/history/
export async function getChatHistory(params: {
  document_id?: string
  workspace_id?: string
}): Promise<{ messages: ChatMessage[] }> {
  const response = await apiClient.get('/ai/chat/history/', { params })
  return response.data
}

// ---- Генерация документа ----

// POST /api/v1/ai/generate/
export async function generateDocument(
  description: string,
  doc_type: 'contract' | 'order' | 'act' | 'invoice'
): Promise<{ content: string; doc_type: string }> {
  const response = await apiClient.post('/ai/generate/', {
    description,
    doc_type,
  })
  return response.data
}

// ---- Резюме документа ----

// POST /api/v1/ai/summarize/
export async function summarizeDocument(
  document_id: string
): Promise<{ summary: string; key_points: string[]; document_id: string; document_title: string }> {
  const response = await apiClient.post('/ai/summarize/', { document_id })
  return response.data
}

// ---- Семантический поиск ----

// POST /api/v1/ai/search/
export async function searchDocuments(
  query: string,
  workspace_id: string
): Promise<{ results: SearchSource[] }> {
  const response = await apiClient.post('/ai/search/', {
    query,
    workspace_id,
  })
  return response.data
}
