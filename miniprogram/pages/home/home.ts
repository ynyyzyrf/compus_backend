import { ensureLogin, goLogin } from '../../services/auth'
import { locale } from '../../utils/i18n'

Page({
  data: {
    lang: locale.get(),
    name: '',
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
  goRelays() {
    wx.navigateTo({ url: '/pages/relay-list/relay-list' })
  },
  comingSoon() {
    wx.showToast({ title: '模塊開發中', icon: 'none' })
  },
})
