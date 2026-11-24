import { request } from './request'

export interface ConnectionSummary {
  eligible: boolean
  discoverable: boolean
  unread: number
  unread_messages: number
}

export interface ConnectionItem {
  peer_id: number
  name: string
  org_path: string
  status: 'pending' | 'accepted' | 'declined'
  incoming: boolean
  message: string
  unread: boolean
  unread_messages: number
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

export interface FriendMessage {
  id: number
  sender_id: number
  message: string
  created_at: string
}

export interface FriendMessagePage {
  peer_name: string
  items: FriendMessage[]
  has_more: boolean
}

export const listFriendMessages = (id: number, beforeId?: number): Promise<FriendMessagePage> =>
  request({ url: `/connections/${id}/messages${beforeId ? `?before_id=${beforeId}` : ''}`, silent: true })

export const sendFriendMessage = (id: number, message: string, clientId: string): Promise<FriendMessage> =>
  request({ url: `/connections/${id}/messages`, method: 'POST', data: { message, client_id: clientId }, silent: true })

export const markFriendMessagesRead = (id: number, throughId: number): Promise<void> =>
  request({ url: `/connections/${id}/messages/read`, method: 'POST', data: { through_id: throughId }, silent: true })
