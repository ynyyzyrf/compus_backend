import { listActivityPhotos, submitActivityPhoto } from '../../services/photos'
import type { PhotoOut } from '../../types/api'
import { locale, t } from '../../utils/i18n'

Page({
  data: {
    lang: locale.get(),
    activityId: 0,
    photos: [] as PhotoOut[],
    loading: true,
    uploading: false,
    copy: {
      title: '',
      empty: '',
      upload: '',
    },
  },

  onLoad(opts: Record<string, string | undefined>) {
    const id = Number(opts.id)
    this.setData({ activityId: Number.isFinite(id) ? id : 0 })
    this.syncCopy()
    if (id) this.load()
  },

  onPullDownRefresh() {
    this.load().finally(() => wx.stopPullDownRefresh())
  },

  syncCopy() {
    this.setData({
      lang: locale.get(),
      copy: {
        title: t('photos.album.title'),
        empty: t('photos.album.empty'),
        upload: t('photos.album.upload'),
      },
    })
    wx.setNavigationBarTitle({ title: t('photos.album.title') })
  },

  async load() {
    if (!this.data.activityId) return
    this.setData({ loading: true })
    try {
      const photos = await listActivityPhotos(this.data.activityId)
      this.setData({ photos })
    } finally {
      this.setData({ loading: false })
    }
  },

  async onUpload() {
    if (this.data.uploading || !this.data.activityId) return
    try {
      const res = await wx.chooseMedia({
        count: 1,
        mediaType: ['image'],
        sourceType: ['album', 'camera'],
      })
      const fileUrl = res.tempFiles[0]?.tempFilePath
      if (!fileUrl) return
      this.setData({ uploading: true })
      await submitActivityPhoto(this.data.activityId, fileUrl)
      wx.showToast({ title: t('photos.album.submitted'), icon: 'success' })
      await this.load()
    } catch {
      wx.showToast({ title: t('common.cancel'), icon: 'none' })
    } finally {
      this.setData({ uploading: false })
    }
  },
})
