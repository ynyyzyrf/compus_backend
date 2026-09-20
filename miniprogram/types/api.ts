// 與後端 schemas 對齊的業務類型（Walking Skeleton 只含登錄/通訊錄）。

export type Role = 'user' | 'super_admin'

export interface UserProfile {
  id: number
  name: string
  name_en?: string | null
  avatar_url: string | null
  role: Role
  status: string
  openid?: string | null
  phone?: string | null
  wechat_id?: string | null
  email?: string | null
  bio?: string | null
}

export interface DevUser {
  id: number
  name: string
  role: Role
  org_path: string
}

export interface LoginResult {
  access_token: string
  token_type: string
  user: UserProfile
}

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export type OrgType = 'school' | 'college' | 'department' | 'class'

export interface OrgNode {
  id: number
  name: string
  type: OrgType
  parent_id: number | null
  sort_order: number
  member_count: number
}

export interface DirectoryTree {
  nodes: OrgNode[]
  scope_level: 'class' | 'department' | 'college' | 'all' | 'none'
}

export interface MemberBrief {
  id: number
  name: string
  avatar_url: string | null
  class_id: number | null
  org_path: string
}

// ===== Articles (slice 2) =====

export type ArticleType = 'news' | 'announcement' | 'notice'
export type ArticleStatus = 'draft' | 'published' | 'offline'

export interface ArticleListItem {
  id: number
  type: ArticleType
  title: string
  cover_url: string | null
  summary: string | null
  is_pinned: boolean
  publish_at: string | null
  created_at: string
}

export interface ArticleDetail extends ArticleListItem {
  content: string
  author_id: number | null
}

export interface ArticleAdminOut extends ArticleDetail {
  status: ArticleStatus
  scope_ids: number[]
}

export interface ArticlePage {
  items: ArticleAdminOut[]
  total: number
  page: number
  page_size: number
}

export interface ArticleCreatePayload {
  type: ArticleType
  title: string
  content: string
  summary?: string | null
  cover_url?: string | null
  is_pinned?: boolean
  status?: ArticleStatus
  publish_at?: string | null
  scope_ids?: number[]
}

export type ArticleUpdatePayload = Partial<ArticleCreatePayload>

// ===== Profile (extended business card) =====

export interface MyProfile {
  id: number
  name: string
  name_en: string | null
  avatar_url: string | null

  phone: string | null
  wechat_id: string | null
  email: string | null

  profession: string | null
  profession_en: string | null
  position: string | null
  company_name: string | null
  company_address: string | null
  company_founded_at: string | null

  bio: string | null
  business_description: string | null
  referrals_needed: string | null
  personal_experience: string | null
  resources_offered: string | null

  chamber_chapter: string | null
  chamber_member_no: string | null
  chamber_join_date: string | null
  chamber_score: number | null

  role: Role
  status: string
}

export type MyProfileUpdate = Partial<
  Omit<MyProfile, 'id' | 'avatar_url' | 'role' | 'status'>
>

// MemberDetail now extends the same shape (minus role/status) plus class context.
export interface MemberDetail extends MyProfile {
  class_id: number | null
  org_path: string
}

// ===== Activities (slice 3) =====

export type ActivityStatus = 'draft' | 'signing' | 'upcoming' | 'ongoing' | 'finished'

export interface ActivityListItem {
  id: number
  title: string
  cover_url: string | null
  description: string
  location: string
  organizer: string | null
  start_at: string
  end_at: string
  signup_start_at: string
  signup_end_at: string
  capacity: number | null
  status: ActivityStatus
  signup_count: number
  checkin_count: number
}

export interface ActivityDetail extends ActivityListItem {
  created_by: number | null
  my_signed_up: boolean
  my_checked_in: boolean
}

export interface SignupRequest {
  phone?: string | null
  remark?: string | null
}

export interface SignupResult {
  id: number
  activity_id: number
  user_id: number
  phone: string | null
  remark: string | null
  status: string
  created_at: string
}

export interface CheckinCode {
  activity_id: number
  token: string
  expires_at: string
}

export interface CheckinResult {
  id: number
  activity_id: number
  user_id: number
  checkin_at: string
  checkin_method: string
}

export interface SignupRow {
  id: number
  user_id: number
  user_name: string
  user_org_path: string
  phone: string | null
  remark: string | null
  status: string
  created_at: string
  checked_in: boolean
  checkin_at: string | null
}

