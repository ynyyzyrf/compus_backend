import { listMyActivities } from '../../services/activities'
import type { ActivityListItem } from '../../types/api'
import { locale, t } from '../../utils/i18n'

type MyActivityCard = ActivityListItem & {
  timeText: string
  countText: string
  statusText: string
  statusClass: string
}

function fmtDateTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const y = d.getFullYear()
  const M = String(d.getMonth() + 1).padStart(2, '0')
  const D = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const m = String(d.getMinutes()).padStart(2, '0')
  return `${y}.${M}.${D} ${h}:${m}`
}

function statusClass(status: string): string {
  if (status === 'signing' || status === 'ongoing') return 'primary'
  if (status === 'upcoming') return 'soft'
  return 'muted'
}

function toCard(item: ActivityListItem): MyActivityCard {
  return {
    ...item,
    timeText: `${fmtDateTime(item.start_at)} - ${fmtDateTime(item.end_at).slice(-5)}`,
    countText: t('activities.count.signup', { count: item.signup_count }),
    statusText: t(`activities.status.${item.status}`),
    statusClass: statusClass(item.status),
  }
}

Page({
  data: {
    lang: locale.get(),
    items: [] as MyActivityCard[],
    loading: false,
  },

  onLoad() {
    this.load()
  },

  onShow() {
    this.setData({ lang: locale.get() })
  },

  onPullDownRefresh() {
    this.load().finally(() => wx.stopPullDownRefresh())
  },

  async load() {
    this.setData({ loading: true })
    try {
      const items = await listMyActivities()
      this.setData({ items: items.map(toCard) })
    } catch (e) {
      wx.showToast({ title: (e as Error).message || t('activities.load_failed'), icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  onCardTap(e: WechatMiniprogram.BaseEvent) {
    const id = Number(e.currentTarget.dataset.id ?? e.target.dataset.id)
    if (!Number.isFinite(id) || id <= 0) {
      wx.showToast({ title: '活動信息異常', icon: 'none' })
      return
    }
    wx.navigateTo({
      url: `/pages/activity-detail/activity-detail?id=${id}`,
      fail: (err) => {
        console.error('open activity detail failed', err)
        wx.showToast({ title: err.errMsg || '無法打開活動詳情', icon: 'none' })
      },
    })
  },
})
