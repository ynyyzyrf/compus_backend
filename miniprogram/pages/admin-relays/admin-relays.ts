import { adminDeleteRelay, adminListRelays } from '../../services/relays'
import type { RelayListItem } from '../../types/api'
import { locale, t } from '../../utils/i18n'

type RelayAdminCard = RelayListItem & {
  statusText: string
  responseText: string
  deadlineText: string
}

function fmt(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const M = String(d.getMonth() + 1).padStart(2, '0')
  const D = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${M}-${D}`
}

function toCard(item: RelayListItem): RelayAdminCard {
  return {
    ...item,
    statusText: t(`relays.status.${item.status}`),
    responseText: t('relays.responses', { count: item.response_count }),
    deadlineText: fmt(item.deadline),
  }
}

Page({
  data: {
    lang: locale.get(),
    items: [] as RelayAdminCard[],
    loading: false,
  },

  onShow() {
    this.setData({ lang: locale.get() })
    this.fetch()
  },

  async fetch() {
    this.setData({ loading: true })
    try {
      const page = await adminListRelays({ page_size: 50 })
      this.setData({ items: page.items.map(toCard) })
    } finally {
      this.setData({ loading: false })
    }
  },

  onNew() {
    wx.navigateTo({ url: '/pages/admin-relay-editor/admin-relay-editor' })
  },

  onEdit(e: WechatMiniprogram.BaseEvent) {
    const id = Number(e.currentTarget.dataset.id)
    wx.navigateTo({ url: `/pages/admin-relay-editor/admin-relay-editor?id=${id}` })
  },

  onResponses(e: WechatMiniprogram.BaseEvent) {
    const id = Number(e.currentTarget.dataset.id)
    wx.navigateTo({ url: `/pages/admin-relay-responses/admin-relay-responses?id=${id}` })
  },

  async onDelete(e: WechatMiniprogram.BaseEvent) {
    const id = Number(e.currentTarget.dataset.id)
    const r = await wx.showModal({ title: t('common.delete'), content: t('relays.delete_confirm') })
    if (!r.confirm) return
    await adminDeleteRelay(id)
    wx.showToast({ title: t('common.saved'), icon: 'success' })
    this.fetch()
  },
})
