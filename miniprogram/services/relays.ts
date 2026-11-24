import type {
  RelayAdminPage,
  RelayCreatePayload,
  RelayDetail,
  RelayListItem,
  RelayResponseOut,
  RelayResponsePage,
  RelayStatus,
  RelayUpdatePayload,
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

export function listRelays(params: {
  status?: RelayStatus
  page?: number
  page_size?: number
} = {}, options: { silent?: boolean } = {}): Promise<RelayListItem[]> {
  return request<RelayListItem[]>({
    url: `/relays${qs(params as Record<string, string | number | boolean | undefined>)}`,
    silent: options.silent,
  })
}

export async function hasActiveRelay(): Promise<boolean> {
  const pageSize = 100
  for (let page = 1; ; page += 1) {
    const relays = await listRelays({ status: 'open', page, page_size: pageSize }, { silent: true })
    const now = Date.now()
    if (relays.some(relay => !relay.deadline || Date.parse(relay.deadline) >= now)) return true
    if (relays.length < pageSize) return false
  }
}

export function getRelay(id: number): Promise<RelayDetail> {
  return request<RelayDetail>({ url: `/relays/${id}` })
}

export function submitRelayResponse(
  id: number,
  response: Record<string, unknown>,
): Promise<RelayResponseOut> {
  return request<RelayResponseOut>({
    url: `/relays/${id}/responses`,
    method: 'POST',
    data: { response },
  })
}

export function adminListRelays(params: {
  status?: RelayStatus
  page?: number
  page_size?: number
} = {}): Promise<RelayAdminPage> {
  return request<RelayAdminPage>({
    url: `/admin/relays${qs(params as Record<string, string | number | boolean | undefined>)}`,
  })
}

export function adminCreateRelay(payload: RelayCreatePayload): Promise<RelayDetail> {
  return request<RelayDetail>({
    url: '/admin/relays',
    method: 'POST',
    data: payload as unknown as Record<string, unknown>,
  })
}

export function adminUpdateRelay(id: number, payload: RelayUpdatePayload): Promise<RelayDetail> {
  return request<RelayDetail>({
    url: `/admin/relays/${id}`,
    method: 'PUT',
    data: payload as unknown as Record<string, unknown>,
  })
}

export function adminDeleteRelay(id: number): Promise<void> {
  return request<void>({ url: `/admin/relays/${id}`, method: 'DELETE', silent: true })
}

export function adminRelayResponses(id: number): Promise<RelayResponsePage> {
  return request<RelayResponsePage>({ url: `/admin/relays/${id}/responses` })
}
