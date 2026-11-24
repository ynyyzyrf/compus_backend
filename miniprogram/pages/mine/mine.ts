import { IS_DEV } from '../../config/env'
import {
  devImpersonate,
  ensureLogin,
  goLogin,
  listDevUsers,
  logout,
} from '../../services/auth'
import { getMyProfile } from '../../services/profile'
import { getMyAffiliation } from '../../services/affiliation'
import { connectionSummary } from '../../services/connections'
import { hasActiveRelay } from '../../services/relays'
import { locale, t } from '../../utils/i18n'
import { session } from '../../utils/session'
import { routeUnassignedUser } from '../../services/startup'
import type { DevUser, UserProfile } from '../../types/api'

const DEFAULT_PROFILE_NAME = '未命名校友'

Page({
  data: {
    lang: locale.get(),
    user: null as UserProfile | null,
    isGuest: false,
    needsProfileName: false,
    isAdmin: false,
    isClassAdmin: false,
    isDev: IS_DEV,
    devUsers: [] as DevUser[],
    heroSub: '',
    affiliationText: '',
    connectionsEligible: false,
    unreadRequests: 0,
    unreadMessages: 0,
    showRelayDot: false,
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar()?.setData({ value: 'mine' })
    }
    this.refresh()
  },

  async refresh() {
    wx.setNavigationBarTitle({ title: t('tab.mine') })
    const user = await ensureLogin().catch(() => null)
    if (!user) {
      goLogin()
      return
    }
    const isGuest = session.isGuest()
    const token = session.getToken()
    const latestUser = !isGuest ? await getMyProfile().catch(() => user) : user
    if (session.getToken() !== token) return
    const displayUser = {
      ...latestUser,
      name: latestUser.name === DEFAULT_PROFILE_NAME && latestUser.name_en ? latestUser.name_en : latestUser.name,
    }
    if (!isGuest) session.setUser(displayUser)
    const [affiliation, connections, showRelayDot] = await Promise.all([
      !isGuest && displayUser.role !== 'super_admin' ? getMyAffiliation().catch(() => null) : null,
      !isGuest ? connectionSummary().catch(() => null) : null,
      !isGuest ? hasActiveRelay().catch(() => false) : false,
    ])
    if (session.getToken() !== token) return
    this.setData({
      user: displayUser,
      isGuest,
      needsProfileName: !isGuest && displayUser.name === DEFAULT_PROFILE_NAME,
      isAdmin: displayUser.role === 'super_admin',
      isClassAdmin: displayUser.role === 'class_admin',
      heroSub: isGuest ? t('mine.member_center_sub') : '',
      affiliationText: affiliation?.pending_class_id ? affiliation.pending_org_path : '',
      connectionsEligible: connections?.eligible ?? false,
      unreadRequests: connections?.unread ?? 0,
      unreadMessages: connections?.unread_messages ?? 0,
      showRelayDot,
    })
    if (IS_DEV) this.loadDevUsers()
  },

  async loadDevUsers() {
    try {
      this.setData({ devUsers: await listDevUsers() })
    } catch {
      /* 開發接口不可用時忽略 */
    }
  },

  async onSwitchUser(e: WechatMiniprogram.BaseEvent) {
    const id = Number(e.currentTarget.dataset.id)
    if (id === this.data.user?.id) return
    wx.showLoading({ title: t('common.loading') })
    try {
      const user = await devImpersonate(id)
      if (await routeUnassignedUser()) return
      this.setData({
        user,
        isGuest: false,
        needsProfileName: false,
        isAdmin: user.role === 'super_admin',
        isClassAdmin: user.role === 'class_admin',
        heroSub: '',
        showRelayDot: false,
      })
      void this.refresh()
      wx.showToast({ title: `${user.name}`, icon: 'success' })
    } finally {
      wx.hideLoading()
    }
  },

  goAdminDashboard() {
    wx.navigateTo({ url: '/pages/admin-dashboard/admin-dashboard' })
  },
  goAffiliationReview() {
    wx.navigateTo({ url: '/pages/admin-affiliations/admin-affiliations' })
  },
  onAvatarError(e: WechatMiniprogram.BaseEvent) {
    const { id, src } = e.currentTarget.dataset
    if (src && this.data.user?.id === Number(id) && this.data.user.avatar_url === src) {
      this.setData({ 'user.avatar_url': null })
    }
  },
  goAdminArticles() {
    wx.navigateTo({ url: '/pages/admin-articles/admin-articles' })
  },
  goAdminActivities() {
    wx.navigateTo({ url: '/pages/admin-activities/admin-activities' })
  },
  goMyActivities() {
    wx.navigateTo({ url: '/pages/my-activities/my-activities' })
  },
  goRelays() {
    wx.navigateTo({ url: '/pages/relay-list/relay-list' })
  },
  goConnections() {
    const tab = this.data.unreadMessages && !this.data.unreadRequests ? '?tab=friends' : ''
    wx.navigateTo({ url: `/pages/connections/connections${tab}` })
  },
  goSettings() {
    if (this.data.isGuest) { this.goLoginIfGuest(); return }
    wx.navigateTo({ url: '/pages/settings/settings' })
  },
  goDirectory() {
    wx.switchTab({ url: '/pages/directory/directory' })
  },
  goMyUploads() {
    wx.navigateTo({ url: '/pages/my-uploads/my-uploads' })
  },
  goProfileEdit() {
    wx.navigateTo({ url: '/pages/profile-edit/profile-edit' })
  },
  goProfileCard() {
    if (this.data.isGuest) { this.goLoginIfGuest(); return }
    this.goProfileEdit()
  },
  signOut() {
    logout()
    goLogin()
  },
  goLoginIfGuest() {
    if (this.data.isGuest) {
      session.clearGuest()
      wx.reLaunch({ url: '/pages/login/login' })
      return
    }
    if (this.data.needsProfileName) this.goProfileEdit()
  },
  comingSoon() {
    wx.showToast({ title: '开发中', icon: 'none' })
  },
  resetOnboarding() {
    if (!IS_DEV) return
    wx.showModal({
      title: t('mine.dev_reset_onboard'),
      content: '清空 onboarded 标记，下次进首页会重新跳到完善名片。',
      success: ({ confirm }) => {
        if (confirm) {
          session.resetOnboarded()
          wx.showToast({ title: t('common.success'), icon: 'success' })
        }
      },
    })
  },
})
