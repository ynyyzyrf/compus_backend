import { ensureLogin, goLogin } from '../../services/auth'
import { listActivities } from '../../services/activities'
import { listArticles } from '../../services/articles'
import { listRelays } from '../../services/relays'
import type { ActivityListItem, ArticleListItem, RelayListItem } from '../../types/api'
import { locale, t } from '../../utils/i18n'

type HomeArticle = ArticleListItem & {
  dateText: string
}

type HomeActivity = ActivityListItem & {
  timeText: string
}

type HomeRelay = RelayListItem & {
  responseText: string
  deadlineText: string
}

function fmtDateTime(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const y = d.getFullYear()
  const M = String(d.getMonth() + 1).padStart(2, '0')
  const D = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const m = String(d.getMinutes()).padStart(2, '0')
  return `${y}.${M}.${D} ${h}:${m}`
}

function toHomeRelay(item: RelayListItem): HomeRelay {
  const deadline = fmtDateTime(item.deadline)
  return {
    ...item,
    responseText: t('relays.responses', { count: item.response_count }),
    deadlineText: deadline ? `${t('relays.deadline')} ${deadline}` : '',
  }
}

function toHomeArticle(item: ArticleListItem): HomeArticle {
  return {
    ...item,
    dateText: fmtDateTime(item.publish_at || item.created_at).slice(0, 10).replace(/\./g, '-'),
  }
}

function toHomeActivity(item: ActivityListItem): HomeActivity {
  const start = fmtDateTime(item.start_at)
  return {
    ...item,
    timeText: start ? start.slice(5, 16).replace('.', '/') : '',
  }
}

Page({
  data: {
    lang: locale.get(),
    name: '',
    latestArticles: [] as HomeArticle[],
    latestActivities: [] as HomeActivity[],
    latestRelay: null as HomeRelay | null,
  },

  async onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar()?.setData({ value: 'home' })
    }
    const user = await ensureLogin().catch(() => null)
    if (!user) {
      goLogin()
      return
    }
    this.setData({ lang: locale.get(), name: user?.name || '校友' })
    this.fetchHomeContent()

    // 首次進入：跳轉到個人名片引導
    const app = getApp<IAppOption>()
    if (app.globalData.pendingOnboarding) {
      app.globalData.pendingOnboarding = false
      wx.navigateTo({ url: '/pages/profile-setup/profile-setup' })
    }
  },

  onReady() {
    // 登錄返回後 onShow 會刷新稱呼。
  },

  goTab(e: WechatMiniprogram.BaseEvent) {
    const tab = e.currentTarget.dataset.tab as string
    wx.switchTab({ url: `/pages/${tab}/${tab}` })
  },
  goArticles() {
    wx.navigateTo({ url: '/pages/article-list/article-list' })
  },
  goArticleDetail(e: WechatMiniprogram.BaseEvent) {
    const id = Number(e.currentTarget.dataset.id)
    if (!Number.isFinite(id)) return
    wx.navigateTo({ url: `/pages/article-detail/article-detail?id=${id}` })
  },
  goActivityDetail(e: WechatMiniprogram.BaseEvent) {
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
  goRelays() {
    wx.navigateTo({ url: '/pages/relay-list/relay-list' })
  },
  goRelayDetail(e: WechatMiniprogram.BaseEvent) {
    const id = Number(e.currentTarget.dataset.id)
    if (!Number.isFinite(id)) return
    wx.navigateTo({ url: `/pages/relay-detail/relay-detail?id=${id}` })
  },
  async fetchHomeContent() {
    const [articles, relays, activities] = await Promise.all([
      listArticles({ page_size: 2 }).catch(() => []),
      listRelays({ status: 'open', page_size: 1 }).catch(() => []),
      listActivities({ page_size: 3 }).catch(() => []),
    ])
    this.setData({
      latestArticles: articles.map(toHomeArticle),
      latestRelay: relays[0] ? toHomeRelay(relays[0]) : null,
      latestActivities: activities.map(toHomeActivity),
    })
  },
  comingSoon() {
    wx.showToast({ title: '模塊開發中', icon: 'none' })
  },
})
