import type {
  DirectoryTree,
  MemberBrief,
  MemberDetail,
  Page,
} from '../types/api'
import { request } from './request'
import type { AcademicSelection } from '../utils/academic'

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
): Promise<Page<MemberBrief>> {
  const query = q ? `&q=${encodeURIComponent(q)}` : ''
  const selections = Object.entries(filters).map(([key, value]) => `&${key}=${value}`).join('')
  return request<Page<MemberBrief>>({
    url: `/directory/members?page=${page}&page_size=${pageSize}${query}${selections}${discover ? '&discover=true' : ''}`,
    silent: true,
  })
}

export function getMember(id: number): Promise<MemberDetail> {
  return request<MemberDetail>({ url: `/directory/members/${id}`, silent: true })
}
