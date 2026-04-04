// ============================================================
// ГосДок — Холст для рисования подписи (react-signature-canvas)
// Раздел 2.7 ТЗ: рукописные подписи (canvas-рисование в браузере)
// ============================================================

import { useRef, useState } from 'react'
import SignatureCanvasLib from 'react-signature-canvas'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Trash2, Check } from 'lucide-react'
import { signDocument } from '@/api/documents'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'

interface SignatureCanvasProps {
  documentId: string
  isOpen: boolean
  onClose: () => void
  onSigned?: () => void
}

export function SignatureCanvas({ documentId, isOpen, onClose, onSigned }: SignatureCanvasProps) {
  const sigRef = useRef<SignatureCanvasLib>(null)
  const [isEmpty, setIsEmpty] = useState(true)
  const queryClient = useQueryClient()

  const signMutation = useMutation({
    mutationFn: (signatureData: string) =>
      signDocument(documentId, { signature_data: signatureData }),
    onSuccess: ({ document_fully_signed }) => {
      queryClient.invalidateQueries({ queryKey: ['document', documentId] })
      queryClient.invalidateQueries({ queryKey: ['document-signatures', documentId] })
      if (document_fully_signed) {
        toast.success('Документ полностью подписан всеми подписантами!')
      } else {
        toast.success('Ваша подпись принята')
      }
      onClose()
      onSigned?.()
    },
    onError: (error: { response?: { data?: { detail?: string } } }) => {
      toast.error(error?.response?.data?.detail ?? 'Ошибка при подписании документа')
    },
  })

  const handleClear = () => {
    sigRef.current?.clear()
    setIsEmpty(true)
  }

  const handleSign = () => {
    if (!sigRef.current || sigRef.current.isEmpty()) {
      toast.error('Пожалуйста, поставьте подпись')
      return
    }
    // Получаем Base64 PNG
    const dataUrl = sigRef.current.toDataURL('image/png')
    signMutation.mutate(dataUrl)
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Электронная подпись"
      size="md"
      footer={
        <>
          <Button variant="ghost" onClick={handleClear} disabled={isEmpty}>
            <Trash2 className="h-4 w-4" />
            Очистить
          </Button>
          <Button variant="secondary" onClick={onClose}>Отмена</Button>
          <Button
            onClick={handleSign}
            isLoading={signMutation.isPending}
            disabled={isEmpty}
          >
            <Check className="h-4 w-4" />
            Подписать
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <p className="text-sm text-gray-500">
          Нарисуйте подпись в поле ниже. Подписанный документ будет заблокирован от редактирования.
        </p>

        {/* Canvas */}
        <div className="border-2 border-dashed border-gray-300 rounded-xl overflow-hidden bg-white">
          <SignatureCanvasLib
            ref={sigRef}
            penColor="#1F3864"
            canvasProps={{
              className: 'w-full',
              style: { width: '100%', height: '200px', touchAction: 'none' },
            }}
            onBegin={() => setIsEmpty(false)}
          />
        </div>

        <p className="text-xs text-gray-400 text-center">
          Проведите пальцем или мышью для рисования подписи
        </p>
      </div>
    </Modal>
  )
}
