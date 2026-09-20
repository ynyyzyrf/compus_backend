import type {
  ActivityAdminOut,
  ActivityAdminPage,
  ActivityCreatePayload,
  ActivityDetail,
  ActivityListItem,
  ActivityStatus,
  ActivityUpdatePayload,
  CheckinCode,
  CheckinResult,
  SignupList,
  SignupRequest,
  SignupResult,
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

// ===== user =====

export function listActivities(params: {
  status?: ActivityStatus
  page?: number
  page_size?: number
} = {}): Promise<ActivityListItem[]> {
  return request<ActivityListItem[]>({
    url: `/activities${qs(params as Record<string, string | number | boolean | undefined>)}`,
  })
}

export function getActivity(id: number): Promise<ActivityDetail> {
  return request<ActivityDetail>({ url: `/activities/${id}` })
}

export function signup(id: number, payload: SignupRequest = {}): Promise<SignupResult> {
  return request<SignupResult>({
    url: `/activities/${id}/signup`,
    method: 'POST',
    data: payload as unknown as Record<string, unknown>,
  })
}

export function cancelSignup(id: number): Promise<void> {
  return request<void>({ url: `/activities/${id}/signup`, method: 'DELETE', silent: true })
}

export function checkin(id: number, token: string): Promise<CheckinResult> {
  return request<CheckinResult>({
    url: `/activities/${id}/checkin`,
    method: 'POST',
    data: { token },
  })
}

// ===== admin =====

export function adminListActivities(params: {
  status?: ActivityStatus
  page?: number
  page_size?: number
} = {}): Promise<ActivityAdminPage> {
  return request<ActivityAdminPage>({
    url: `/admin/activities${qs(params as Record<string, string | number | boolean | undefined>)}`,
  })
}

export function adminGetActivity(id: number): Promise<ActivityAdminOut> {
  return request<ActivityAdminOut>({ url: `/admin/activities/${id}` })
}

export function adminCreateActivity(payload: ActivityCreatePayload): Promise<ActivityAdminOut> {
  return request<ActivityAdminOut>({
    url: '/admin/activities',
    method: 'POST',
    data: payload as unknown as Record<string, unknown>,
  })
}

export function adminUpdateActivity(id: number, payload: ActivityUpdatePayload): Promise<ActivityAdminOut> {
  return request<ActivityAdminOut>({
    url: `/admin/activities/${id}`,
    method: 'PUT',
    data: payload as unknown as Record<string, unknown>,
  })
}

export function adminDeleteActivity(id: number): Promise<void> {
  return request<void>({ url: `/admin/activities/${id}`, method: 'DELETE', silent: true })
}

export function adminIssueCheckinCode(id: number): Promise<CheckinCode> {
  return request<CheckinCode>({ url: `/admin/activities/${id}/checkin-code`, method: 'POST' })
}

export function adminRoster(id: number): Promise<SignupList> {
  return request<SignupList>({ url: `/admin/activities/${id}/signups` })
}
