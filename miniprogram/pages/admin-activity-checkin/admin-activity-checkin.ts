import { adminIssueCheckinCode } from '../../services/activities'

function fmt(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

Page({
  data: {
    activityId: 0,
    token: '',
    expiresAtText: '',
    loading: false,
  },

  onLoad(opts: Record<string, string | undefined>) {
    const id = Number(opts.id)
    if (Number.isFinite(id) && id > 0) this.setData({ activityId: id })
  },

  onShow() {
    this.refresh()
  },

  async refresh() {
    if (!this.data.activityId) return
    this.setData({ loading: true })
    try {
      const r = await adminIssueCheckinCode(this.data.activityId)
      this.setData({ token: r.token, expiresAtText: fmt(r.expires_at) })
    } catch {
      wx.showToast({ title: '生成失敗', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  copyToken() {
    if (!this.data.token) return
    wx.setClipboardData({ data: this.data.token })
    wx.showToast({ title: '已複製 token', icon: 'success' })
  },
})
