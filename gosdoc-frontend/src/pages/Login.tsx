// ============================================================
// ГосДок — Страница входа
// ============================================================

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation } from '@tanstack/react-query'
import { useNavigate, Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { login } from '@/api/auth'
import { useAuthStore } from '@/store/authStore'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { FileText } from 'lucide-react'

const schema = z.object({
  email: z.string().email('Введите корректный email'),
  password: z.string().min(1, 'Введите пароль'),
})

type FormData = z.infer<typeof schema>

export default function Login() {
  const navigate = useNavigate()
  const { setUser } = useAuthStore()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  const mutation = useMutation({
    mutationFn: login,
    onSuccess: ({ user }) => {
      setUser(user)
      navigate('/dashboard')
      toast.success(`Добро пожаловать, ${user.full_name}!`)
    },
    onError: () => {
      toast.error('Неверный email или пароль')
    },
  })

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Логотип */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-[#1F3864] mb-4">
            <FileText className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">e-doc</h1>
          <p className="text-sm text-gray-500 mt-1">Облачная платформа документооборота</p>
        </div>

        {/* Форма */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-6">Вход в систему</h2>

          <form onSubmit={handleSubmit((data) => mutation.mutate(data))} className="space-y-4">
            <Input
              label="Email"
              type="email"
              placeholder="name@organization.kz"
              autoComplete="email"
              required
              error={errors.email?.message}
              {...register('email')}
            />
            <Input
              label="Пароль"
              type="password"
              placeholder="••••••••"
              autoComplete="current-password"
              required
              error={errors.password?.message}
              {...register('password')}
            />

            <Button
              type="submit"
              className="w-full"
              size="lg"
              isLoading={mutation.isPending}
            >
              Войти
            </Button>
          </form>

          <div className="mt-6 space-y-2 text-center text-sm text-gray-500">
            <p>
              <Link to="/forgot-password" className="text-[#1F3864] font-medium hover:underline">
                Забыли пароль?
              </Link>
            </p>
            <p>
              Нет аккаунта?{' '}
              <Link to="/register" className="text-[#1F3864] font-medium hover:underline">
                Зарегистрироваться
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
