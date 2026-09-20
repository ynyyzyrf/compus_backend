import { adminApprovePhoto, adminListPendingPhotos, adminRejectPhoto } from '../../services/photos'
import type { PhotoOut } from '../../types/api'
import { locale, t } from '../../utils/i18n'

Page({
  data: {
    lang: locale.get(),
    rows: [] as PhotoOut[],
    loading: true,
    title: '',
    empty: '',
    approveText: '',
    rejectText: '',
    approvingId: 0,
  },

  onShow() {
    this.setData({
      lang: locale.get(),
      title: t('photos.admin.title'),
      empty: t('photos.admin.empty'),
      approveText: t('photos.admin.approve_action'),
      rejectText: t('photos.admin.reject_action'),
    })
    wx.setNavigationBarTitle({ title: t('photos.admin.title') })
    this.load()
  },

  async load() {
    this.setData({ loading: true })
    try {
      const page = await adminListPendingPhotos()
      this.setData({ rows: page.items })
    } finally {
      this.setData({ loading: false })
    }
  },

  async approve(e: WechatMiniprogram.BaseEvent) {
    const id = Number(e.currentTarget.dataset.id)
    if (!id) return
    this.setData({ approvingId: id })
    try {
      await adminApprovePhoto(id)
      wx.showToast({ title: t('photos.admin.approved'), icon: 'success' })
      await this.load()
    } finally {
      this.setData({ approvingId: 0 })
    }
  },

  async reject(e: WechatMiniprogram.BaseEvent) {
    const id = Number(e.currentTarget.dataset.id)
    if (!id) return
    const res = await wx.showModal({ title: t('photos.admin.reject_confirm') })
    if (!res.confirm) return
    this.setData({ approvingId: id })
    try {
      await adminRejectPhoto(id)
      wx.showToast({ title: t('photos.admin.rejected'), icon: 'success' })
      await this.load()
    } finally {
      this.setData({ approvingId: 0 })
    }
  },
})
