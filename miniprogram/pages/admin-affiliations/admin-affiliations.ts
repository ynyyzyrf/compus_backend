import { ensureLogin, goLogin } from '../../services/auth'
import { listAffiliationRequests, reviewAffiliation } from '../../services/admin'
import type { AffiliationReviewItem } from '../../services/admin'

Page({
  data: { items: [] as AffiliationReviewItem[], loading: true, busyId: 0, error: '' },
  onShow() { this.load() },
  async load() {
    const user = await ensureLogin().catch(() => null)
    if (!user) { goLogin(); return }
    if (user.role !== 'super_admin') { wx.navigateBack(); return }
    this.setData({ loading: true, error: '' })
    try { this.setData({ items: await listAffiliationRequests() }) }
    catch (error) { this.setData({ error: (error as Error).message || '載入失敗' }) }
    finally { this.setData({ loading: false }) }
  },
  approve(e: WechatMiniprogram.BaseEvent) { this.review(Number(e.currentTarget.dataset.id), 'approve') },
  reject(e: WechatMiniprogram.BaseEvent) { this.review(Number(e.currentTarget.dataset.id), 'reject') },
  review(id: number, action: 'approve' | 'reject') {
    if (!id || this.data.busyId) return
    const item = this.data.items.find(row => row.user_id === id)
    if (!item) return
    wx.showModal({
      title: action === 'approve' ? '確認通過申請' : '確認退回申請',
      content: `${item.name}\n${item.org_path}`,
      success: async result => {
        if (!result.confirm) return
        this.setData({ busyId: id })
        try {
          await reviewAffiliation(id, action)
          wx.showToast({ title: action === 'approve' ? '已通過' : '已退回', icon: 'success' })
          await this.load()
        } catch (error) {
          wx.showModal({ title: '審核失敗', content: (error as Error).message || '請稍後重試', showCancel: false })
        } finally { this.setData({ busyId: 0 }) }
      },
    })
  },
})
