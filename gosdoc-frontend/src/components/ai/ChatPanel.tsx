// ============================================================
// ГосДок — Панель чата с документом (боковая панель)
// ============================================================

import { useEffect, useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Sparkles, Send, X } from 'lucide-react'
import { clsx } from 'clsx'
import { chatWithDocument, getChatHistory } from '@/api/ai'
import type { ChatMessage, ContextChunk } from '@/api/ai'

interface ChatPanelProps {
  documentId: string
  documentTitle: string
  isOpen: boolean
  onClose: () => void
}

export function ChatPanel({ documentId, documentTitle, isOpen, onClose }: ChatPanelProps) {
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const queryClient = useQueryClient()

  // Подгружаем историю чата
  const { data: historyData } = useQuery({
    queryKey: ['chat-history', documentId],
    queryFn: () => getChatHistory({ document_id: documentId }),
    enabled: isOpen,
  })

  const messages = historyData?.messages ?? []

  // Отправка сообщения
  const sendMutation = useMutation({
    mutationFn: (message: string) => chatWithDocument(documentId, message),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat-history', documentId] })
    },
  })

  // Последние context_chunks из ответа
  const [lastChunks, setLastChunks] = useState<ContextChunk[]>([])

  useEffect(() => {
    if (sendMutation.data?.context_chunks) {
      setLastChunks(sendMutation.data.context_chunks)
    }
  }, [sendMutation.data])

  // Автоскролл к последнему сообщению
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sendMutation.isPending])

  // Фокус на поле ввода при открытии
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 200)
    }
  }, [isOpen])

  const handleSend = () => {
    const trimmed = input.trim()
    if (!trimmed || sendMutation.isPending) return
    setInput('')
    sendMutation.mutate(trimmed)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  if (!isOpen) return null

  return (
    <div className="w-[380px] flex-shrink-0 border-l border-gray-200 bg-white flex flex-col h-full">
      {/* Header */}
      <div className="bg-[#1F3864] text-white px-4 py-3 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <Sparkles className="h-5 w-5 flex-shrink-0 text-yellow-300" />
          <div className="min-w-0">
            <h3 className="text-sm font-semibold truncate">AI Ассистент</h3>
            <p className="text-xs text-blue-200 truncate">{documentTitle}</p>
          </div>
        </div>
        <button onClick={onClose} className="text-white/60 hover:text-white flex-shrink-0">
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Сообщения */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && !sendMutation.isPending && (
          <div className="text-center py-8">
            <Sparkles className="h-8 w-8 text-purple-300 mx-auto mb-3" />
            <p className="text-sm text-gray-500">
              Задайте вопрос по документу,<br />и AI ответит на основе его содержания.
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {/* Индикатор загрузки */}
        {sendMutation.isPending && (
          <div className="flex items-start gap-2">
            <div className="h-7 w-7 rounded-full bg-purple-100 flex items-center justify-center flex-shrink-0">
              <Sparkles className="h-4 w-4 text-purple-600" />
            </div>
            <div className="bg-gray-100 rounded-2xl rounded-tl-sm px-4 py-3">
              <div className="flex gap-1.5">
                <span className="h-2 w-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
                <span className="h-2 w-2 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
                <span className="h-2 w-2 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}

        {/* Источники */}
        {lastChunks.length > 0 && !sendMutation.isPending && messages.length > 0 && (
          <div className="bg-purple-50 border border-purple-100 rounded-lg px-3 py-2">
            <p className="text-xs font-medium text-purple-700 mb-1">Источники:</p>
            {lastChunks.slice(0, 3).map((chunk, i) => (
              <p key={i} className="text-xs text-purple-600 truncate">
                Фрагмент {chunk.chunk_index + 1}: {chunk.chunk_text.slice(0, 80)}...
              </p>
            ))}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Ошибка */}
      {sendMutation.isError && (
        <div className="px-4 pb-2">
          <p className="text-xs text-red-500">Ошибка AI-сервиса. Попробуйте ещё раз.</p>
        </div>
      )}

      {/* Поле ввода */}
      <div className="border-t border-gray-200 px-4 py-3 flex-shrink-0">
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Задайте вопрос по документу..."
            rows={1}
            className="flex-1 resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1F3864] max-h-24"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || sendMutation.isPending}
            className={clsx(
              'rounded-lg p-2 transition-colors flex-shrink-0',
              input.trim() && !sendMutation.isPending
                ? 'bg-[#1F3864] text-white hover:bg-[#162952]'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
            )}
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  )
}

// ---- Пузырёк сообщения ----

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'

  return (
    <div className={clsx('flex items-start gap-2', isUser && 'flex-row-reverse')}>
      <div
        className={clsx(
          'h-7 w-7 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-semibold',
          isUser ? 'bg-[#1F3864] text-white' : 'bg-purple-100'
        )}
      >
        {isUser ? 'Вы' : <Sparkles className="h-4 w-4 text-purple-600" />}
      </div>
      <div
        className={clsx(
          'max-w-[85%] rounded-2xl px-4 py-2.5 text-sm',
          isUser
            ? 'bg-[#1F3864] text-white rounded-tr-sm'
            : 'bg-gray-100 text-gray-800 rounded-tl-sm'
        )}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
      </div>
    </div>
  )
}
