import type {
  DashboardStats,
  DirectoryPermissionItem,
  DirectoryPermissionOut,
  MemberAdminOut,
  MemberListPage,
  OrgNodeAdminOut,
} from '../types/api'
import { request } from './request'

function qs(params: Record<string, string | number | boolean | undefined>): string {
  const parts: string[] = []
  Object.entries(params).forEach(([k, v]) => {
    if (v === undefined || v === null || v === '') return
    parts.push(`${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
  })
  return parts.length ? '?' + parts.join('&') : ''
}

// ===== dashboard =====
export function getDashboard(): Promise<DashboardStats> {
  return request<DashboardStats>({ url: '/admin/dashboard' })
}

// ===== members =====
export interface AffiliationReviewItem {
  user_id: number
  name: string
  verified_phone: string | null
  class_id: number
  org_path: string
  requested_at: string | null
}

export function listAffiliationRequests(): Promise<AffiliationReviewItem[]> {
  return request<AffiliationReviewItem[]>({ url: '/admin/affiliation-requests' })
}

export function reviewAffiliation(userId: number, action: 'approve' | 'reject'): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>({ url: `/admin/affiliation-requests/${userId}/${action}`, method: 'POST' })
}

export function listMembers(params: {
  q?: string
  role?: 'user' | 'class_admin' | 'super_admin'
  status?: 'active' | 'disabled'
  college_id?: number
  department_id?: number
  page?: number
  page_size?: number
} = {}): Promise<MemberListPage> {
  return request<MemberListPage>({
    url: `/admin/members${qs(params as Record<string, string | number | boolean | undefined>)}`,
  })
}

export function updateMember(
  id: number,
  payload: Partial<MemberAdminOut>,
): Promise<MemberAdminOut> {
  return request<MemberAdminOut>({
    url: `/admin/members/${id}`,
    method: 'PUT',
    data: payload as unknown as Record<string, unknown>,
  })
}

export function setMemberStatus(
  id: number,
  status: 'active' | 'disabled',
): Promise<MemberAdminOut> {
  return request<MemberAdminOut>({
    url: `/admin/members/${id}/status`,
    method: 'POST',
    data: { status },
  })
}

// ===== organizations =====
export function listOrganizations(): Promise<OrgNodeAdminOut[]> {
  return request<OrgNodeAdminOut[]>({ url: '/admin/organizations' })
}

export interface ClassAdministrator {
  id: number
  name: string
  status: 'active' | 'disabled'
}

export interface ClassAdministratorList {
  class_id: number
  class_name: string
  items: ClassAdministrator[]
}

export interface ClassAdministratorCandidate { id: number; name: string; org_path: string }
export interface ClassAdministratorCandidates { items: ClassAdministratorCandidate[]; total: number; page: number; page_size: number }

export function listClassAdministrators(classId: number): Promise<ClassAdministratorList> {
  return request({ url: `/admin/organizations/${classId}/class-admins` })
}

export function listClassAdministratorCandidates(classId: number, q: string, page = 1): Promise<ClassAdministratorCandidates> {
  return request({ url: `/admin/organizations/${classId}/class-admin-candidates${qs({ q, page, page_size: 20 })}` })
}

export function addClassAdministrator(classId: number, userId: number): Promise<ClassAdministratorList> {
  return request({ url: `/admin/organizations/${classId}/class-admins`, method: 'POST', data: { user_id: userId } })
}

export function removeClassAdministrator(classId: number, userId: number): Promise<ClassAdministratorList> {
  return request({ url: `/admin/organizations/${classId}/class-admins/${userId}`, method: 'DELETE' })
}

export interface OrgNodePayload {
  name: string
  type: OrgNodeAdminOut['type']
  parent_id: number | null
  sort_order?: number
  entry_year?: number | null
}

export function createOrganization(
  payload: OrgNodePayload,
): Promise<OrgNodeAdminOut> {
  return request<OrgNodeAdminOut>({
    url: '/admin/organizations',
    method: 'POST',
    data: payload as unknown as Record<string, unknown>,
  })
}

export function updateOrganization(
  id: number,
  payload: Partial<{ name: string; parent_id: number | null; sort_order: number; status: 'active' | 'disabled'; entry_year: number | null }>,
): Promise<OrgNodeAdminOut> {
  return request<OrgNodeAdminOut>({
    url: `/admin/organizations/${id}`,
    method: 'PUT',
    data: payload as unknown as Record<string, unknown>,
  })
}

export function deleteOrganization(id: number): Promise<void> {
  return request<void>({ url: `/admin/organizations/${id}`, method: 'DELETE', silent: true })
}

export interface MissingClassItem {
  user_id: number
  name: string
  note: string
}

export function listMissingClasses(): Promise<MissingClassItem[]> {
  return request({ url: '/admin/missing-classes', silent: true })
}

export function resolveMissingClass(id: number): Promise<void> {
  return request({ url: `/admin/missing-classes/${id}/resolve`, method: 'POST', silent: true })
}

// ===== directory permissions =====
export function listDirectoryPermissions(): Promise<DirectoryPermissionOut[]> {
  return request<DirectoryPermissionOut[]>({ url: '/admin/directory-permissions' })
}

export function saveDirectoryPermissions(
  permissions: DirectoryPermissionItem[],
): Promise<DirectoryPermissionOut[]> {
  return request<DirectoryPermissionOut[]>({
    url: '/admin/directory-permissions',
    method: 'PUT',
    data: { permissions },
  })
}
