import type {
  DirectoryTree,
  MemberBrief,
  MemberDetail,
  Page,
} from '../types/api'
import { request } from './request'
import type { AcademicSelection } from '../utils/academic'

export type DirectoryCategory = 'all' | 'city' | 'profession'
export type DirectoryRelation = 'class' | 'year' | 'department' | 'college'

/** 後端已按當前用戶可讀範圍裁剪過組織樹。 */
export function getDirectoryTree(): Promise<DirectoryTree> {
  return request<DirectoryTree>({ url: '/directory/tree' })
}

export function searchMembers(
  q: string,
  page = 1,
  pageSize = 50,
  filters: AcademicSelection = {},
  discover = false,
  category: DirectoryCategory = 'all',
  relation?: DirectoryRelation,
): Promise<Page<MemberBrief>> {
  const query = q ? `&q=${encodeURIComponent(q)}` : ''
  const selections = Object.entries(filters).map(([key, value]) => `&${key}=${value}`).join('')
  const categoryParam = category === 'all' ? '' : `&category=${category}`
  return request<Page<MemberBrief>>({
    url: `/directory/members?page=${page}&page_size=${pageSize}${query}${selections}${discover ? '&discover=true' : ''}${categoryParam}${relation ? `&relation=${relation}` : ''}`,
    silent: true,
  })
}

export function getMember(id: number): Promise<MemberDetail> {
  return request<MemberDetail>({ url: `/directory/members/${id}`, silent: true })
}
