import type { MyProfile, MyProfileUpdate } from '../types/api'
import { request } from './request'

export function getMyProfile(): Promise<MyProfile> {
  return request<MyProfile>({ url: '/me/profile' })
}

export function updateMyProfile(payload: MyProfileUpdate): Promise<MyProfile> {
  return request<MyProfile>({
    url: '/me/profile',
    method: 'PUT',
    data: payload as unknown as Record<string, unknown>,
  })
}
