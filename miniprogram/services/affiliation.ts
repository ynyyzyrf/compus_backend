import type { Affiliation, AffiliationOption } from '../types/api'
import { request } from './request'

export function getMyAffiliation(): Promise<Affiliation> {
  return request<Affiliation>({ url: '/me/affiliation', silent: true })
}

export function getAffiliationOptions(): Promise<AffiliationOption[]> {
  return request<AffiliationOption[]>({ url: '/me/affiliation/options' })
}

export function submitAffiliation(classId: number, name: string): Promise<Affiliation> {
  return request<Affiliation>({
    url: '/me/affiliation',
    method: 'POST',
    data: { class_id: classId, name },
    silent: true,
  })
}
