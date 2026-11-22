import { ensureLogin, goLogin } from '../../services/auth'
import { listAffiliationRequests, listMissingClasses, resolveMissingClass, reviewAffiliation } from '../../services/admin'
import type { AffiliationReviewItem, MissingClassItem } from '../../services/admin'

Page({
  data: { items: [] as AffiliationReviewItem[], missing: [] as MissingClassItem[], loading: true, busyId: 0, error: '' },
  onShow() { this.load() },
  async load() {
    const user = await ensureLogin().catch(() => null)
    if (!user) { goLogin(); return }
    if (user.role !== 'super_admin') { wx.navigateBack(); return }
    this.setData({ loading: true, error: '' })
    try {
      const [items, missing] = await Promise.all([listAffiliationRequests(), listMissingClasses()])
      this.setData({ items, missing })
    }
    catch (error) { this.setData({ error: (error as Error).message || '载入失败' }) }
    finally { this.setData({ loading: false }) }
  },
  approve(e: WechatMiniprogram.BaseEvent) { this.review(Number(e.currentTarget.dataset.id), 'approve') },
  reject(e: WechatMiniprogram.BaseEvent) { this.review(Number(e.currentTarget.dataset.id), 'reject') },
  async resolve(e: WechatMiniprogram.BaseEvent) {
    const id = Number(e.currentTarget.dataset.id)
    if (this.data.busyId) return
    this.setData({ busyId: id })
    try {
      await resolveMissingClass(id)
      await this.load()
    } catch (error) {
      wx.showModal({ title: '处理失败', content: (error as Error).message || '请稍后重试', showCancel: false })
    } finally { this.setData({ busyId: 0 }) }
  },
  review(id: number, action: 'approve' | 'reject') {
    if (!id || this.data.busyId) return
    const item = this.data.items.find(row => row.user_id === id)
    if (!item) return
    wx.showModal({
      title: action === 'approve' ? '确认通过申请' : '确认退回申请',
      content: `${item.name}\n${item.org_path}`,
      success: async result => {
        if (!result.confirm) return
        this.setData({ busyId: id })
        try {
          await reviewAffiliation(id, action)
          wx.showToast({ title: action === 'approve' ? '已通过' : '已退回', icon: 'success' })
          await this.load()
        } catch (error) {
          wx.showModal({ title: '审核失败', content: (error as Error).message || '请稍后重试', showCancel: false })
        } finally { this.setData({ busyId: 0 }) }
      },
    })
  },
})
