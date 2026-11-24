import { ensureLogin, goLogin } from '../../services/auth'
import { getMyProfile, updateMyProfile } from '../../services/profile'
import { connectionSummary, updateDiscoverability } from '../../services/connections'
import { session } from '../../utils/session'
import type { MyProfile, ProfileAudience, ProfileVisibilityKey } from '../../types/api'

Page({
  data: {
    profile: null as MyProfile | null,
    loading: true,
    saving: false,
    error: '',
    eligible: false,
    discoverable: false,
  },

  onShow() { void this.load() },

  async load() {
    if (this.data.saving) return
    const user = await ensureLogin().catch(() => null)
    if (!user || session.isGuest()) { goLogin(); return }
    const token = session.getToken()
    this.setData({ loading: true, error: '' })
    try {
      const [profile, summary] = await Promise.all([getMyProfile(), connectionSummary()])
      if (session.getToken() !== token) return
      this.setData({ profile, eligible: summary.eligible, discoverable: summary.discoverable })
    } catch (error) {
      if (session.getToken() === token) this.setData({ error: (error as Error).message || '设置加载失败，请重试' })
    } finally {
      if (session.getToken() === token) this.setData({ loading: false })
    }
  },

  async onVisibility(e: WechatMiniprogram.CustomEvent<{ key: ProfileVisibilityKey; value: ProfileAudience }>) {
    const { key, value } = e.detail
    if (this.data.loading || this.data.saving || !this.data.profile || this.data.profile[key] === value) return
    if (!['basic_visibility', 'contact_visibility', 'details_visibility'].includes(key) ||
        !['private', 'friends', 'classmates'].includes(value)) return
    const token = session.getToken()
    this.setData({ saving: true })
    try {
      const profile = await updateMyProfile({ [key]: value })
      if (session.getToken() !== token) return
      session.setUser(profile)
      this.setData({ profile, ...(key === 'basic_visibility' && value === 'private' ? { discoverable: false } : {}) })
      wx.showToast({ title: '已保存', icon: 'success' })
    } catch (error) {
      if (session.getToken() === token) wx.showModal({ title: '保存失败', content: (error as Error).message || '请稍后重试', showCancel: false })
    } finally {
      if (session.getToken() === token) this.setData({ saving: false })
    }
  },

  setDiscoverability() {
    if (this.data.loading || this.data.saving || !this.data.profile) return
    const enabled = !this.data.discoverable
    if (enabled && !this.data.eligible) {
      wx.showToast({ title: '组织审核通过后才可开启', icon: 'none' })
      return
    }
    if (enabled && this.data.profile.basic_visibility === 'private') {
      wx.showModal({ title: '请先调整基础资料权限', content: '基础资料目前仅自己可见。允许好友或同班同学查看后，才可开启校友查找。', showCancel: false })
      return
    }
    const token = session.getToken()
    wx.showModal({
      title: enabled ? '允许本校校友找到我' : '关闭跨院系查找',
      content: enabled
        ? '本校已审核的校友可以搜索到你的姓名、头像和班级，并发送好友申请。'
        : '关闭后，通讯录范围外的校友无法继续通过搜索找到你。',
      confirmText: enabled ? '开启' : '关闭',
      success: async ({ confirm }) => {
        if (!confirm || this.data.saving || session.getToken() !== token) return
        this.setData({ saving: true })
        try {
          const result = await updateDiscoverability(enabled)
          if (session.getToken() !== token) return
          this.setData({ discoverable: result.discoverable })
          wx.showToast({ title: '已保存', icon: 'success' })
        } catch (error) {
          if (session.getToken() === token) wx.showModal({ title: '设置失败', content: (error as Error).message || '请稍后重试', showCancel: false })
        } finally {
          if (session.getToken() === token) this.setData({ saving: false })
        }
      },
    })
  },
})
