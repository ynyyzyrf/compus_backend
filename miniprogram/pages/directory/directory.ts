import { ensureLogin, goLogin } from '../../services/auth'
import { getDirectoryTree, searchMembers } from '../../services/directory'
import type { MemberBrief, OrgNode } from '../../types/api'
import { locale, t } from '../../utils/i18n'

type MemberView = MemberBrief & { initial: string }

const SCOPE_LABEL: Record<string, string> = {
  class: 'directory.scope.class',
  department: 'directory.scope.department',
  college: 'directory.scope.college',
  all: 'directory.scope.all',
  none: 'directory.scope.none',
}

Page({
  data: {
    lang: locale.get(),
    keyword: '',
    members: [] as MemberView[],
    total: 0,
    scopeText: '',
    colleges: [] as OrgNode[],
    activeCollege: 'all',
    loading: false,
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar()?.setData({ value: 'directory' })
    }
    this.setData({ lang: locale.get() })
    this.init()
  },

  async init() {
    const user = await ensureLogin().catch(() => null)
    if (!user) {
      goLogin()
      return
    }
    await Promise.all([this.loadTree(), this.loadMembers()])
  },

  async loadTree() {
    try {
      const tree = await getDirectoryTree()
      const colleges = tree.nodes.filter((n) => n.type === 'college')
      this.setData({
        colleges,
        scopeText: SCOPE_LABEL[tree.scope_level] ? t(SCOPE_LABEL[tree.scope_level]) : '',
      })
    } catch (e) {
      console.error('load tree failed', e)
    }
  },

  async loadMembers() {
    const { keyword, activeCollege } = this.data
    // 分院篩選復用後端的「組織路徑」搜索；輸入關鍵詞時以關鍵詞為準。
    const q = keyword.trim() || (activeCollege !== 'all' ? activeCollege : '')
    this.setData({ loading: true })
    try {
      const page = await searchMembers(q, 1, 100)
      const members = page.items.map((m) => ({
        ...m,
        initial: m.name ? m.name.charAt(0) : '·',
      }))
      this.setData({ members, total: page.total })
    } finally {
      this.setData({ loading: false })
    }
  },

  onSearchInput(e: WechatMiniprogram.Input) {
    this.setData({ keyword: String(e.detail.value || ''), activeCollege: 'all' })
  },
  onSearchClear() {
    this.setData({ keyword: '' })
    this.loadMembers()
  },
  onSearchSubmit() {
    this.loadMembers()
  },
  onSelectCollege(e: WechatMiniprogram.BaseEvent) {
    const value = e.currentTarget.dataset.value as string
    this.setData({ activeCollege: value, keyword: '' })
    this.loadMembers()
  },

  onMemberTap(e: WechatMiniprogram.BaseEvent) {
    const id = Number(e.currentTarget.dataset.id)
    if (!Number.isFinite(id)) return
    wx.navigateTo({ url: `/pages/member-detail/member-detail?id=${id}` })
  },
})
