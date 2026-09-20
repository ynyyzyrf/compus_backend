import { listMyPhotos } from '../../services/photos'
import type { PhotoOut } from '../../types/api'
import { locale, t } from '../../utils/i18n'

type UploadView = PhotoOut & { statusText: string }

function statusText(status: string): string {
  if (status === 'approved') return t('photos.status.approved')
  if (status === 'rejected') return t('photos.status.rejected')
  return t('photos.status.pending')
}

Page({
  data: {
    lang: locale.get(),
    rows: [] as UploadView[],
    loading: true,
    title: '',
    empty: '',
  },

  onShow() {
    this.setData({
      lang: locale.get(),
      title: t('photos.my.title'),
      empty: t('photos.my.empty'),
    })
    wx.setNavigationBarTitle({ title: t('photos.my.title') })
    this.load()
  },

  async load() {
    this.setData({ loading: true })
    try {
      const page = await listMyPhotos()
      this.setData({
        rows: page.items.map((row) => ({ ...row, statusText: statusText(row.status) })),
      })
    } finally {
      this.setData({ loading: false })
    }
  },
})
