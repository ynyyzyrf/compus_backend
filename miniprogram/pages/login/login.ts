import { IS_DEV } from '../../config/env'
import { loginWithWechat } from '../../services/auth'
import { getMyAffiliation } from '../../services/affiliation'
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
  },

  async onShow() {
    this.setData({ lang: locale.get() })
    if (session.getToken() && session.getUser()) {
      await this.routeAfterLogin()
    }
  },

  async routeAfterLogin() {
    const user = session.getUser()
    if (!user) return
    if (user.role !== 'super_admin') {
      try {
        const affiliation = await getMyAffiliation()
        if (!affiliation.class_id && !affiliation.pending_class_id) {
          wx.redirectTo({ url: '/pages/org-select/org-select' })
          return
        }
      } catch (error) {
        showLoginError(loginErrorMessage(error))
        return
      }
    }
    wx.switchTab({ url: '/pages/home/home', fail: (error) => showLoginError(loginErrorMessage(error)) })
  },

  onLogin() {
    if (this.data.loading) return
    return this.confirmLogin()
  },

  skipLogin() {
    session.enterGuest()
    const app = getApp<IAppOption>()
    app.globalData.pendingOnboarding = false
    wx.switchTab({ url: '/pages/home/home' })
  },

  async confirmLogin() {
    if (this.data.loading) return
    this.setData({ loading: true })
    wx.showLoading({ title: t('login.loading'), mask: true })
    let loginError: string | null = null
    try {
      await loginWithWechat()
    } catch (e) {
      loginError = loginErrorMessage(e)
    } finally {
      wx.hideLoading()
      this.setData({ loading: false })
    }
    if (loginError) {
      showLoginError(loginError)
      return
    }

    const app = getApp<IAppOption>()
    app.globalData.pendingOnboarding = !session.hasOnboarded()
    await this.routeAfterLogin()
  },
})
