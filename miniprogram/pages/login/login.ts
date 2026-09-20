import { IS_DEV } from '../../config/env'
import { loginWithWechat } from '../../services/auth'
import { locale, t } from '../../utils/i18n'
import { session } from '../../utils/session'

Page({
  data: {
    lang: locale.get(),
    loading: false,
    isDev: IS_DEV,
    phoneSheetOpen: false,
    selectedPhone: '135****5123',
  },

  onShow() {
    this.setData({ lang: locale.get() })
  },

  onLogin() {
    if (this.data.loading) return
    this.setData({ phoneSheetOpen: true })
  },

  skipLogin() {
    session.enterGuest()
    const app = getApp<IAppOption>()
    app.globalData.pendingOnboarding = false
    wx.switchTab({ url: '/pages/home/home' })
  },

  closePhoneSheet() {
    this.setData({ phoneSheetOpen: false })
  },

  choosePhone(e: WechatMiniprogram.BaseEvent) {
    const phone = String(e.currentTarget.dataset.phone || '')
    this.setData({ selectedPhone: phone })
    this.confirmLogin()
  },

  managePhone() {
    wx.showToast({ title: t('login.manage_phone_tip'), icon: 'none' })
  },

  async confirmLogin() {
    if (this.data.loading) return
    this.setData({ loading: true })
    wx.showLoading({ title: t('login.loading'), mask: true })
    try {
      await loginWithWechat()
      const app = getApp<IAppOption>()
      app.globalData.pendingOnboarding = !session.hasOnboarded()
      this.setData({ phoneSheetOpen: false })
      wx.switchTab({ url: '/pages/home/home' })
    } catch (e) {
      wx.showToast({ title: (e as Error).message || t('login.fail'), icon: 'none' })
    } finally {
      wx.hideLoading()
      this.setData({ loading: false })
    }
  },
})
