// ============================================================
// ГосДок — Страница регистрации с подтверждением email
// ============================================================

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation } from '@tanstack/react-query'
import { useNavigate, Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { register as registerApi, verifyEmail, resendCode } from '@/api/auth'
import { TOKEN_KEYS } from '@/api/client'
import { useAuthStore } from '@/store/authStore'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { FileText, Mail } from 'lucide-react'

const registerSchema = z.object({
  full_name: z.string().min(2, 'Минимум 2 символа').max(255),
  email: z.string().email('Введите корректный email'),
  phone: z.string().optional(),
  password: z.string().min(8, 'Минимум 8 символов'),
  confirm_password: z.string(),
}).refine((d) => d.password === d.confirm_password, {
  message: 'Пароли не совпадают',
  path: ['confirm_password'],
})

const codeSchema = z.object({
  code: z.string().length(6, 'Код состоит из 6 цифр').regex(/^\d+$/, 'Только цифры'),
})

type RegisterForm = z.infer<typeof registerSchema>
type CodeForm = z.infer<typeof codeSchema>

export default function Register() {
  const navigate = useNavigate()
  const setUser = useAuthStore((s) => s.setUser)
  const [step, setStep] = useState<'register' | 'verify'>('register')
  const [pendingEmail, setPendingEmail] = useState('')

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterForm>({ resolver: zodResolver(registerSchema) })

  const {
    register: registerCode,
    handleSubmit: handleCode,
    formState: { errors: codeErrors },
  } = useForm<CodeForm>({ resolver: zodResolver(codeSchema) })

  // Шаг 1 — регистрация
  const registerMutation = useMutation({
    mutationFn: (data: RegisterForm) =>
      registerApi({
        email: data.email,
        full_name: data.full_name,
        password: data.password,
        password_confirm: data.confirm_password,
        phone: data.phone,
      }),
    onSuccess: (res) => {
      setPendingEmail(res.email)
      setStep('verify')
      toast.success('Код подтверждения отправлен на ваш email')
    },
    onError: (error: { response?: { data?: Record<string, string[]> } }) => {
      const data = error?.response?.data
      if (data) {
        const firstKey = Object.keys(data)[0]
        toast.error(firstKey ? (data[firstKey][0] ?? 'Ошибка регистрации') : 'Ошибка регистрации')
      } else {
        toast.error('Ошибка регистрации')
      }
    },
  })

  // Повторная отправка кода
  const resendMutation = useMutation({
    mutationFn: () => resendCode({ email: pendingEmail, purpose: 'registration' }),
    onSuccess: () => toast.success('Код отправлен повторно'),
    onError: () => toast.error('Не удалось отправить код'),
  })

  // Шаг 2 — подтверждение кода
  const verifyMutation = useMutation({
    mutationFn: (data: CodeForm) => verifyEmail({ email: pendingEmail, code: data.code }),
    onSuccess: (res) => {
      localStorage.setItem(TOKEN_KEYS.access, res.access)
      localStorage.setItem(TOKEN_KEYS.refresh, res.refresh)
      setUser(res.user)
      toast.success('Email подтверждён! Добро пожаловать!')
      navigate('/dashboard')
    },
    onError: () => toast.error('Неверный или просроченный код'),
  })

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Логотип */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-[#1F3864] mb-4">
            <FileText className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">ГосДок</h1>
          <p className="text-sm text-gray-500 mt-1">Облачная платформа документооборота</p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
          {step === 'register' ? (
            <>
              <h2 className="text-lg font-semibold text-gray-900 mb-6">Создать аккаунт</h2>
              <form onSubmit={handleSubmit((d) => registerMutation.mutate(d))} className="space-y-4">
                <Input
                  label="ФИО"
                  placeholder="Иван Иванов"
                  required
                  error={errors.full_name?.message}
                  {...register('full_name')}
                />
                <Input
                  label="Email"
                  type="email"
                  placeholder="name@organization.kz"
                  required
                  error={errors.email?.message}
                  {...register('email')}
                />
                <Input
                  label="Телефон"
                  type="tel"
                  placeholder="+7 (700) 000-0000"
                  error={errors.phone?.message}
                  {...register('phone')}
                />
                <Input
                  label="Пароль"
                  type="password"
                  placeholder="Минимум 8 символов"
                  required
                  error={errors.password?.message}
                  {...register('password')}
                />
                <Input
                  label="Подтвердите пароль"
                  type="password"
                  placeholder="Повторите пароль"
                  required
                  error={errors.confirm_password?.message}
                  {...register('confirm_password')}
                />
                <Button type="submit" className="w-full" size="lg" isLoading={registerMutation.isPending}>
                  Зарегистрироваться
                </Button>
              </form>
            </>
          ) : (
            <>
              <div className="text-center mb-6">
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-blue-50 mb-3">
                  <Mail className="h-6 w-6 text-[#1F3864]" />
                </div>
                <h2 className="text-lg font-semibold text-gray-900">Подтвердите email</h2>
                <p className="text-sm text-gray-500 mt-1">
                  Мы отправили 6-значный код на<br />
                  <strong className="text-gray-700">{pendingEmail}</strong>
                </p>
              </div>
              <form onSubmit={handleCode((d) => verifyMutation.mutate(d))} className="space-y-4">
                <Input
                  label="Код подтверждения"
                  placeholder="000000"
                  maxLength={6}
                  required
                  error={codeErrors.code?.message}
                  className="text-center text-2xl tracking-widest font-mono"
                  {...registerCode('code')}
                />
                <Button type="submit" className="w-full" size="lg" isLoading={verifyMutation.isPending}>
                  Подтвердить
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
                    onClick={() => setStep('register')}
                    className="text-sm text-gray-400 hover:text-gray-600"
                  >
                    ← Вернуться назад
                  </button>
                </div>
              </form>
            </>
          )}

          <p className="text-center text-sm text-gray-500 mt-6">
            Уже есть аккаунт?{' '}
            <Link to="/login" className="text-[#1F3864] font-medium hover:underline">
              Войти
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
