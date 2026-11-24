import { ensureLogin, goLogin } from '../../services/auth'
import { getMyAffiliation } from '../../services/affiliation'
import { listActivities } from '../../services/activities'
import { listArticles } from '../../services/articles'
import type { ActivityListItem, Affiliation, ArticleListItem } from '../../types/api'
import { t } from '../../utils/i18n'
import { session } from '../../utils/session'

type HomeArticle = ArticleListItem & { dateText: string }
type HomeActivity = ActivityListItem & { timeText: string; statusText: string; canSignUp: boolean; previewUrl: string }
const DEFAULT_ACTIVITY_PREVIEW = '/assets/campus-hero.jpg'

function fmtDateTime(iso: string | null): string {
  if (!iso) return ''
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hour = String(date.getHours()).padStart(2, '0')
  const minute = String(date.getMinutes()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day} ${hour}:${minute}`
}

function toHomeArticle(item: ArticleListItem): HomeArticle {
  return { ...item, dateText: fmtDateTime(item.publish_at || item.created_at).slice(0, 10) }
}

function toHomeActivity(item: ActivityListItem, now: number): HomeActivity {
  let statusText = t(`activities.status.${item.status}`)
  let canSignUp = false
  if (item.status === 'signing') {
    if (Date.parse(item.signup_start_at) > now) statusText = '报名未开始'
    else if (item.capacity !== null && item.signup_count >= item.capacity) statusText = '名额已满'
    else canSignUp = true
  } else if (item.status === 'upcoming') {
    statusText = '报名已截止'
  }

  const start = fmtDateTime(item.start_at)
  return {
    ...item,
    timeText: start ? start.slice(5).replace('-', '/') : '',
    statusText,
    canSignUp,
    previewUrl: item.cover_url?.trim() || DEFAULT_ACTIVITY_PREVIEW,
  }
}

function recentActivities(items: ActivityListItem[]) {
  const upcoming = items.filter(item => item.status !== 'finished' && item.status !== 'draft')
    .sort((a, b) => Date.parse(a.start_at) - Date.parse(b.start_at))
  const finished = items.filter(item => item.status === 'finished')
    .sort((a, b) => Date.parse(b.start_at) - Date.parse(a.start_at))
  return [...upcoming, ...finished].slice(0, 3)
}

Page({
  data: {
    isGuest: false,
    affiliation: null as Affiliation | null,
    pinnedArticle: null as HomeArticle | null,
    latestArticles: [] as HomeArticle[],
    latestActivities: [] as HomeActivity[],
    contentLoading: true,
    contentFailed: false,
    contentRequest: 0,
  },

  async onShow() {
    if (typeof this.getTabBar === 'function') this.getTabBar()?.setData({ value: 'home' })
    const user = await ensureLogin().catch(() => null)
    if (!user) {
      goLogin()
      return
    }

    const isGuest = session.isGuest()
    this.setData({ isGuest, affiliation: null })
    if (isGuest) {
      this.setData({ pinnedArticle: null, latestArticles: [], latestActivities: [], contentLoading: false, contentFailed: false })
      return
    }

    let canFindClass = false
    try {
      const affiliation = await getMyAffiliation()
      this.setData({ affiliation })
      canFindClass = !affiliation.class_id && !affiliation.pending_class_id
      if (canFindClass) {
        wx.reLaunch({ url: '/pages/org-select/org-select' })
        return
      }
    } catch (error) {
      if (user.role !== 'super_admin') {
        wx.showToast({ title: (error as Error).message || '组织资料载入失败', icon: 'none' })
        return
      }
    }

    void this.fetchHomeContent()
    const app = getApp<IAppOption>()
    if (app.globalData.pendingOnboarding && !canFindClass) {
      app.globalData.pendingOnboarding = false
      wx.navigateTo({ url: '/pages/profile-setup/profile-setup' })
    }
  },

  goSignIn() { goLogin() },

  goFindAlumni() {
    if (this.data.isGuest) { goLogin(); return }
    const { globalData } = getApp<IAppOption>()
    globalData.openDirectoryDiscovery = true
    wx.switchTab({
      url: '/pages/directory/directory',
      fail: () => { delete globalData.openDirectoryDiscovery },
    })
  },

  goFindClass() {
    if (this.data.isGuest) { goLogin(); return }
    const { affiliation } = this.data
    if (affiliation?.class_id) {
      wx.showModal({ title: '我的组织', content: affiliation.org_path, showCancel: false })
      return
    }
    wx.navigateTo({ url: '/pages/org-select/org-select' })
  },

  goActivities() { wx.switchTab({ url: '/pages/activities/activities' }) },
  goArticles() { wx.navigateTo({ url: '/pages/article-list/article-list' }) },
  goArticleDetail(e: WechatMiniprogram.BaseEvent) {
    const id = Number(e.currentTarget.dataset.id)
    if (Number.isInteger(id) && id > 0) wx.navigateTo({ url: `/pages/article-detail/article-detail?id=${id}` })
  },
  goActivityDetail(e: WechatMiniprogram.BaseEvent) {
    const id = Number(e.currentTarget.dataset.id)
    if (!Number.isInteger(id) || id <= 0) {
      wx.showToast({ title: '活动信息异常', icon: 'none' })
      return
    }
    wx.navigateTo({
      url: `/pages/activity-detail/activity-detail?id=${id}`,
      fail: (error) => {
        console.error('open activity detail failed', error)
        wx.showToast({ title: '无法打开活动详情', icon: 'none' })
      },
    })
  },
  onActivityPreviewError(e: WechatMiniprogram.BaseEvent) {
    const { id, src } = e.currentTarget.dataset
    if (src === DEFAULT_ACTIVITY_PREVIEW) return
    const index = this.data.latestActivities.findIndex(row => row.id === Number(id) && row.previewUrl === src)
    if (index >= 0) {
      this.setData({ [`latestActivities[${index}].previewUrl`]: DEFAULT_ACTIVITY_PREVIEW })
    }
  },

  onArticleCoverError(e: WechatMiniprogram.BaseEvent) {
    const index = this.data.latestArticles.findIndex(row => row.id === Number(e.currentTarget.dataset.id))
    if (index >= 0 && this.data.latestArticles[index].cover_url) {
      this.setData({ [`latestArticles[${index}].cover_url`]: null })
    }
  },

  async fetchHomeContent() {
    const token = session.getToken()
    const contentRequest = this.data.contentRequest + 1
    this.setData({ contentRequest, contentLoading: true, contentFailed: false })
    const silent = { silent: true }
    const [articleResult, activityResult] = await Promise.allSettled([
      listArticles({ page_size: 5 }, silent),
      listActivities({ page_size: 20 }, silent),
    ])
    if (this.data.contentRequest !== contentRequest || this.data.isGuest || session.getToken() !== token) return

    const articles = articleResult.status === 'fulfilled' ? articleResult.value : []
    const activities = activityResult.status === 'fulfilled' ? activityResult.value : []
    const pinned = articles.find(item => item.is_pinned)
    const now = Date.now()
    this.setData({
      pinnedArticle: pinned ? toHomeArticle(pinned) : null,
      latestArticles: articles.filter(item => item.id !== pinned?.id).slice(0, 3).map(toHomeArticle),
      latestActivities: recentActivities(activities).map(item => toHomeActivity(item, now)),
      contentLoading: false,
      contentFailed: articleResult.status === 'rejected' || activityResult.status === 'rejected',
    })
  },
})
