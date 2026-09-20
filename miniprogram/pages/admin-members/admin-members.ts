import { listMembers, setMemberStatus } from '../../services/admin'
import { ensureLogin } from '../../services/auth'
import { session } from '../../utils/session'
import type { MemberAdminOut } from '../../types/api'

Page({
  data: {
    items: [] as MemberAdminOut[],
    total: 0,
    q: '',
    loading: false,
  },

  onShow() { this.fetch() },
  onPullDownRefresh() { this.fetch().finally(() => wx.stopPullDownRefresh()) },

  async fetch() {
    const user = await ensureLogin().catch(() => session.getUser())
    if (!user || user.role !== 'super_admin') {
      wx.showToast({ title: '僅超管可進入', icon: 'none' })
      setTimeout(() => wx.navigateBack(), 800)
      return
    }
    this.setData({ loading: true })
    try {
      const page = await listMembers({ q: this.data.q || undefined, page: 1, page_size: 100 })
      this.setData({ items: page.items, total: page.total })
    } finally {
      this.setData({ loading: false })
    }
  },

  onSearch(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ q: e.detail.value })
  },
  onSearchSubmit() { this.fetch() },
  onSearchClear() { this.setData({ q: '' }); this.fetch() },

  onEdit(e: WechatMiniprogram.BaseEvent) {
    const id = e.currentTarget.dataset.id as number
    wx.navigateTo({ url: `/pages/admin-member-edit/admin-member-edit?id=${id}` })
  },

  async onToggleStatus(e: WechatMiniprogram.BaseEvent) {
    const item = this.data.items.find((m) => m.id === e.currentTarget.dataset.id)
    if (!item) return
    const next = item.status === 'active' ? 'disabled' : 'active'
    const r = await wx.showModal({
      title: '確認',
      content: next === 'disabled' ? '停用後成員將無法登錄' : '啟用該成員',
    })
    if (!r.confirm) return
    try {
      await setMemberStatus(item.id, next)
      wx.showToast({ title: '已更新', icon: 'success' })
      this.fetch()
    } catch (err) {
      wx.showToast({ title: (err as Error).message || '失敗', icon: 'none' })
    }
  },
})
