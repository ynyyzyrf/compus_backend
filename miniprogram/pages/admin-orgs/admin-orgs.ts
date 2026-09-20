import {
  createOrganization,
  deleteOrganization,
  listOrganizations,
  OrgNodePayload,
  updateOrganization,
} from '../../services/admin'
import type { OrgNodeAdminOut } from '../../types/api'

const TYPE_LABEL: Record<string, string> = {
  school: '學校',
  college: '分院',
  department: '系',
  class: '班',
}

interface Decorated extends OrgNodeAdminOut {
  typeLabel: string
  path: string
}

function decorate(nodes: OrgNodeAdminOut[]): Decorated[] {
  const byId = new Map(nodes.map((n) => [n.id, n]))
  return nodes.map((n) => {
    const path: string[] = []
    let cur = byId.get(n.parent_id ?? -1)
    while (cur) {
      path.unshift(cur.name)
      cur = cur.parent_id != null ? byId.get(cur.parent_id) : undefined
    }
    return { ...n, typeLabel: TYPE_LABEL[n.type] || n.type, path: path.join(' · ') }
  })
}

Page({
  data: {
    items: [] as Decorated[],
    loading: true,
    sheet: false,
    sheetMode: 'create' as 'create' | 'edit',
    form: {
      id: 0,
      name: '',
      type: 'department' as OrgNodePayload['type'],
      parent_id: null as number | null,
    },
    parents: [] as Decorated[], // schools + colleges + departments
  },

  onShow() { this.fetch() },

  async fetch() {
    this.setData({ loading: true })
    try {
      const list = await listOrganizations()
      const items = decorate(list)
      const parents = items.filter((n) => n.type !== 'class')
      this.setData({ items, parents })
    } finally {
      this.setData({ loading: false })
    }
  },

  onAddRoot() {
    this.setData({
      sheet: true,
      sheetMode: 'create',
      form: { id: 0, name: '', type: 'department', parent_id: null },
    })
  },

  onAddChild(e: WechatMiniprogram.BaseEvent) {
    const parentId = Number(e.currentTarget.dataset.id)
    const parent = this.data.items.find((n) => n.id === parentId)
    if (!parent) return
    const childType: OrgNodePayload['type'] =
      parent.type === 'school' ? 'college' :
      parent.type === 'college' ? 'department' :
      'class'
    this.setData({
      sheet: true,
      sheetMode: 'create',
      form: { id: 0, name: '', type: childType, parent_id: parentId },
    })
  },

  onRename(e: WechatMiniprogram.BaseEvent) {
    const id = Number(e.currentTarget.dataset.id)
    const node = this.data.items.find((n) => n.id === id)
    if (!node) return
    this.setData({
      sheet: true,
      sheetMode: 'edit',
      form: { id, name: node.name, type: node.type, parent_id: node.parent_id },
    })
  },

  onDelete(e: WechatMiniprogram.BaseEvent) {
    const id = Number(e.currentTarget.dataset.id)
    const node = this.data.items.find((n) => n.id === id)
    if (!node) return
    wx.showModal({
      title: '刪除 / 停用',
      content: node.member_count > 0 ? '有成員將轉為停用' : '確認刪除該節點',
      success: async ({ confirm }) => {
        if (!confirm) return
        try {
          await deleteOrganization(id)
          wx.showToast({ title: '已處理', icon: 'success' })
          this.fetch()
        } catch (err) {
          wx.showToast({ title: (err as Error).message || '失敗', icon: 'none' })
        }
      },
    })
  },

  closeSheet() { this.setData({ sheet: false }) },
  onNameChange(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ 'form.name': e.detail.value })
  },
  onTypeChange(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ 'form.type': e.detail.value })
  },
  onParentChange(e: WechatMiniprogram.CustomEvent<{ value: number[] }>) {
    const v = e.detail.value[0] ?? null
    this.setData({ 'form.parent_id': v })
  },

  async onSave() {
    const f = this.data.form
    if (!f.name.trim()) {
      wx.showToast({ title: '請填寫名稱', icon: 'none' })
      return
    }
    try {
      if (this.data.sheetMode === 'create') {
        await createOrganization({
          name: f.name.trim(),
          type: f.type,
          parent_id: f.parent_id,
        })
      } else {
        await updateOrganization(f.id, { name: f.name.trim() })
      }
      wx.showToast({ title: '已保存', icon: 'success' })
      this.setData({ sheet: false })
      this.fetch()
    } catch (err) {
      wx.showToast({ title: (err as Error).message || '失敗', icon: 'none' })
    }
  },
})
