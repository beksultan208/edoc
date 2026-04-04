// ============================================================
// ГосДок — Хуки для работы с задачами
// ============================================================

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { getTasks, completeTask, skipTask } from '@/api/tasks'
import type { TaskStatus } from '@/types'

export function useTasks(params?: { status?: TaskStatus; workspace?: string }) {
  return useQuery({
    queryKey: ['tasks', params],
    queryFn: () => getTasks(params),
    refetchInterval: 60_000,  // обновляем раз в минуту
  })
}

export function useCompleteTask() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: completeTask,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      if (data.next_task) {
        toast.success(`Задача завершена. Следующий шаг: ${data.next_task.title}`)
      } else {
        toast.success('Все шаги завершены. Документ готов к подписи!')
      }
    },
    onError: () => {
      toast.error('Не удалось завершить задачу')
    },
  })
}

export function useSkipTask() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: skipTask,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      toast.success('Задача пропущена')
    },
    onError: () => {
      toast.error('Не удалось пропустить задачу')
    },
  })
}
