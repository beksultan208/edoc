// ============================================================
// ГосДок — TypeScript типы всех сущностей БД
// Строго по разделу 3 ТЗ
// ============================================================

// ---- 3.1 organizations ----
export type OrganizationType = 'individual' | 'corporate'

export interface Organization {
  id: string
  name: string
  type: OrganizationType
  inn: string | null
  address: string | null
  owner_id: string
  created_at: string
}

// ---- 3.2 users ----
export interface User {
  id: string
  email: string
  full_name: string
  phone: string | null
  organization_id: string | null
  is_active: boolean
  is_staff: boolean
  created_at: string
  last_login: string | null
}

// ---- 3.3 workspaces ----
export type WorkspaceType = 'individual' | 'corporate'
export type WorkspaceStatus = 'active' | 'archived' | 'closed'

export interface Workspace {
  id: string
  title: string
  type: WorkspaceType
  organization: string | null
  organization_name: string | null
  created_by: string
  created_by_name: string
  status: WorkspaceStatus
  description: string | null
  deadline: string | null
  created_at: string
  members_count: number
}

export interface WorkspaceListItem {
  id: string
  title: string
  type: WorkspaceType
  organization_name: string | null
  status: WorkspaceStatus
  deadline: string | null
  created_at: string
  user_role: WorkspaceMemberRole | null
}

// ---- 3.4 workspace_members ----
export type WorkspaceMemberRole = 'owner' | 'editor' | 'signer' | 'viewer'

export interface WorkspaceMember {
  id: string
  workspace: string
  user: string
  user_email: string
  user_name: string
  role: WorkspaceMemberRole
  step_order: number | null
  joined_at: string
}

// ---- 3.5 documents ----
export type DocumentStatus = 'draft' | 'review' | 'signed' | 'archived'

export interface Document {
  id: string
  workspace: string
  workspace_title?: string
  title: string
  file_type: string
  storage_key: string
  storage_url: string | null
  current_version: string | null
  current_version_number?: number
  status: DocumentStatus
  uploaded_by: string
  uploaded_by_name?: string
  created_at: string
  updated_at: string
}

export interface DocumentListItem {
  id: string
  workspace: string
  workspace_title?: string
  title: string
  file_type: string
  status: DocumentStatus
  uploaded_by: string
  uploaded_by_name?: string
  created_at: string
  updated_at: string
  current_version_number?: number
}

// ---- 3.6 document_versions ----
export interface DocumentVersion {
  id: string
  document: string
  version_number: number
  storage_key: string
  checksum: string
  ai_changes_detected: boolean
  ai_diff_summary: AiDiffSummary | null
  created_by: string
  created_by_name?: string
  created_at: string
}

export interface AiDiffSummary {
  ai_changes_detected: boolean
  summary: string | null
  additions_count: number
  deletions_count: number
  additions_sample: string[]
  deletions_sample: string[]
}

// ---- 3.7 signatures ----
export interface Signature {
  id: string
  document: string
  user: string
  user_name: string
  signature_data: string
  certificate_id: string | null
  signed_at: string
  ip_address: string
  is_valid: boolean
}

export interface SignatureVerification {
  id: string
  is_valid: boolean
  document: {
    id: string
    title: string
    status: DocumentStatus
  }
  signer: {
    id: string | null
    full_name: string | null
    email: string | null
  }
  signed_at: string
  ip_address: string
  certificate_id: string | null
}

// ---- 3.8 comments ----
export interface Comment {
  id: string
  document: string
  author: string
  author_name?: string
  content: string
  parent: string | null
  replies?: Comment[]
  is_resolved: boolean
  created_at: string
}

// ---- 3.9 tasks ----
export type TaskStatus = 'pending' | 'in_progress' | 'done' | 'skipped'

export interface Task {
  id: string
  workspace: string
  workspace_title?: string
  document: string
  document_title?: string
  assigned_to: string
  assigned_to_name?: string
  step_order: number
  title: string
  status: TaskStatus
  due_date: string | null
  completed_at: string | null
}

// ---- 3.10 notifications ----
export type NotificationType =
  | 'task_assigned'
  | 'step_completed'
  | 'document_signed'
  | 'new_comment'
  | 'deadline_approaching'
  | 'document_rejected'

export interface Notification {
  id: string
  type: NotificationType
  title: string
  message: string | null
  entity_type: string | null
  entity_id: string | null
  is_read: boolean
  created_at: string
}

// ---- 3.11 monthly_reports ----
export interface MonthlyReport {
  id: string
  organization: string
  period_year: number
  period_month: number
  docs_total: number
  docs_completed: number
  docs_signed: number
  tasks_completed: number
  avg_completion_days: number | null
  report_data: Record<string, unknown> | null
  generated_at: string
}

// ============================================================
// Вспомогательные типы для API
// ============================================================

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface ApiError {
  detail?: string
  [key: string]: string | string[] | undefined
}

// Токены JWT
export interface TokenPair {
  access: string
  refresh: string
}

// Presigned upload данные
export interface PresignedUploadResponse {
  upload_url: string
  upload_fields: Record<string, string>
  storage_key: string
  expires_in: number
  meta: {
    workspace_id: string
    title: string
    file_name: string
  }
}

// Ответ на генерацию отчёта
export interface GenerateReportRequest {
  period_year: number
  period_month: number
  organization: string
}
