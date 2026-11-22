import { ensureLogin, goLogin, logout } from '../../services/auth'
import { getAffiliationOptions, getMyAffiliation, reportMissingClass, submitAffiliation } from '../../services/affiliation'
import { session } from '../../utils/session'
import { academicClasses, matchesAcademicSelection, matchesClassKeyword, normalizeAcademicKeyword } from '../../utils/academic'
import type { AcademicClass, AcademicSelection } from '../../utils/academic'

Page({
  data: {
    classes: [] as AcademicClass[],
    shown: [] as AcademicClass[],
    selection: {} as AcademicSelection,
    keyword: '',
    searchCount: 0,
    chosen: null as AcademicClass | null,
    name: '',
    pendingPath: '',
    loading: true,
    submitting: false,
    error: '',
  },
  onShow() { this.load() },
  async load() {
    const user = await ensureLogin().catch(() => null)
    if (!user || session.isGuest()) { goLogin(); return }
    if (user.name !== '未命名校友') this.setData({ name: user.name })
    this.setData({ loading: true, error: '' })
    try {
      const affiliation = await getMyAffiliation()
      if (affiliation.class_id) { wx.switchTab({ url: '/pages/home/home' }); return }
      this.setData({ pendingPath: affiliation.pending_org_path || '' })
      if (!affiliation.pending_class_id) {
        this.setData({ classes: academicClasses(await getAffiliationOptions()) })
        this.filter()
      }
    } catch (error) {
      this.setData({ error: (error as Error).message || '组织资料载入失败' })
    } finally {
      this.setData({ loading: false })
    }
  },
  filter(limit = 30) {
    const terms = normalizeAcademicKeyword(this.data.keyword).split(/\s+/).filter(Boolean)
    const rows = this.data.classes.filter(row =>
      matchesAcademicSelection(row, this.data.selection) && matchesClassKeyword(row, terms))
    this.setData({ shown: rows.slice(0, limit), searchCount: rows.length })
  },
  search(e: WechatMiniprogram.Input) {
    this.setData({ keyword: e.detail.value })
    this.filter()
  },
  onFilter(e: WechatMiniprogram.CustomEvent<AcademicSelection>) {
    this.setData({ selection: e.detail })
    this.filter()
  },
  showMore() { this.filter(this.data.shown.length + 30) },
  choose(e: WechatMiniprogram.BaseEvent) {
    const row = this.data.classes.find(item => item.id === Number(e.currentTarget.dataset.id))
    if (row) {
      this.setData({ chosen: row }, () => wx.pageScrollTo({ selector: '#confirm-class' }))
    }
  },
  onNameInput(e: WechatMiniprogram.Input) { this.setData({ name: e.detail.value }) },
  async submit() {
    if (this.data.submitting || !this.data.chosen) return
    const name = this.data.name.trim()
    if (!name) { wx.showToast({ title: '请输入姓名', icon: 'none' }); return }
    this.setData({ submitting: true })
    try {
      const result = await submitAffiliation(this.data.chosen.id, name)
      const user = session.getUser()
      if (user) session.setUser({ ...user, name })
      this.setData({ pendingPath: result.pending_org_path })
      wx.showToast({ title: '已提交审核', icon: 'success' })
    } catch (error) {
      wx.showModal({ title: '提交失败', content: (error as Error).message || '请稍后重试', showCancel: false })
    } finally {
      this.setData({ submitting: false })
    }
  },
  report() {
    wx.showModal({
      title: '找不到我的班级',
      editable: true,
      placeholderText: '填写学校、入学年份、专业或班级',
      confirmText: '提交',
      success: async result => {
        if (!result.confirm) return
        const note = (result.content || '').trim()
        if (note.length < 2 || note.length > 200) {
          wx.showToast({ title: '请填写 2–200 字的班级线索', icon: 'none' })
          return
        }
        try {
          await reportMissingClass(note)
          wx.showToast({ title: '已提交给管理员', icon: 'success' })
        } catch (error) {
          wx.showModal({ title: '提交失败', content: (error as Error).message || '请稍后重试', showCancel: false })
        }
      },
    })
  },
  enterHome() { wx.switchTab({ url: '/pages/home/home' }) },
  signOut() { logout(); goLogin() },
})
