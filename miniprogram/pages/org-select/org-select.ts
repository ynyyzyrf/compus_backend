import { ensureLogin, goLogin, logout } from '../../services/auth'
import { getAffiliationOptions, getMyAffiliation, submitAffiliation } from '../../services/affiliation'
import type { AffiliationOption } from '../../types/api'
import { session } from '../../utils/session'

const levels = ['school', 'college', 'department', 'class'] as const
type Level = typeof levels[number]

Page({
  data: {
    options: [] as AffiliationOption[],
    schoolItems: [] as AffiliationOption[], collegeItems: [] as AffiliationOption[],
    departmentItems: [] as AffiliationOption[], classItems: [] as AffiliationOption[],
    schoolNames: [] as string[], collegeNames: [] as string[],
    departmentNames: [] as string[], classNames: [] as string[],
    schoolId: 0, collegeId: 0, departmentId: 0, classId: 0,
    schoolName: '', collegeName: '', departmentName: '', className: '',
    name: '',
    pendingPath: '', loading: true, submitting: false, error: '',
  },

  onShow() { this.load() },

  async load() {
    const user = await ensureLogin().catch(() => null)
    if (!user) { goLogin(); return }
    if (user.name !== '未命名校友') this.setData({ name: user.name })
    this.setData({ loading: true, error: '' })
    try {
      const affiliation = await getMyAffiliation()
      if (affiliation.class_id) { wx.switchTab({ url: '/pages/home/home' }); return }
      if (affiliation.pending_class_id) {
        this.setData({ pendingPath: affiliation.pending_org_path, loading: false })
        return
      }
      const options = await getAffiliationOptions()
      const schoolItems = options.filter(item => item.type === 'school' && item.parent_id === null)
      this.setData({ options, schoolItems, schoolNames: schoolItems.map(item => item.name), loading: false })
    } catch (error) {
      this.setData({ loading: false, error: (error as Error).message || '組織資料載入失敗' })
    }
  },

  select(level: Level, index: number) {
    const items = this.data[`${level}Items`] as AffiliationOption[]
    const selected = items[index]
    if (!selected) return
    const next: Record<string, unknown> = {
      [`${level}Id`]: selected.id, [`${level}Name`]: selected.name,
    }
    const start = levels.indexOf(level)
    for (const descendant of levels.slice(start + 1)) {
      next[`${descendant}Id`] = 0
      next[`${descendant}Name`] = ''
      const childItems = descendant === levels[start + 1]
        ? this.data.options.filter(item => item.type === descendant && item.parent_id === selected.id)
        : []
      next[`${descendant}Items`] = childItems
      next[`${descendant}Names`] = childItems.map(item => item.name)
    }
    this.setData(next)
  },
  onSchool(e: WechatMiniprogram.PickerChange) { this.select('school', Number(e.detail.value)) },
  onCollege(e: WechatMiniprogram.PickerChange) { this.select('college', Number(e.detail.value)) },
  onDepartment(e: WechatMiniprogram.PickerChange) { this.select('department', Number(e.detail.value)) },
  onClass(e: WechatMiniprogram.PickerChange) { this.select('class', Number(e.detail.value)) },
  onNameInput(e: WechatMiniprogram.Input) { this.setData({ name: e.detail.value }) },

  async submit() {
    if (this.data.submitting) return
    const name = this.data.name.trim()
    if (!name) { wx.showToast({ title: '請輸入姓名', icon: 'none' }); return }
    if (!this.data.classId) { wx.showToast({ title: '請選擇所屬班級', icon: 'none' }); return }
    this.setData({ submitting: true })
    try {
      const result = await submitAffiliation(this.data.classId, name)
      const user = session.getUser()
      if (user) session.setUser({ ...user, name })
      this.setData({ pendingPath: result.pending_org_path })
      wx.showToast({ title: '已提交審核', icon: 'success' })
    } catch (error) {
      wx.showModal({ title: '提交失敗', content: (error as Error).message || '請稍後重試', showCancel: false })
    } finally {
      this.setData({ submitting: false })
    }
  },
  enterHome() { wx.switchTab({ url: '/pages/home/home' }) },
  signOut() { logout(); goLogin() },
})
