import { request } from './request'

export interface ConnectionSummary {
  eligible: boolean
  discoverable: boolean
  unread: number
}

export interface ConnectionItem {
  peer_id: number
  name: string
  org_path: string
  status: 'pending' | 'accepted' | 'declined'
  incoming: boolean
  message: string
  unread: boolean
  shares_wechat: boolean
  peer_wechat_id: string | null
}

export const connectionSummary = (): Promise<ConnectionSummary> =>
  request({ url: '/connections/summary', silent: true })

export const updateDiscoverability = (discoverable: boolean): Promise<{ discoverable: boolean }> =>
  request({ url: '/connections/preferences', method: 'PUT', data: { discoverable }, silent: true })

export const listConnections = (): Promise<ConnectionItem[]> =>
  request({ url: '/connections', silent: true })

export const markRequestsRead = (peerIds: number[]): Promise<void> =>
  request({ url: '/connections/read', method: 'POST', data: { peer_ids: peerIds }, silent: true })

export const sendConnectionRequest = (id: number, message: string): Promise<void> =>
  request({ url: `/connections/${id}/request`, method: 'POST', data: { message }, silent: true })

export const respondToRequest = (id: number, action: 'accept' | 'decline'): Promise<void> =>
  request({ url: `/connections/${id}/respond`, method: 'POST', data: { action }, silent: true })

export const shareWechat = (id: number, share: boolean): Promise<void> =>
  request({ url: `/connections/${id}/wechat`, method: 'PUT', data: { share }, silent: true })
