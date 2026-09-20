import { IS_DEV } from '../../config/env'
import { loginWithWechat } from '../../services/auth'
import { ApiError } from '../../services/request'
import { locale, t } from '../../utils/i18n'
import { session } from '../../utils/session'

function loginErrorMessage(error: unknown): string {
  if (error && typeof error === 'object') {
    const detail = error as { message?: unknown; errMsg?: unknown }
    if (typeof detail.message === 'string' && detail.message) return detail.message
    if (typeof detail.errMsg === 'string' && detail.errMsg) return detail.errMsg
  }
  return t('login.fail')
}

function showLoginError(message: string) {
  wx.showModal({ title: t('login.fail'), content: message, showCancel: false })
}

Page({
  data: {
    lang: locale.get(),
    loading: false,
    isDev: IS_DEV,
    phoneSheetOpen: false,
  },

  onShow() {
    this.setData({ lang: locale.get() })
    if (session.getToken() && session.getUser()) {
      wx.switchTab({ url: '/pages/home/home' })
    }
  },

  onLogin() {
    if (this.data.loading) return
    return this.confirmLogin()
  },

  openPhoneSheet() {
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

  onPhoneAuthorized(e: WechatMiniprogram.CustomEvent<{ code?: string; errMsg?: string }>) {
    const phoneCode = e.detail.code
    if (!phoneCode) {
      if (e.detail.errMsg && !e.detail.errMsg.includes('deny')) {
        showLoginError(e.detail.errMsg)
      }
      return
    }
    return this.confirmLogin(phoneCode)
  },

  async confirmLogin(phoneCode?: string) {
    if (this.data.loading) return
    this.setData({ loading: true })
    wx.showLoading({ title: t('login.loading'), mask: true })
    let phoneRequired = false
    let loginError: string | null = null
    try {
      await loginWithWechat(phoneCode)
    } catch (e) {
      if (e instanceof ApiError && e.statusCode === 428 && !phoneCode) {
        phoneRequired = true
      } else {
        loginError = loginErrorMessage(e)
      }
    } finally {
      wx.hideLoading()
      this.setData({ loading: false })
    }
    if (phoneRequired) {
      this.setData({ phoneSheetOpen: true })
      return
    }
    if (loginError) {
      showLoginError(loginError)
      return
    }

    const app = getApp<IAppOption>()
    app.globalData.pendingOnboarding = !session.hasOnboarded()
    this.setData({ phoneSheetOpen: false })
    wx.switchTab({
      url: '/pages/home/home',
      fail: (error) => showLoginError(loginErrorMessage(error)),
    })
  },
})
