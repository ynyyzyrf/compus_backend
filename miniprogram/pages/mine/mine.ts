import { IS_DEV } from '../../config/env'
import {
  devImpersonate,
  ensureLogin,
  goLogin,
  listDevUsers,
} from '../../services/auth'
import { getMyProfile } from '../../services/profile'
import { getMyAffiliation } from '../../services/affiliation'
import { connectionSummary, updateDiscoverability } from '../../services/connections'
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
    heroSub: '',
    affiliationText: '',
    connectionsEligible: false,
    discoverable: false,
    unreadRequests: 0,
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
    const latestUser = !isGuest ? await getMyProfile().catch(() => user) : user
    const displayUser = {
      ...latestUser,
      name: latestUser.name === DEFAULT_PROFILE_NAME && latestUser.name_en ? latestUser.name_en : latestUser.name,
    }
    if (!isGuest) session.setUser(displayUser)
    const [affiliation, connections] = await Promise.all([
      !isGuest && displayUser.role !== 'super_admin' ? getMyAffiliation().catch(() => null) : null,
      !isGuest ? connectionSummary().catch(() => null) : null,
    ])
    this.setData({
      user: displayUser,
      initial: displayUser.name.charAt(0) || '·',
      isGuest,
      needsProfileName: !isGuest && displayUser.name === DEFAULT_PROFILE_NAME,
      isAdmin: displayUser.role === 'super_admin',
      heroSub: isGuest ? t('mine.member_center_sub') : '',
      affiliationText: affiliation?.pending_class_id ? affiliation.pending_org_path : '',
      connectionsEligible: connections?.eligible ?? false,
      discoverable: connections?.discoverable ?? false,
      unreadRequests: connections?.unread ?? 0,
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
  goConnections() { wx.navigateTo({ url: '/pages/connections/connections' }) },
  setDiscoverability() {
    const enabled = !this.data.discoverable
    wx.showModal({
      title: enabled ? '允许本校校友找到我' : '关闭跨院系查找',
      content: enabled
        ? '本校已审核的校友可以搜索到你的姓名、头像和班级，并发送好友申请。'
        : '关闭后，通讯录范围外的校友无法继续通过搜索找到你。',
      confirmText: enabled ? '开启' : '关闭',
      success: async ({ confirm }) => {
        if (!confirm) return
        try {
          const result = await updateDiscoverability(enabled)
          this.setData({ discoverable: result.discoverable })
        } catch (error) {
          wx.showModal({ title: '设置失败', content: (error as Error).message || '请稍后重试', showCancel: false })
        }
      },
    })
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
