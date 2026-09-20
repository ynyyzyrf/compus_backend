import type {
  DirectoryTree,
  MemberBrief,
  MemberDetail,
  Page,
} from '../types/api'
import { request } from './request'

/** 後端已按當前用戶可讀範圍裁剪過組織樹。 */
export function getDirectoryTree(): Promise<DirectoryTree> {
  return request<DirectoryTree>({ url: '/directory/tree' })
}

export function searchMembers(
  q: string,
  page = 1,
  pageSize = 50,
): Promise<Page<MemberBrief>> {
  const query = q ? `&q=${encodeURIComponent(q)}` : ''
  return request<Page<MemberBrief>>({
    url: `/directory/members?page=${page}&page_size=${pageSize}${query}`,
  })
}

export function getMember(id: number): Promise<MemberDetail> {
  return request<MemberDetail>({ url: `/directory/members/${id}`, silent: true })
}
