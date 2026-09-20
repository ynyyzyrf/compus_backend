import {
  adminCreateActivity,
  adminGetActivity,
  adminUpdateActivity,
} from '../../services/activities'
import type {
  ActivityCreatePayload,
  ActivityUpdatePayload,
} from '../../types/api'

interface FormState {
  title: string
  location: string
  organizer: string
  description: string
  cover_url: string
  capacity: string
  status: 'draft' | 'signing' | 'upcoming' | 'ongoing' | 'finished'
  start_at: string
  end_at: string
  signup_start_at: string
  signup_end_at: string
}

Page({
  data: {
    isEdit: false,
    activityId: 0,
    form: {
      title: '',
      location: '',
      organizer: '',
      description: '',
      cover_url: '',
      capacity: '',
      status: 'signing',
      start_at: '',
      end_at: '',
      signup_start_at: '',
      signup_end_at: '',
    } as FormState,
    saving: false,
  },

  onLoad(opts: Record<string, string | undefined>) {
    const id = Number(opts.id)
    if (Number.isFinite(id) && id > 0) {
      this.setData({ isEdit: true, activityId: id })
      wx.setNavigationBarTitle({ title: '編輯活動' })
      this.load(id)
    } else {
      wx.setNavigationBarTitle({ title: '新建活動' })
    }
  },

  async load(id: number) {
    try {
      const a = await adminGetActivity(id)
      this.setData({
        form: {
          title: a.title,
          location: a.location,
          organizer: a.organizer || '',
          description: a.description,
          cover_url: a.cover_url || '',
          capacity: a.capacity ? String(a.capacity) : '',
          status: a.status,
          start_at: this._toInput(a.start_at),
          end_at: this._toInput(a.end_at),
          signup_start_at: this._toInput(a.signup_start_at),
          signup_end_at: this._toInput(a.signup_end_at),
        },
      })
    } catch (e) {
      wx.showToast({ title: '加載失敗', icon: 'none' })
    }
  },

  // Convert ISO -> "YYYY-MM-DDTHH:mm" for the input
  _toInput(iso: string): string {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return ''
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
  },
  // "YYYY-MM-DDTHH:mm" -> ISO
  _toIso(s: string): string {
    if (!s) return ''
    const d = new Date(s)
    return Number.isNaN(d.getTime()) ? '' : d.toISOString()
  },

  onTitle(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.setData({ 'form.title': e.detail.value }) },
  onLocation(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.setData({ 'form.location': e.detail.value }) },
  onOrganizer(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.setData({ 'form.organizer': e.detail.value }) },
  onDesc(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.setData({ 'form.description': e.detail.value }) },
  onCover(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.setData({ 'form.cover_url': e.detail.value }) },
  onCapacity(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.setData({ 'form.capacity': e.detail.value }) },
  onStart(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.setData({ 'form.start_at': e.detail.value }) },
  onEnd(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.setData({ 'form.end_at': e.detail.value }) },
  onSignupStart(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.setData({ 'form.signup_start_at': e.detail.value }) },
  onSignupEnd(e: WechatMiniprogram.CustomEvent<{ value: string }>) { this.setData({ 'form.signup_end_at': e.detail.value }) },

  async onSave() {
    const f = this.data.form
    if (!f.title.trim() || !f.location.trim()) {
      wx.showToast({ title: '請填寫標題與地點', icon: 'none' })
      return
    }
    if (!this._toIso(f.start_at) || !this._toIso(f.end_at) ||
        !this._toIso(f.signup_start_at) || !this._toIso(f.signup_end_at)) {
      wx.showToast({ title: '請填寫完整時間', icon: 'none' })
      return
    }
    const capacityNum = f.capacity.trim() ? Number(f.capacity) : null
    if (capacityNum !== null && Number.isNaN(capacityNum)) {
      wx.showToast({ title: '名額需為數字', icon: 'none' })
      return
    }
    this.setData({ saving: true })
    try {
      if (this.data.isEdit) {
        const payload: ActivityUpdatePayload = {
          title: f.title.trim(),
          location: f.location.trim(),
          organizer: f.organizer.trim() || null,
          description: f.description,
          cover_url: f.cover_url.trim() || null,
          capacity: capacityNum,
          start_at: this._toIso(f.start_at),
          end_at: this._toIso(f.end_at),
          signup_start_at: this._toIso(f.signup_start_at),
          signup_end_at: this._toIso(f.signup_end_at),
        }
        await adminUpdateActivity(this.data.activityId, payload)
      } else {
        const payload: ActivityCreatePayload = {
          title: f.title.trim(),
          location: f.location.trim(),
          organizer: f.organizer.trim() || null,
          description: f.description,
          cover_url: f.cover_url.trim() || null,
          capacity: capacityNum,
          status: 'signing',
          start_at: this._toIso(f.start_at),
          end_at: this._toIso(f.end_at),
          signup_start_at: this._toIso(f.signup_start_at),
          signup_end_at: this._toIso(f.signup_end_at),
        }
        await adminCreateActivity(payload)
      }
      wx.showToast({ title: '已保存', icon: 'success' })
      setTimeout(() => wx.navigateBack(), 600)
    } catch (e) {
      wx.showToast({ title: (e as Error).message || '保存失敗', icon: 'none' })
    } finally {
      this.setData({ saving: false })
    }
  },
})
