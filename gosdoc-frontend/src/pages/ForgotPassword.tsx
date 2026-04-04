// ============================================================
// ГосДок — Страница сброса пароля (Забыли пароль?)
// 3 шага: email → код → новый пароль
// ============================================================

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { resetPassword, resetPasswordConfirm, resendCode } from '@/api/auth'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { FileText, Mail, KeyRound } from 'lucide-react'

const emailSchema = z.object({
  email: z.string().email('Введите корректный email'),
})
const codeSchema = z.object({
  code: z.string().length(6, 'Код состоит из 6 цифр').regex(/^\d+$/, 'Только цифры'),
})
const passwordSchema = z.object({
  new_password: z.string().min(8, 'Минимум 8 символов'),
  confirm_password: z.string(),
}).refine((d) => d.new_password === d.confirm_password, {
  message: 'Пароли не совпадают',
  path: ['confirm_password'],
})

type EmailForm = z.infer<typeof emailSchema>
type CodeForm = z.infer<typeof codeSchema>
type PasswordForm = z.infer<typeof passwordSchema>

type Step = 'email' | 'code' | 'password' | 'done'

export default function ForgotPassword() {
  const navigate = useNavigate()
  const [step, setStep] = useState<Step>('email')
  const [pendingEmail, setPendingEmail] = useState('')
  const [pendingCode, setPendingCode] = useState('')

  const emailForm = useForm<EmailForm>({ resolver: zodResolver(emailSchema) })
  const codeForm = useForm<CodeForm>({ resolver: zodResolver(codeSchema) })
  const passwordForm = useForm<PasswordForm>({ resolver: zodResolver(passwordSchema) })

  // Шаг 1 — отправить код
  const requestMutation = useMutation({
    mutationFn: (data: EmailForm) => resetPassword({ email: data.email }),
    onSuccess: (_, vars) => {
      setPendingEmail(vars.email)
      setStep('code')
      toast.success('Если email зарегистрирован — код отправлен')
    },
    onError: () => toast.error('Ошибка отправки кода'),
  })

  // Повторная отправка кода сброса
  const resendMutation = useMutation({
    mutationFn: () => resendCode({ email: pendingEmail, purpose: 'password_reset' }),
    onSuccess: () => toast.success('Код отправлен повторно'),
    onError: () => toast.error('Не удалось отправить код'),
  })

  // Шаг 2 — проверяем что код введён, переходим к паролю
  const handleCodeSubmit = (data: CodeForm) => {
    setPendingCode(data.code)
    setStep('password')
  }

  // Шаг 3 — сбросить пароль
  const confirmMutation = useMutation({
    mutationFn: (data: PasswordForm) =>
      resetPasswordConfirm({ email: pendingEmail, code: pendingCode, new_password: data.new_password }),
    onSuccess: () => {
      setStep('done')
    },
    onError: () => toast.error('Неверный или просроченный код. Начните заново.'),
  })

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-[#1F3864] mb-4">
            <FileText className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">ГосДок</h1>
          <p className="text-sm text-gray-500 mt-1">Облачная платформа документооборота</p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">

          {/* Шаг 1 — email */}
          {step === 'email' && (
            <>
              <h2 className="text-lg font-semibold text-gray-900 mb-2">Забыли пароль?</h2>
              <p className="text-sm text-gray-500 mb-6">
                Введите email — мы отправим код для сброса пароля.
              </p>
              <form onSubmit={emailForm.handleSubmit((d) => requestMutation.mutate(d))} className="space-y-4">
                <Input
                  label="Email"
                  type="email"
                  placeholder="name@organization.kz"
                  required
                  error={emailForm.formState.errors.email?.message}
                  {...emailForm.register('email')}
                />
                <Button type="submit" className="w-full" size="lg" isLoading={requestMutation.isPending}>
                  Отправить код
                </Button>
              </form>
            </>
          )}

          {/* Шаг 2 — код */}
          {step === 'code' && (
            <>
              <div className="text-center mb-6">
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-blue-50 mb-3">
                  <Mail className="h-6 w-6 text-[#1F3864]" />
                </div>
                <h2 className="text-lg font-semibold text-gray-900">Введите код</h2>
                <p className="text-sm text-gray-500 mt-1">
                  Код отправлен на <strong className="text-gray-700">{pendingEmail}</strong>
                </p>
              </div>
              <form onSubmit={codeForm.handleSubmit(handleCodeSubmit)} className="space-y-4">
                <Input
                  label="Код подтверждения"
                  placeholder="000000"
                  maxLength={6}
                  required
                  error={codeForm.formState.errors.code?.message}
                  className="text-center text-2xl tracking-widest font-mono"
                  {...codeForm.register('code')}
                />
                <Button type="submit" className="w-full" size="lg">
                  Продолжить
                </Button>
                <div className="flex flex-col gap-2 items-center">
                  <button
                    type="button"
                    onClick={() => resendMutation.mutate()}
                    disabled={resendMutation.isPending}
                    className="text-sm text-[#1F3864] hover:underline disabled:opacity-50"
                  >
                    {resendMutation.isPending ? 'Отправляем...' : 'Не пришёл код? Отправить повторно'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setStep('email')}
                    className="text-sm text-gray-400 hover:text-gray-600"
                  >
                    ← Изменить email
                  </button>
                </div>
              </form>
            </>
          )}

          {/* Шаг 3 — новый пароль */}
          {step === 'password' && (
            <>
              <div className="text-center mb-6">
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-green-50 mb-3">
                  <KeyRound className="h-6 w-6 text-green-600" />
                </div>
                <h2 className="text-lg font-semibold text-gray-900">Новый пароль</h2>
                <p className="text-sm text-gray-500 mt-1">Придумайте новый пароль для аккаунта</p>
              </div>
              <form onSubmit={passwordForm.handleSubmit((d) => confirmMutation.mutate(d))} className="space-y-4">
                <Input
                  label="Новый пароль"
                  type="password"
                  placeholder="Минимум 8 символов"
                  required
                  error={passwordForm.formState.errors.new_password?.message}
                  {...passwordForm.register('new_password')}
                />
                <Input
                  label="Повторите пароль"
                  type="password"
                  placeholder="Повторите новый пароль"
                  required
                  error={passwordForm.formState.errors.confirm_password?.message}
                  {...passwordForm.register('confirm_password')}
                />
                <Button type="submit" className="w-full" size="lg" isLoading={confirmMutation.isPending}>
                  Сохранить пароль
                </Button>
              </form>
            </>
          )}

          {/* Готово */}
          {step === 'done' && (
            <div className="text-center py-4">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-50 mb-4">
                <KeyRound className="h-8 w-8 text-green-600" />
              </div>
              <h2 className="text-lg font-semibold text-gray-900 mb-2">Пароль изменён!</h2>
              <p className="text-sm text-gray-500 mb-6">Теперь войдите с новым паролем.</p>
              <Button className="w-full" onClick={() => navigate('/login')}>
                Войти
              </Button>
            </div>
          )}

          {step !== 'done' && (
            <p className="text-center text-sm text-gray-500 mt-6">
              Вспомнили пароль?{' '}
              <Link to="/login" className="text-[#1F3864] font-medium hover:underline">
                Войти
              </Link>
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
