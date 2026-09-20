import { adminRoster } from '../../services/activities'
import type { SignupList } from '../../types/api'

Page({
  data: {
    activityId: 0,
    roster: null as SignupList | null,
    loading: true,
  },

  onLoad(opts: Record<string, string | undefined>) {
    const id = Number(opts.id)
    if (Number.isFinite(id) && id > 0) {
      this.setData({ activityId: id })
      this.fetch()
    } else {
      this.setData({ loading: false })
    }
  },

  async fetch() {
    this.setData({ loading: true })
    try {
      const roster = await adminRoster(this.data.activityId)
      this.setData({ roster })
    } finally {
      this.setData({ loading: false })
    }
  },

  copyPhone(e: WechatMiniprogram.BaseEvent) {
    const phone = e.currentTarget.dataset.phone as string
    if (!phone) return
    wx.setClipboardData({ data: phone })
    wx.showToast({ title: '已複製', icon: 'success' })
  },
})
