import { getDashboard } from '../../services/admin'
import { ensureLogin } from '../../services/auth'
import { session } from '../../utils/session'
import type { DashboardStats } from '../../types/api'
import { locale, t } from '../../utils/i18n'

Page({
  data: {
    lang: locale.get(),
    stats: null as DashboardStats | null,
    loading: true,
  },

  onShow() {
    this.fetch()
  },

  async fetch() {
    const user = await ensureLogin().catch(() => session.getUser())
    if (!user || user.role !== 'super_admin') {
      wx.showToast({ title: t('admin.only_super_admin'), icon: 'none' })
      setTimeout(() => wx.navigateBack(), 800)
      return
    }
    this.setData({ lang: locale.get(), loading: true })
    try {
      const stats = await getDashboard()
      this.setData({ stats })
    } finally {
      this.setData({ loading: false })
    }
  },

  goMembers() { wx.navigateTo({ url: '/pages/admin-members/admin-members' }) },
  goOrgs() { wx.navigateTo({ url: '/pages/admin-orgs/admin-orgs' }) },
  goPermissions() { wx.navigateTo({ url: '/pages/admin-permissions/admin-permissions' }) },
  goArticles() { wx.navigateTo({ url: '/pages/admin-articles/admin-articles' }) },
  goActivities() { wx.navigateTo({ url: '/pages/admin-activities/admin-activities' }) },
  goRelays() { wx.navigateTo({ url: '/pages/admin-relays/admin-relays' }) },
  goPhotos() { wx.navigateTo({ url: '/pages/admin-photos/admin-photos' }) },
  goAi() { wx.navigateTo({ url: '/pages/admin-ai/admin-ai' }) },
})
