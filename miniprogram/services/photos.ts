import type { PhotoOut, PhotoPage } from '../types/api'
import { request } from './request'

function qs(params: Record<string, string | number | boolean | undefined>): string {
  const parts: string[] = []
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
  })
  return parts.length ? '?' + parts.join('&') : ''
}

export function listActivityPhotos(activityId: number): Promise<PhotoOut[]> {
  return request<PhotoOut[]>({ url: `/activities/${activityId}/photos` })
}

export function submitActivityPhoto(activityId: number, fileUrl: string): Promise<PhotoOut> {
  return request<PhotoOut>({
    url: `/activities/${activityId}/photos`,
    method: 'POST',
    data: { file_url: fileUrl },
  })
}

export function listMyPhotos(params: { page?: number; page_size?: number } = {}): Promise<PhotoPage> {
  return request<PhotoPage>({ url: `/me/photos${qs(params)}` })
}

export function adminListPendingPhotos(params: { page?: number; page_size?: number } = {}): Promise<PhotoPage> {
  return request<PhotoPage>({ url: `/admin/photos/pending${qs(params)}` })
}

export function adminApprovePhoto(id: number): Promise<PhotoOut> {
  return request<PhotoOut>({ url: `/admin/photos/${id}/approve`, method: 'POST' })
}

export function adminRejectPhoto(id: number): Promise<PhotoOut> {
  return request<PhotoOut>({ url: `/admin/photos/${id}/reject`, method: 'POST' })
}