export interface SignupList {
  items: SignupRow[]
  total: number
  signup_count: number
  checkin_count: number
  checkin_rate: number
  by_college: Record<string, number>
}

export interface ActivityAdminOut extends ActivityListItem {
  created_by: number | null
}

export interface ActivityAdminPage {
  items: ActivityAdminOut[]
  total: number
  page: number
  page_size: number
}

export interface ActivityCreatePayload {
  title: string
  location: string
  description?: string
  cover_url?: string | null
  organizer?: string | null
  start_at: string
  end_at: string
  signup_start_at: string
  signup_end_at: string
  capacity?: number | null
  status?: ActivityStatus
}

export type ActivityUpdatePayload = Partial<ActivityCreatePayload>

// ===== Photos / Albums (P1) =====

export type PhotoStatus = 'pending' | 'approved' | 'rejected'

export interface PhotoOut {
  id: number
  activity_id: number
  uploader_id: number | null
  file_url: string
  status: PhotoStatus
  created_at: string
  reviewed_at: string | null
}

export interface PhotoPage {
  items: PhotoOut[]
  total: number
  page: number
  page_size: number
}

// ===== AI assistant (P1) =====

export interface AiChatResponse {
  answer: string
  tools: Record<string, unknown>
}

// ===== Relays (P1) =====

export type RelayStatus = 'open' | 'closed'
export type RelayFieldType = 'text' | 'textarea' | 'number' | 'radio' | 'checkbox' | 'date' | 'image'

export interface RelayField {
  id: number
  label: string
  field_type: RelayFieldType
  required: boolean
  options: string[] | null
  sort_order: number
}

export interface RelayListItem {
  id: number
  title: string
  description: string | null
  deadline: string | null
  status: RelayStatus
  response_count: number
  created_at: string
}

export interface RelayDetail extends RelayListItem {
  fields: RelayField[]
  my_response: Record<string, unknown> | null
}

export interface RelayResponseOut {
  id: number
  relay_id: number
  user_id: number
  response: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface RelayFieldPayload {
  label: string
  field_type: RelayFieldType
  required: boolean
  options?: string[] | null
  sort_order?: number
}

export interface RelayCreatePayload {
  title: string
  description?: string | null
  deadline?: string | null
  status?: RelayStatus
  fields: RelayFieldPayload[]
}

export type RelayUpdatePayload = Partial<RelayCreatePayload>

export interface RelayAdminPage {
  items: RelayListItem[]
  total: number
  page: number
  page_size: number
}

export interface RelayResponseRow {
  id: number
  user_id: number
  user_name: string
  response: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface RelayResponsePage {
  items: RelayResponseRow[]
  total: number
}

// ===== Admin (slice 4) =====

export interface DashboardStats {
  member_total: number
  active_member_total: number
  college_count: number
  department_count: number
  class_count: number
  signing_activity_total: number
  ongoing_activity_total: number
  recent_checkin_rate: number
}

export interface MemberAdminOut {
  id: number
  name: string
  avatar_url: string | null
  role: 'user' | 'super_admin'
  status: 'active' | 'disabled'
  openid: string | null
  unionid: string | null
  phone: string | null
  wechat_id: string | null
  email: string | null
  name_en: string | null
  profession: string | null
  profession_en: string | null
  position: string | null
  company_name: string | null
  company_address: string | null
  company_founded_at: string | null
  bio: string | null
  business_description: string | null
  referrals_needed: string | null
  personal_experience: string | null
  resources_offered: string | null
  chamber_chapter: string | null
  chamber_member_no: string | null
  chamber_join_date: string | null
  chamber_score: number | null
  primary_class_id: number | null
  primary_class_name: string | null
  primary_org_path: string
}

export interface MemberListPage {
  items: MemberAdminOut[]
  total: number
  page: number
  page_size: number
}

export interface OrgNodeAdminOut {
  id: number
  name: string
  type: 'school' | 'college' | 'department' | 'class'
  parent_id: number | null
  sort_order: number
  status: 'active' | 'disabled'
  member_count: number
}

export interface DirectoryPermissionOut {
  organization_id: number
  organization_name: string
  organization_type: string
  scope_type: 'class' | 'department' | 'college'
  is_enabled: boolean
}

export interface DirectoryPermissionItem {
  organization_id: number
  scope_type: 'class' | 'department' | 'college'
  is_enabled: boolean
}
