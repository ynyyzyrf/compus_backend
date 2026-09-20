import { IS_DEV } from '../../config/env'
import {
  devImpersonate,
  ensureLogin,
  goLogin,
  listDevUsers,
} from '../../services/auth'
import { locale, t } from '../../utils/i18n'
import { session } from '../../utils/session'
import type { DevUser, UserProfile } from '../../types/api'

Page({
  data: {
    lang: locale.get(),
    user: null as UserProfile | null,
    initial: '·',
    isAdmin: false,
    isDev: IS_DEV,
    devUsers: [] as DevUser[],
    langLabel: '',
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
    const user = await ensureLogin().catch(() => null)
    if (!user) {
      goLogin()
      return
    }
    this.setData({
      user,
      initial: user.name.charAt(0) || '·',
      isAdmin: user.role === 'super_admin',
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
      this.setData({
        user,
        initial: user.name.charAt(0) || '·',
        isAdmin: user.role === 'super_admin',
      })
      wx.showToast({ title: `${user.name}`, icon: 'success' })
    } finally {
      wx.hideLoading()
    }
  },

  onSwitchLang() {
    const next = locale.get() === 'zh-TW' ? 'zh-CN' : 'zh-TW'
    locale.set(next)
    // sync to globalData so the wxs filter renders correctly after reLaunch
    const app = getApp<IAppOption>()
    if (app) app.globalData.locale = next
    wx.showToast({ title: t('mine.lang.switched'), icon: 'success' })
    setTimeout(() => wx.reLaunch({ url: '/pages/mine/mine' }), 300)
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
