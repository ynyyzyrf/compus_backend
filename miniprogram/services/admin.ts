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
  role?: 'user' | 'super_admin'
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

export interface OrgNodePayload {
  name: string
  type: 'school' | 'college' | 'department' | 'class'
  parent_id: number | null
  sort_order?: number
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
  payload: Partial<{ name: string; parent_id: number | null; sort_order: number; status: 'active' | 'disabled' }>,
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
