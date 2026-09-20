import { listActivities } from '../../services/activities'
import { ensureLogin, goLogin } from '../../services/auth'
import type { ActivityListItem, ActivityStatus } from '../../types/api'
import { locale, t } from '../../utils/i18n'

type ActivityTabKey = 'all' | 'signup' | 'soon' | 'ended'

type ActivityCard = ActivityListItem & {
  month: string
  day: string
  timeText: string
  countText: string
  remainingText: string
  statusText: string
  statusClass: string
}

const TAB_STATUS: Record<ActivityTabKey, ActivityStatus | undefined> = {
  all: undefined,
  signup: 'signing',
  soon: 'upcoming',
  ended: 'finished',
}

function buildTabs() {
  return [
    { key: 'all' as ActivityTabKey, label: t('activities.tab.all') },
    { key: 'signup' as ActivityTabKey, label: t('activities.tab.signup') },
    { key: 'soon' as ActivityTabKey, label: t('activities.tab.soon') },
    { key: 'ended' as ActivityTabKey, label: t('activities.tab.ended') },
  ]
}

function fmtDate(iso: string): Date | null {
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? null : d
}

function fmtDateTime(iso: string): string {
  const d = fmtDate(iso)
  if (!d) return ''
  const M = String(d.getMonth() + 1).padStart(2, '0')
  const D = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const m = String(d.getMinutes()).padStart(2, '0')
  return `${d.getFullYear()}.${M}.${D} ${h}:${m}`
}

function statusText(status: ActivityStatus): string {
  return t(`activities.status.${status}`)
}

function statusClass(status: ActivityStatus): string {
  if (status === 'signing' || status === 'ongoing') return 'primary'
  if (status === 'upcoming') return 'soft'
  return 'muted'
}

function toCard(item: ActivityListItem): ActivityCard {
  const start = fmtDate(item.start_at)
  return {
    ...item,
    month: start ? `${start.getMonth() + 1}月` : '',
    day: start ? String(start.getDate()).padStart(2, '0') : '',
    timeText: `${fmtDateTime(item.start_at)} - ${fmtDateTime(item.end_at).slice(-5)}`,
    countText: t('activities.count.signup', { count: item.signup_count }),
    remainingText: item.capacity ? t('activities.count.remaining', { count: Math.max(item.capacity - item.signup_count, 0) }) : '',
    statusText: statusText(item.status),
    statusClass: statusClass(item.status),
  }
}

Page({
  data: {
    lang: locale.get(),
    current: 'all' as ActivityTabKey,
    tabs: buildTabs(),
    activities: [] as ActivityCard[],
    loading: false,
  },

  async onLoad() {
    const user = await ensureLogin().catch(() => null)
    if (!user) {
      goLogin()
      return
    }
    this.fetch()
  },

  async onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar()?.setData({ value: 'activities' })
    }
    this.setData({ lang: locale.get(), tabs: buildTabs() })
    const user = await ensureLogin().catch(() => null)
    if (!user) goLogin()
  },

  onPullDownRefresh() {
    this.fetch().finally(() => wx.stopPullDownRefresh())
  },

  async fetch() {
    this.setData({ loading: true })
    try {
      const status = TAB_STATUS[this.data.current]
      const items = await listActivities({ status, page_size: 50 })
      this.setData({ activities: items.map(toCard) })
    } catch (e) {
      wx.showToast({ title: (e as Error).message || t('activities.load_failed'), icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  onTabTap(e: WechatMiniprogram.BaseEvent) {
    const key = e.currentTarget.dataset.key as ActivityTabKey
    this.setData({ current: key })
    this.fetch()
  },

  openActivityDetail(id: number) {
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

  onCardTap(e: WechatMiniprogram.BaseEvent) {
    const id = Number(e.currentTarget.dataset.id ?? e.target.dataset.id)
    this.openActivityDetail(id)
  },

  onSignup(e: WechatMiniprogram.BaseEvent) {
    const id = Number(e.currentTarget.dataset.id ?? e.target.dataset.id)
    this.openActivityDetail(id)
  },
})
