import { ensureLogin, goLogin } from '../../services/auth'
import { addClassAdministrator, listClassAdministratorCandidates, listClassAdministrators, removeClassAdministrator } from '../../services/admin'
import type { ClassAdministrator, ClassAdministratorCandidate } from '../../services/admin'

Page({
  data: {
    classId: 0, className: '', administrators: [] as ClassAdministrator[],
    candidates: [] as ClassAdministratorCandidate[], keyword: '', total: 0, page: 0,
    loading: true, searching: false, busyId: 0, requestId: 0, error: '',
  },
  onLoad(options: Record<string, string | undefined>) {
    const classId = Number(options.id)
    if (Number.isSafeInteger(classId) && classId > 0) this.setData({ classId })
    else this.setData({ loading: false, error: '班级不存在' })
  },
  onShow() { if (this.data.classId) void this.load() },
  async load() {
    const user = await ensureLogin().catch(() => null)
    if (!user) { goLogin(); return }
    if (user.role !== 'super_admin') {
      this.setData({ loading: false, error: '仅超级管理员可分配班级管理员' })
      return
    }
    this.setData({ loading: true, error: '' })
    try {
      const result = await listClassAdministrators(this.data.classId)
      this.setData({ className: result.class_name, administrators: result.items })
      await this.search(1)
    } catch (error) {
      this.setData({ error: (error as Error).message || '管理员资料加载失败' })
    } finally { this.setData({ loading: false }) }
  },
  onKeyword(e: WechatMiniprogram.Input) { this.setData({ keyword: e.detail.value }) },
  onSearch() { void this.search(1) },
  async search(page: number) {
    const requestId = this.data.requestId + 1
    this.setData({ requestId, searching: true, error: '', ...(page === 1 ? { candidates: [], page: 0, total: 0 } : {}) })
    try {
      const result = await listClassAdministratorCandidates(this.data.classId, this.data.keyword.trim(), page)
      if (requestId !== this.data.requestId) return
      this.setData({ candidates: page === 1 ? result.items : [...this.data.candidates, ...result.items], total: result.total, page })
    } catch (error) {
      if (requestId === this.data.requestId) this.setData({ error: (error as Error).message || '用户搜索失败' })
    } finally { if (requestId === this.data.requestId) this.setData({ searching: false }) }
  },
  showMore() { if (!this.data.searching) void this.search(this.data.page + 1) },
  assign(e: WechatMiniprogram.BaseEvent) { this.confirm(Number(e.currentTarget.dataset.id), true) },
  remove(e: WechatMiniprogram.BaseEvent) { this.confirm(Number(e.currentTarget.dataset.id), false) },
  confirm(userId: number, add: boolean) {
    if (this.data.busyId) return
    const person = (add ? this.data.candidates : this.data.administrators).find(item => item.id === userId)
    if (!person) return
    wx.showModal({
      title: add ? '设置班级管理员' : '移除班级管理员',
      content: add ? `允许${person.name}审核「${this.data.className}」的加入申请？` : `移除${person.name}对「${this.data.className}」的审核权限？`,
      success: result => { if (result.confirm) void this.changeAdministrator(userId, add) },
    })
  },
  async changeAdministrator(userId: number, add: boolean) {
    if (this.data.busyId) return
    this.setData({ busyId: userId })
    try {
      const action = add ? addClassAdministrator : removeClassAdministrator
      const result = await action(this.data.classId, userId)
      this.setData({ administrators: result.items })
      wx.showToast({ title: add ? '已添加' : '已移除', icon: 'success' })
      await this.search(1)
    } catch (error) {
      wx.showModal({ title: '操作失败', content: (error as Error).message || '请稍后重试', showCancel: false })
    } finally { this.setData({ busyId: 0 }) }
  },
})
