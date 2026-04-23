// ============================================================
// ГосДок — Общий AI ассистент (полноэкранный чат)
// ============================================================

import { useEffect, useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Sparkles, Send, FileText, Search, HelpCircle, Download } from 'lucide-react'
import { clsx } from 'clsx'
import { useNavigate } from 'react-router-dom'
import { Document, Packer, Paragraph, TextRun } from 'docx'
import { generalChat, getChatHistory } from '@/api/ai'
import type { ChatMessage, SearchSource } from '@/api/ai'

const DOCUMENT_KEYWORDS = ['ДОГОВОР', 'СОГЛАШЕНИЕ', 'АКТ', 'ПРИКАЗ', 'ЗАЯВЛЕНИЕ']

function isDocumentMessage(text: string): boolean {
  const upper = text.toUpperCase()
  return DOCUMENT_KEYWORDS.some((kw) => upper.includes(kw))
}

async function downloadAsDocx(text: string) {
  const paragraphs = text.split('\n').map(
    (line) => new Paragraph({ children: [new TextRun(line)] })
  )
  const doc = new Document({ sections: [{ children: paragraphs }] })
  const blob = await Packer.toBlob(doc)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'document.docx'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

interface GeneralChatProps {
  workspaceId: string
}

const QUICK_ACTIONS = [
  { label: 'Создать договор', icon: FileText, message: 'Помоги создать договор' },
  { label: 'Найти документы', icon: Search, message: 'Найди документы, связанные с' },
  { label: 'Помощь с документом', icon: HelpCircle, message: 'Объясни, как работает процесс подписания документов' },
]

export function GeneralChat({ workspaceId }: GeneralChatProps) {
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  // Подгружаем историю чата
  const { data: historyData } = useQuery({
    queryKey: ['chat-history-general', workspaceId],
    queryFn: () => getChatHistory({ workspace_id: workspaceId }),
    enabled: !!workspaceId,
  })

  const messages = historyData?.messages ?? []

  // Отправка сообщения
  const sendMutation = useMutation({
    mutationFn: (message: string) => generalChat(message, workspaceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat-history-general', workspaceId] })
    },
  })

  // Последние sources из ответа
  const [lastSources, setLastSources] = useState<SearchSource[]>([])

  useEffect(() => {
    if (sendMutation.data?.sources) {
      setLastSources(sendMutation.data.sources)
    }
  }, [sendMutation.data])

  // Автоскролл
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sendMutation.isPending])

  // Фокус при монтировании
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const handleSend = (text?: string) => {
    const msg = text ?? input.trim()
    if (!msg || sendMutation.isPending) return
    setInput('')
    sendMutation.mutate(msg)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const isFirstOpen = messages.length === 0 && !sendMutation.isPending

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-3 flex-shrink-0">
        <div className="h-10 w-10 rounded-xl bg-purple-100 flex items-center justify-center">
          <Sparkles className="h-5 w-5 text-purple-600" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-gray-900">AI Ассистент</h1>
          <p className="text-xs text-gray-500">Помощь с документами и поиск по кабинету</p>
        </div>
      </div>

      {/* Сообщения */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="max-w-3xl mx-auto space-y-5">

          {/* Приветствие */}
          {isFirstOpen && (
            <div className="text-center py-12">
              <div className="h-16 w-16 rounded-2xl bg-purple-100 flex items-center justify-center mx-auto mb-4">
                <Sparkles className="h-8 w-8 text-purple-600" />
              </div>
              <h2 className="text-xl font-bold text-gray-900 mb-2">Привет!</h2>
              <p className="text-sm text-gray-500 max-w-md mx-auto">
                Я AI ассистент ГосДок. Могу помочь найти документы,
                ответить на вопросы и создать новые документы.
              </p>

              {/* Быстрые кнопки */}
              <div className="flex flex-wrap justify-center gap-3 mt-6">
                {QUICK_ACTIONS.map(({ label, icon: Icon, message }) => (
                  <button
                    key={label}
                    onClick={() => handleSend(message)}
                    className="flex items-center gap-2 px-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm text-gray-700 hover:border-[#1F3864] hover:text-[#1F3864] transition-colors"
                  >
                    <Icon className="h-4 w-4" />
                    {label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Список сообщений */}
          {messages.map((msg) => (
            <MessageRow key={msg.id} message={msg} />
          ))}

          {/* Индикатор загрузки */}
          {sendMutation.isPending && (
            <div className="flex items-start gap-3">
              <div className="h-8 w-8 rounded-full bg-purple-100 flex items-center justify-center flex-shrink-0">
                <Sparkles className="h-4 w-4 text-purple-600" />
              </div>
              <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3">
                <div className="flex gap-1.5">
                  <span className="h-2 w-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
                  <span className="h-2 w-2 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
                  <span className="h-2 w-2 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
                </div>
              </div>
            </div>
          )}

          {/* Источники */}
          {lastSources.length > 0 && !sendMutation.isPending && messages.length > 0 && (
            <div className="max-w-xl bg-white border border-purple-100 rounded-xl px-4 py-3 ml-11">
              <p className="text-xs font-medium text-purple-700 mb-2">Найденные документы:</p>
              <div className="space-y-1.5">
                {lastSources.map((source, i) => (
                  <button
                    key={i}
                    onClick={() => navigate(`/documents/${source.document_id}`)}
                    className="flex items-center gap-2 text-left w-full hover:bg-purple-50 rounded-lg px-2 py-1.5 transition-colors"
                  >
                    <FileText className="h-4 w-4 text-purple-500 flex-shrink-0" />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm text-gray-800 font-medium truncate">{source.title}</p>
                      <p className="text-xs text-gray-500 truncate">{source.chunk_text.slice(0, 100)}</p>
                    </div>
                    <span className="text-xs text-purple-600 flex-shrink-0">{Math.round(source.score * 100)}%</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Ошибка */}
      {sendMutation.isError && (
        <div className="px-6 pb-2">
          <p className="text-xs text-red-500 text-center">Ошибка AI-сервиса. Попробуйте ещё раз.</p>
        </div>
      )}

      {/* Поле ввода */}
      <div className="border-t border-gray-200 bg-white px-6 py-4 flex-shrink-0">
        <div className="max-w-3xl mx-auto flex items-end gap-3">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Напишите сообщение..."
            rows={1}
            className="flex-1 resize-none rounded-xl border border-gray-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#1F3864] max-h-32"
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || sendMutation.isPending}
            className={clsx(
              'rounded-xl p-2.5 transition-colors flex-shrink-0',
              input.trim() && !sendMutation.isPending
                ? 'bg-[#1F3864] text-white hover:bg-[#162952]'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
            )}
          >
            <Send className="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>
  )
}

// ---- Строка сообщения ----

function MessageRow({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'
  const showDownload = !isUser && isDocumentMessage(message.content)

  return (
    <div className={clsx('flex items-start gap-3', isUser && 'flex-row-reverse')}>
      <div
        className={clsx(
          'h-8 w-8 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-semibold',
          isUser ? 'bg-[#1F3864] text-white' : 'bg-purple-100'
        )}
      >
        {isUser ? 'Вы' : <Sparkles className="h-4 w-4 text-purple-600" />}
      </div>
      <div className="flex flex-col items-start gap-2 max-w-xl">
        <div
          className={clsx(
            'rounded-2xl px-4 py-3 text-sm',
            isUser
              ? 'bg-[#1F3864] text-white rounded-tr-sm'
              : 'bg-white border border-gray-200 text-gray-800 rounded-tl-sm'
          )}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
        {showDownload && (
          <button
            onClick={() => downloadAsDocx(message.content)}
            className="flex items-center gap-1.5 px-2.5 py-1 border border-gray-300 text-gray-600 hover:bg-gray-50 rounded-md text-xs transition-colors"
          >
            <Download className="h-3.5 w-3.5" />
            Скачать как DOCX
          </button>
        )}
      </div>
    </div>
  )
}
