import { listRelays } from '../../services/relays'
import type { RelayListItem } from '../../types/api'
import { locale, t } from '../../utils/i18n'

type RelayCard = RelayListItem & {
  deadlineText: string
  responseText: string
  statusText: string
}

function fmt(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const M = String(d.getMonth() + 1).padStart(2, '0')
  const D = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const m = String(d.getMinutes()).padStart(2, '0')
  return `${d.getFullYear()}-${M}-${D} ${h}:${m}`
}

function toCard(item: RelayListItem): RelayCard {
  return {
    ...item,
    deadlineText: fmt(item.deadline),
    responseText: t('relays.responses', { count: item.response_count }),
    statusText: t(`relays.status.${item.status}`),
  }
}

Page({
  data: {
    lang: locale.get(),
    loading: false,
    items: [] as RelayCard[],
  },

  onLoad() {
    this.fetch()
  },

  onShow() {
    this.setData({ lang: locale.get() })
  },

  onPullDownRefresh() {
    this.fetch().finally(() => wx.stopPullDownRefresh())
  },

  async fetch() {
    this.setData({ loading: true })
    try {
      const items = await listRelays({ page_size: 50 })
      this.setData({ items: items.map(toCard) })
    } catch (e) {
      wx.showToast({ title: (e as Error).message || t('relays.load_failed'), icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  onItemTap(e: WechatMiniprogram.BaseEvent) {
    const id = Number(e.currentTarget.dataset.id)
    if (!Number.isFinite(id)) return
    wx.navigateTo({ url: `/pages/relay-detail/relay-detail?id=${id}` })
  },
})
