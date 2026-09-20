import {
  cancelSignup,
  checkin,
  getActivity,
  signup,
} from '../../services/activities'
import type { ActivityDetail as ActivityDetailModel } from '../../types/api'

type ActivityDetailView = ActivityDetailModel & {
  dateText: string
  endText: string
  signupEndText: string
}

function fmtDate(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const M = String(d.getMonth() + 1).padStart(2, '0')
  const D = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const m = String(d.getMinutes()).padStart(2, '0')
  return `${d.getFullYear()}-${M}-${D} ${h}:${m}`
}

Page({
  data: {
    activity: null as ActivityDetailView | null,
    loading: true,
    sheetOpen: false,
    sheetMode: 'signup' as 'signup' | 'checkin',
    phone: '',
    remark: '',
    scanToken: '',
    submitting: false,
  },

  onLoad(opts: Record<string, string | undefined>) {
    const id = Number(opts.id)
    if (!Number.isFinite(id)) {
      this.setData({ loading: false })
      return
    }
    this.load(id)
  },

  onShow() {
    if (this.data.activity) this.load(this.data.activity.id)
  },

  async load(id: number) {
    this.setData({ loading: true })
    try {
      const a = await getActivity(id)
      this.setData({
        activity: {
          ...a,
          // derived strings
          dateText: fmtDate(a.start_at),
          endText: fmtDate(a.end_at),
          signupEndText: fmtDate(a.signup_end_at),
        },
      })
      wx.setNavigationBarTitle({ title: a.title.slice(0, 14) })
    } catch {
      this.setData({ activity: null })
    } finally {
      this.setData({ loading: false })
    }
  },

  openSignupSheet() {
    this.setData({ sheetOpen: true, sheetMode: 'signup', phone: '', remark: '' })
  },
  openCheckinSheet() {
    this.setData({ sheetOpen: true, sheetMode: 'checkin', scanToken: '' })
  },
  closeSheet() {
    this.setData({ sheetOpen: false })
  },
  onPhone(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ phone: e.detail.value })
  },
  onRemark(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ remark: e.detail.value })
  },
  onScanToken(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ scanToken: e.detail.value })
  },

  async onScanCode() {
    // wx.scanCode reads QR/barcode; result text becomes the token.
    try {
      const res = await new Promise<WechatMiniprogram.ScanCodeSuccessCallbackResult>(
        (resolve, reject) => wx.scanCode({ success: resolve, fail: reject }),
      )
      this.setData({ scanToken: res.result })
    } catch {
      wx.showToast({ title: '掃碼取消', icon: 'none' })
    }
  },

  async onConfirmSignup() {
    if (this.data.submitting) return
    if (!this.data.activity) return
    this.setData({ submitting: true })
    try {
      await signup(this.data.activity.id, {
        phone: this.data.phone || null,
        remark: this.data.remark || null,
      })
      this.setData({ sheetOpen: false })
      wx.showToast({ title: '報名成功', icon: 'success' })
      this.load(this.data.activity.id)
    } catch (e) {
      wx.showToast({ title: (e as Error).message || '報名失敗', icon: 'none' })
    } finally {
      this.setData({ submitting: false })
    }
  },

  async onConfirmCheckin() {
    if (!this.data.activity) return
    const token = this.data.scanToken.trim()
    if (!token) {
      wx.showToast({ title: '請掃碼或粘貼 token', icon: 'none' })
      return
    }
    this.setData({ submitting: true })
    try {
      await checkin(this.data.activity.id, token)
      this.setData({ sheetOpen: false })
      wx.showToast({ title: '簽到成功', icon: 'success' })
      this.load(this.data.activity.id)
    } catch (e) {
      wx.showToast({ title: (e as Error).message || '簽到失敗', icon: 'none' })
    } finally {
      this.setData({ submitting: false })
    }
  },

  async onCancelSignup() {
    if (!this.data.activity) return
    const r = await wx.showModal({ title: '確認取消報名', content: '報名截止後不可取消' })
    if (!r.confirm) return
    try {
      await cancelSignup(this.data.activity.id)
      wx.showToast({ title: '已取消', icon: 'success' })
      this.load(this.data.activity.id)
    } catch (e) {
      wx.showToast({ title: (e as Error).message || '取消失敗', icon: 'none' })
    }
  },

  goAlbum() {
    if (!this.data.activity) return
    wx.navigateTo({ url: `/pages/activity-album/activity-album?id=${this.data.activity.id}` })
  },

  goPoster() {
    if (!this.data.activity) return
    wx.navigateTo({ url: `/pages/activity-poster/activity-poster?id=${this.data.activity.id}` })
  },
})
