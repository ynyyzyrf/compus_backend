import {
  adminDeleteArticle,
  adminListArticles,
} from '../../services/articles'
import { ensureLogin } from '../../services/auth'
import { session } from '../../utils/session'
import type { ArticleAdminOut } from '../../types/api'

const STATUS_TABS = [
  { key: '', label: '全部' },
  { key: 'published', label: '已發布' },
  { key: 'draft', label: '草稿' },
  { key: 'offline', label: '已下架' },
]

Page({
  data: {
    tabs: STATUS_TABS,
    current: 0,
    items: [] as ArticleAdminOut[],
    total: 0,
    loading: false,
  },

  onShow() {
    if (!this.data.items.length) this.fetch()
    else this.fetch()
  },

  onPullDownRefresh() {
    this.fetch().finally(() => wx.stopPullDownRefresh())
  },

  async fetch() {
    const user = await ensureLogin().catch(() => session.getUser())
    if (!user || user.role !== 'super_admin') {
      wx.showToast({ title: '僅超級管理員可進入', icon: 'none' })
      setTimeout(() => wx.navigateBack(), 800)
      return
    }
    const status = STATUS_TABS[this.data.current].key as 'draft' | 'published' | 'offline' | undefined
    this.setData({ loading: true })
    try {
      const page = await adminListArticles({ status, page: 1, page_size: 50 })
      this.setData({ items: page.items, total: page.total })
    } finally {
      this.setData({ loading: false })
    }
  },

  onTabChange(e: WechatMiniprogram.CustomEvent<{ value: number }>) {
    this.setData({ current: e.detail.value })
    this.fetch()
  },

  onNew() {
    wx.navigateTo({ url: '/pages/admin-article-editor/admin-article-editor' })
  },

  onEdit(e: WechatMiniprogram.BaseEvent) {
    const id = e.currentTarget.dataset.id as number
    wx.navigateTo({ url: `/pages/admin-article-editor/admin-article-editor?id=${id}` })
  },

  async onDelete(e: WechatMiniprogram.BaseEvent) {
    const id = Number(e.currentTarget.dataset.id)
    const res = await wx.showModal({
      title: '確認刪除',
      content: '刪除後無法恢復，確定嗎？',
    })
    if (!res.confirm) return
    try {
      await adminDeleteArticle(id)
      wx.showToast({ title: '已刪除', icon: 'success' })
      this.fetch()
    } catch (err) {
      wx.showToast({ title: (err as Error).message || '刪除失敗', icon: 'none' })
    }
  },
})
