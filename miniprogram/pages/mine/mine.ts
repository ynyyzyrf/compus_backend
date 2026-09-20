import { IS_DEV } from '../../config/env'
import {
  devImpersonate,
  ensureLogin,
  goLogin,
  listDevUsers,
} from '../../services/auth'
import { getMyProfile } from '../../services/profile'
import { getMyAffiliation } from '../../services/affiliation'
import { locale, t } from '../../utils/i18n'
import { session } from '../../utils/session'
import type { DevUser, UserProfile } from '../../types/api'

const DEFAULT_PROFILE_NAME = '未命名校友'

Page({
  data: {
    lang: locale.get(),
    user: null as UserProfile | null,
    initial: '·',
    isGuest: false,
    needsProfileName: false,
    isAdmin: false,
    isDev: IS_DEV,
    devUsers: [] as DevUser[],
    langLabel: '',
    heroSub: '',
    affiliationText: '',
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar()?.setData({ value: 'mine' })
    }
    this.refresh()
  },

  async refresh() {
    const currentLocale = locale.get()
    this.setData({
      lang: currentLocale,
      langLabel: currentLocale === 'zh-TW' ? t('mine.lang.zh-TW') : t('mine.lang.zh-CN'),
    })
    wx.setNavigationBarTitle({ title: t('tab.mine') })
    const user = await ensureLogin().catch(() => null)
    if (!user) {
      goLogin()
      return
    }
    const isGuest = session.isGuest()
    const latestUser = !isGuest ? await getMyProfile().catch(() => user) : user
    const displayUser = {
      ...latestUser,
      name: latestUser.name === DEFAULT_PROFILE_NAME && latestUser.name_en ? latestUser.name_en : latestUser.name,
    }
    if (!isGuest) session.setUser(displayUser)
    const affiliation = !isGuest && displayUser.role !== 'super_admin'
      ? await getMyAffiliation().catch(() => null) : null
    this.setData({
      user: displayUser,
      initial: displayUser.name.charAt(0) || '·',
      isGuest,
      needsProfileName: !isGuest && displayUser.name === DEFAULT_PROFILE_NAME,
      isAdmin: displayUser.role === 'super_admin',
      heroSub: isGuest ? t('mine.member_center_sub') : '',
      affiliationText: affiliation?.pending_class_id ? `審核中：${affiliation.pending_org_path}` : '',
    })
    if (IS_DEV) this.loadDevUsers()
  },

  goAffiliation() { wx.navigateTo({ url: '/pages/org-select/org-select' }) },

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
      this.setData({
        user,
        initial: user.name.charAt(0) || '·',
        isGuest: false,
        needsProfileName: false,
        isAdmin: user.role === 'super_admin',
        heroSub: '',
      })
      wx.showToast({ title: `${user.name}`, icon: 'success' })
    } finally {
      wx.hideLoading()
    }
  },

  onSwitchLang() {
    const next = locale.get() === 'zh-TW' ? 'zh-CN' : 'zh-TW'
    locale.set(next)
    const app = getApp<IAppOption>()
    if (app) app.globalData.locale = next
    this.setData({
      lang: next,
      langLabel: next === 'zh-TW' ? t('mine.lang.zh-TW') : t('mine.lang.zh-CN'),
    })
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar()?.setData({ value: 'mine' })
      const tabBar = this.getTabBar() as WechatMiniprogram.Component.TrivialInstance & {
        refreshLocale?: () => void
      }
      tabBar.refreshLocale?.()
    }
    wx.showToast({ title: t('mine.lang.switched'), icon: 'success' })
    this.refresh()
  },

  goAdminDashboard() {
    wx.navigateTo({ url: '/pages/admin-dashboard/admin-dashboard' })
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
  goDirectory() {
    wx.switchTab({ url: '/pages/directory/directory' })
  },
  goMyUploads() {
    wx.navigateTo({ url: '/pages/my-uploads/my-uploads' })
  },
  goProfileEdit() {
    wx.navigateTo({ url: '/pages/profile-edit/profile-edit' })
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
    wx.showToast({ title: '開發中', icon: 'none' })
  },
  resetOnboarding() {
    if (!IS_DEV) return
    wx.showModal({
      title: t('mine.dev_reset_onboard'),
      content: '清空 onboarded 標記，下次進首頁會重新跳到完善名片。',
      success: ({ confirm }) => {
        if (confirm) {
          session.resetOnboarded()
          wx.showToast({ title: t('common.success'), icon: 'success' })
        }
      },
    })
  },
})
