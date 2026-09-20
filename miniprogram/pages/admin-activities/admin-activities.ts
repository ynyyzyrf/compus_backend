import { adminDeleteActivity, adminListActivities } from '../../services/activities'
import { ensureLogin } from '../../services/auth'
import { session } from '../../utils/session'
import type { ActivityAdminOut } from '../../types/api'

Page({
  data: {
    items: [] as ActivityAdminOut[],
    loading: false,
  },

  onShow() {
    this.fetch()
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
    this.setData({ loading: true })
    try {
      const page = await adminListActivities({ page: 1, page_size: 50 })
      this.setData({ items: page.items })
    } finally {
      this.setData({ loading: false })
    }
  },

  onNew() {
    wx.navigateTo({ url: '/pages/admin-activity-editor/admin-activity-editor' })
  },
  onEdit(e: WechatMiniprogram.BaseEvent) {
    const id = e.currentTarget.dataset.id as number
    wx.navigateTo({ url: `/pages/admin-activity-editor/admin-activity-editor?id=${id}` })
  },
  onRoster(e: WechatMiniprogram.BaseEvent) {
    const id = e.currentTarget.dataset.id as number
    wx.navigateTo({ url: `/pages/admin-activity-roster/admin-activity-roster?id=${id}` })
  },
  onCheckinCode(e: WechatMiniprogram.BaseEvent) {
    const id = e.currentTarget.dataset.id as number
    wx.navigateTo({ url: `/pages/admin-activity-checkin/admin-activity-checkin?id=${id}` })
  },
  async onDelete(e: WechatMiniprogram.BaseEvent) {
    const id = Number(e.currentTarget.dataset.id)
    const r = await wx.showModal({ title: '確認刪除', content: '刪除後無法恢復' })
    if (!r.confirm) return
    try {
      await adminDeleteActivity(id)
      wx.showToast({ title: '已刪除', icon: 'success' })
      this.fetch()
    } catch (err) {
      wx.showToast({ title: (err as Error).message || '刪除失敗', icon: 'none' })
    }
  },
})
