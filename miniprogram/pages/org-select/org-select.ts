import { ensureLogin, goLogin } from '../../services/auth'
import { getAffiliationOptions, getMyAffiliation, reportMissingClass, submitAffiliation } from '../../services/affiliation'
import { session } from '../../utils/session'
import { academicClasses, matchesAcademicSelection, matchesClassKeyword, normalizeAcademicKeyword } from '../../utils/academic'
import type { AcademicClass, AcademicSelection } from '../../utils/academic'

Page({
  data: {
    step: 'select' as 'select' | 'confirm' | 'pending',
    canSubmit: false,
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
    if (user.name !== '未命名校友') this.setData({ name: user.name, canSubmit: Boolean(user.name.trim()) })
    this.setData({ loading: true, error: '' })
    try {
      const affiliation = await getMyAffiliation()
      if (affiliation.class_id) { wx.switchTab({ url: '/pages/home/home' }); return }
      this.setData({ pendingPath: affiliation.pending_org_path || '' })
      this.setStep(affiliation.pending_class_id ? 'pending' : this.data.step === 'confirm' ? 'confirm' : 'select')
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
    const chosen = this.data.chosen && rows.some(row => row.id === this.data.chosen?.id) ? this.data.chosen : null
    this.setData({ shown: rows.slice(0, limit), searchCount: rows.length, chosen })
  },
  search(e: WechatMiniprogram.Input) {
    this.setData({ keyword: e.detail.value })
    this.filter()
  },
  clearSearch() { this.setData({ keyword: '' }); this.filter() },
  onFilter(e: WechatMiniprogram.CustomEvent<AcademicSelection>) {
    this.setData({ selection: e.detail })
    this.filter()
  },
  showMore() { this.filter(this.data.shown.length + 30) },
  choose(e: WechatMiniprogram.BaseEvent) {
    if (this.data.submitting) return
    const row = this.data.shown.find(item => item.id === Number(e.currentTarget.dataset.id))
    if (row) this.setData({ chosen: row })
  },
  setStep(step: 'select' | 'confirm' | 'pending') {
    this.setData({ step })
    wx.setNavigationBarTitle({ title: { select: '选择班级', confirm: '确认身份', pending: '申请进度' }[step] })
  },
  nextStep() {
    if (this.data.loading || this.data.submitting || !this.data.chosen) return
    this.setStep('confirm')
    wx.pageScrollTo({ scrollTop: 0, duration: 0 })
  },
  reselect() {
    if (this.data.submitting) return
    this.setStep('select')
    wx.pageScrollTo({ scrollTop: 0, duration: 0 })
  },
  onNameInput(e: WechatMiniprogram.Input) { this.setData({ name: e.detail.value, canSubmit: Boolean(e.detail.value.trim()) }) },
  async submit() {
    if (this.data.submitting || this.data.step !== 'confirm' || !this.data.chosen) return
    const name = this.data.name.trim()
    if (!name) { wx.showToast({ title: '请输入姓名', icon: 'none' }); return }
    this.setData({ submitting: true })
    try {
      const result = await submitAffiliation(this.data.chosen.id, name)
      const user = session.getUser()
      if (user) session.setUser({ ...user, name })
      this.setData({ pendingPath: result.pending_org_path })
      this.setStep('pending')
      wx.pageScrollTo({ scrollTop: 0, duration: 0 })
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
})
