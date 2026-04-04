// ============================================================
// ГосДок — Страница отчётов
// Список, генерация за период, экспорт PDF/XLSX
// ============================================================

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { format } from 'date-fns'
import { ru } from 'date-fns/locale'
import { BarChart2, Download, Plus, FileText } from 'lucide-react'
import toast from 'react-hot-toast'
import { Layout } from '@/components/layout/Layout'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Modal } from '@/components/ui/Modal'
import { Spinner } from '@/components/ui/Spinner'
import { getReports, generateReport, exportReport, downloadBlob } from '@/api/reports'
import { getWorkspaces } from '@/api/workspaces'
import type { MonthlyReport } from '@/types'

const MONTHS = [
  'Январь','Февраль','Март','Апрель','Май','Июнь',
  'Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь',
]

const generateSchema = z.object({
  period_year: z.coerce.number().int().min(2020).max(2030),
  period_month: z.coerce.number().int().min(1).max(12),
  organization: z.string().min(1, 'Выберите организацию'),
})
type GenerateForm = z.infer<typeof generateSchema>

export default function Reports() {
  const queryClient = useQueryClient()
  const [generateOpen, setGenerateOpen] = useState(false)
  const [exportingId, setExportingId] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['reports'],
    queryFn: () => getReports(),
  })

  // Кабинеты для выбора организации
  const { data: workspacesData } = useQuery({
    queryKey: ['workspaces'],
    queryFn: () => getWorkspaces(),
    enabled: generateOpen,
  })

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<GenerateForm>({
    resolver: zodResolver(generateSchema),
    defaultValues: {
      period_year: new Date().getFullYear(),
      period_month: new Date().getMonth() + 1,
    },
  })

  const generateMutation = useMutation({
    mutationFn: generateReport,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] })
      setGenerateOpen(false)
      reset()
      toast.success('Отчёт сгенерирован')
    },
    onError: () => toast.error('Не удалось сгенерировать отчёт'),
  })

  const handleExport = async (reportId: string, format: 'pdf' | 'xlsx') => {
    setExportingId(reportId)
    try {
      const blob = await exportReport(reportId, format)
      downloadBlob(blob, `report_${reportId}.${format}`)
      toast.success(`Отчёт экспортирован в ${format.toUpperCase()}`)
    } catch {
      toast.error('Ошибка при экспорте отчёта')
    } finally {
      setExportingId(null)
    }
  }

  const reports = data?.results ?? []

  // Кабинеты как источник для отчёта
  const orgOptions = workspacesData?.results
    ?.map((w) => ({ value: w.id, label: w.title })) ?? []

  return (
    <Layout title="Отчёты">
      <div className="flex justify-end mb-6">
        <Button onClick={() => setGenerateOpen(true)}>
          <Plus className="h-4 w-4" />
          Сгенерировать отчёт
        </Button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : reports.length === 0 ? (
        <div className="text-center py-16">
          <BarChart2 className="h-12 w-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500 font-medium">Нет отчётов</p>
          <p className="text-sm text-gray-400 mt-1">
            Отчёты генерируются автоматически 1-го числа каждого месяца
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {reports.map((report) => (
            <ReportCard
              key={report.id}
              report={report}
              isExporting={exportingId === report.id}
              onExport={(fmt) => handleExport(report.id, fmt)}
            />
          ))}
        </div>
      )}

      {/* Модал генерации */}
      <Modal
        isOpen={generateOpen}
        onClose={() => { setGenerateOpen(false); reset() }}
        title="Сгенерировать отчёт"
        size="sm"
        footer={
          <>
            <Button variant="secondary" onClick={() => setGenerateOpen(false)}>Отмена</Button>
            <Button
              onClick={handleSubmit((d) => generateMutation.mutate(d))}
              isLoading={generateMutation.isPending}
            >
              Сгенерировать
            </Button>
          </>
        }
      >
        <form className="space-y-4">
          <Input
            label="Год"
            type="number"
            min={2020}
            max={2030}
            required
            error={errors.period_year?.message}
            {...register('period_year')}
          />
          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium text-gray-700">
              Месяц <span className="text-red-500">*</span>
            </label>
            <select
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1F3864]"
              {...register('period_month')}
            >
              {MONTHS.map((m, i) => (
                <option key={i + 1} value={i + 1}>{m}</option>
              ))}
            </select>
            {errors.period_month && (
              <p className="text-xs text-red-600">{errors.period_month.message}</p>
            )}
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium text-gray-700">
              Кабинет <span className="text-red-500">*</span>
            </label>
            <select
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1F3864]"
              {...register('organization')}
            >
              <option value="">Выберите кабинет...</option>
              {orgOptions.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
            {errors.organization && (
              <p className="text-xs text-red-600">{errors.organization.message}</p>
            )}
          </div>
        </form>
      </Modal>
    </Layout>
  )
}

// ---- Карточка отчёта ----
function ReportCard({
  report,
  isExporting,
  onExport,
}: {
  report: MonthlyReport
  isExporting: boolean
  onExport: (format: 'pdf' | 'xlsx') => void
}) {
  const monthName = MONTHS[report.period_month - 1]

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex flex-col sm:flex-row sm:items-center gap-4">
        <div className="flex items-center gap-3 flex-1">
          <div className="p-2.5 rounded-lg bg-blue-50">
            <BarChart2 className="h-5 w-5 text-[#1F3864]" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">
              {monthName} {report.period_year}
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">
              Сгенерирован: {format(new Date(report.generated_at), 'd MMM yyyy, HH:mm', { locale: ru })}
            </p>
          </div>
        </div>

        {/* Метрики */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
          <Metric label="Документов" value={report.docs_total} />
          <Metric label="Завершено" value={report.docs_completed} />
          <Metric label="Подписано" value={report.docs_signed} />
          <Metric
            label="Ср. дней"
            value={report.avg_completion_days ? Number(report.avg_completion_days).toFixed(1) : '—'}
          />
        </div>

        {/* Экспорт */}
        <div className="flex gap-2 flex-shrink-0">
          <Button
            size="sm"
            variant="outline"
            onClick={() => onExport('pdf')}
            isLoading={isExporting}
          >
            <FileText className="h-4 w-4" />
            PDF
          </Button>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => onExport('xlsx')}
            isLoading={isExporting}
          >
            <Download className="h-4 w-4" />
            XLSX
          </Button>
        </div>
      </div>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div>
      <p className="text-lg font-bold text-gray-900">{value}</p>
      <p className="text-xs text-gray-400">{label}</p>
    </div>
  )
}
