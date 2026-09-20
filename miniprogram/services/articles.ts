import type {
  ArticleAdminOut,
  ArticleCreatePayload,
  ArticleDetail,
  ArticleListItem,
  ArticlePage,
  ArticleUpdatePayload,
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

export function listArticles(params: {
  type?: 'news' | 'announcement' | 'notice'
  pinned_only?: boolean
  page?: number
  page_size?: number
} = {}): Promise<ArticleListItem[]> {
  return request<ArticleListItem[]>({
    url: `/articles${qs(params as Record<string, string | number | boolean | undefined>)}`,
  })
}

export function getArticle(id: number): Promise<ArticleDetail> {
  return request<ArticleDetail>({ url: `/articles/${id}`, silent: true })
}

// ===== admin =====

export function adminListArticles(params: {
  status?: 'draft' | 'published' | 'offline'
  type?: 'news' | 'announcement' | 'notice'
  page?: number
  page_size?: number
} = {}): Promise<ArticlePage> {
  return request<ArticlePage>({
    url: `/admin/articles${qs(params as Record<string, string | number | boolean | undefined>)}`,
  })
}

export function adminGetArticle(id: number): Promise<ArticleAdminOut> {
  return request<ArticleAdminOut>({ url: `/admin/articles/${id}`, silent: true })
}

export function adminCreateArticle(payload: ArticleCreatePayload): Promise<ArticleAdminOut> {
  return request<ArticleAdminOut>({
    url: '/admin/articles',
    method: 'POST',
    data: payload as unknown as Record<string, unknown>,
  })
}

export function adminUpdateArticle(
  id: number,
  payload: ArticleUpdatePayload,
): Promise<ArticleAdminOut> {
  return request<ArticleAdminOut>({
    url: `/admin/articles/${id}`,
    method: 'PUT',
    data: payload as unknown as Record<string, unknown>,
  })
}

export function adminDeleteArticle(id: number): Promise<void> {
  return request<void>({ url: `/admin/articles/${id}`, method: 'DELETE', silent: true })
}
