import { createOrganization, deleteOrganization, listOrganizations, updateOrganization } from '../../services/admin'
import type { OrgNodeAdminOut, OrgType } from '../../types/api'

const LABELS: Record<OrgType, string> = {
  school: '学校', college: '学院', department: '系别', major: '专业', class: '班级',
}
const CHILD: Partial<Record<OrgType, OrgType>> = {
  school: 'college', college: 'department', department: 'major', major: 'class',
}
type Node = OrgNodeAdminOut & { typeLabel: string; depth: number }
type Form = { id: number; name: string; type: OrgType; parent_id: number | null; year: string }

function orderTree(nodes: OrgNodeAdminOut[]): Node[] {
  const result: Node[] = []
  const visited = new Set<number>()
  function visit(node: OrgNodeAdminOut, depth: number) {
    if (visited.has(node.id)) return
    visited.add(node.id)
    result.push({ ...node, typeLabel: LABELS[node.type], depth: Math.min(4, depth) })
    nodes.filter(child => child.parent_id === node.id).forEach(child => visit(child, depth + 1))
  }
  nodes.filter(node => node.parent_id === null).forEach(node => visit(node, 0))
  nodes.forEach(node => visit(node, 0))
  return result
}

Page({
  data: {
    items: [] as Node[],
    loading: true,
    saving: false,
    sheet: false,
    sheetMode: 'create' as 'create' | 'edit',
    form: { id: 0, name: '', type: 'school', parent_id: null, year: '' } as Form,
    parentName: '',
    typeLabel: '',
    parentChoices: [] as Node[],
  },
  onShow() { this.fetch() },
  async fetch() {
    this.setData({ loading: true })
    try { this.setData({ items: orderTree(await listOrganizations()) }) }
    catch (error) { wx.showToast({ title: (error as Error).message || '载入失败', icon: 'none' }) }
    finally { this.setData({ loading: false }) }
  },
  manageClassAdmins(e: WechatMiniprogram.BaseEvent) {
    const id = Number(e.currentTarget.dataset.id)
    if (this.data.items.some(item => item.id === id && item.type === 'class')) {
      wx.navigateTo({ url: `/pages/admin-class-admins/admin-class-admins?id=${id}` })
    }
  },
  onAddChild(e: WechatMiniprogram.BaseEvent) {
    const parent = this.data.items.find(node => node.id === Number(e.currentTarget.dataset.id))
    if (!parent) return
    const type = e.currentTarget.dataset.type === 'class' ? 'class' : CHILD[parent.type]
    if (type) this.openCreate(type, parent)
  },
  openCreate(type: OrgType, parent: Node | null) {
    this.setData({
      sheet: true, sheetMode: 'create', typeLabel: LABELS[type], parentName: parent?.name || '',
      form: { id: 0, name: '', type, parent_id: parent?.id ?? null, year: '' }, parentChoices: [],
    })
  },
  onEdit(e: WechatMiniprogram.BaseEvent) {
    const node = this.data.items.find(row => row.id === Number(e.currentTarget.dataset.id))
    if (!node) return
    const parent = this.data.items.find(row => row.id === node.parent_id)
    const departmentId = parent?.type === 'major' ? parent.parent_id : parent?.id
    const parentChoices = node.type === 'class'
      ? this.data.items.filter(row => row.status === 'active' &&
        (row.id === departmentId || (row.type === 'major' && row.parent_id === departmentId)))
      : []
    this.setData({
      sheet: true, sheetMode: 'edit', typeLabel: node.typeLabel, parentName: parent?.name || '', parentChoices,
      form: { id: node.id, name: node.name, type: node.type, parent_id: node.parent_id, year: String(node.entry_year ?? '') },
    })
  },
  onParent(e: WechatMiniprogram.PickerChange) {
    const parent = this.data.parentChoices[Number(e.detail.value)]
    if (parent) this.setData({ 'form.parent_id': parent.id, parentName: parent.name })
  },
  onNameChange(e: WechatMiniprogram.Input) { this.setData({ 'form.name': e.detail.value }) },
  onYearChange(e: WechatMiniprogram.Input) { this.setData({ 'form.year': e.detail.value }) },
  closeSheet() { if (!this.data.saving) this.setData({ sheet: false }) },
  stopTap() {},
  async onSave() {
    if (this.data.saving) return
    const f = this.data.form
    if (!f.name.trim()) { wx.showToast({ title: '请填写名称', icon: 'none' }); return }
    const year = Number(f.year)
    if (f.type === 'class' && (f.year || this.data.sheetMode === 'create') &&
        (!/^\d{4}$/.test(f.year) || year < 1900 || year > 2100)) {
      wx.showToast({ title: '请输入有效的四位入学年份', icon: 'none' })
      return
    }
    const data = { name: f.name.trim(), parent_id: f.parent_id, entry_year: f.type === 'class' && f.year ? year : null }
    this.setData({ saving: true })
    try {
      if (this.data.sheetMode === 'create') await createOrganization({ ...data, type: f.type })
      else await updateOrganization(f.id, data)
      this.setData({ sheet: false })
      wx.showToast({ title: '已保存', icon: 'success' })
      await this.fetch()
    } catch (error) {
      wx.showModal({ title: '保存失败', content: (error as Error).message || '请稍后重试', showCancel: false })
    } finally { this.setData({ saving: false }) }
  },
  onDelete(e: WechatMiniprogram.BaseEvent) {
    const node = this.data.items.find(row => row.id === Number(e.currentTarget.dataset.id))
    if (!node) return
    wx.showModal({
      title: '删除或停用',
      content: node.member_count > 0 ? '该班级仍有成员，操作将停用班级。' : `确定删除「${node.name}」吗？`,
      success: async ({ confirm }) => {
        if (!confirm) return
        try {
          await deleteOrganization(node.id)
          await this.fetch()
        } catch (error) {
          wx.showModal({ title: '处理失败', content: (error as Error).message || '请稍后重试', showCancel: false })
        }
      },
    })
  },
})
