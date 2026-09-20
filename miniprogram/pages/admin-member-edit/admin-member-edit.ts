import { listMembers, updateMember } from '../../services/admin'
import type { MemberAdminOut } from '../../types/api'

Page({
  data: {
    memberId: 0,
    m: null as Partial<MemberAdminOut> | null,
    saving: false,
  },

  onLoad(opts: Record<string, string | undefined>) {
    const id = Number(opts.id)
    if (Number.isFinite(id) && id > 0) {
      this.setData({ memberId: id })
      this.load(id)
    }
  },

  async load(id: number) {
    const page = await listMembers({ page: 1, page_size: 100 })
    const m = page.items.find((x) => x.id === id)
    if (m) {
      this.setData({ m })
      wx.setNavigationBarTitle({ title: `編輯 ${m.name}` })
    }
  },

  onRole(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ 'm.role': e.detail.value })
  },
  onStatus(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ 'm.status': e.detail.value })
  },
  onPhone(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ 'm.phone': e.detail.value })
  },
  onPosition(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ 'm.position': e.detail.value })
  },
  onCompany(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ 'm.company_name': e.detail.value })
  },
  onBiz(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ 'm.business_description': e.detail.value })
  },
  onChamber(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ 'm.chamber_chapter': e.detail.value })
  },
  onChamberScore(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    const v = e.detail.value
    const num = v ? Number(v) : null
    this.setData({ 'm.chamber_score': num && !Number.isNaN(num) ? num : null })
  },

  async onSave() {
    if (!this.data.m) return
    const m = this.data.m
    this.setData({ saving: true })
    try {
      const payload = {
        role: m.role as 'user' | 'super_admin' | undefined,
        status: m.status as 'active' | 'disabled' | undefined,
        phone: m.phone,
        position: m.position,
        company_name: m.company_name,
        business_description: m.business_description,
        chamber_chapter: m.chamber_chapter,
        chamber_score: m.chamber_score,
      }
      await updateMember(this.data.memberId, payload)
      wx.showToast({ title: '已保存', icon: 'success' })
      setTimeout(() => wx.navigateBack(), 600)
    } catch (err) {
      wx.showToast({ title: (err as Error).message || '失敗', icon: 'none' })
    } finally {
      this.setData({ saving: false })
    }
  },
})
