import { ensureLogin, goLogin } from '../../services/auth'
import { getAffiliationOptions, getMyAffiliation } from '../../services/affiliation'
import { getDirectoryTree, searchMembers } from '../../services/directory'
import type { MemberBrief } from '../../types/api'
import { academicClasses, normalizeAcademicKeyword } from '../../utils/academic'
import type { AcademicClass, AcademicSelection } from '../../utils/academic'
import { requestAlumniContact } from '../../utils/connection-actions'
import { session } from '../../utils/session'

const PAGE_SIZE = 20
type MemberView = MemberBrief & { initial: string }
const SCOPE: Record<string, string> = {
  class: '同班可见', department: '同系可见', college: '同院可见', all: '全部组织', none: '入组后开放通讯录',
}

Page({
  data: {
    keyword: '',
    appliedKeyword: '',
    members: [] as MemberView[],
    scopedClasses: [] as AcademicClass[],
    schoolClasses: [] as AcademicClass[],
    filters: {} as AcademicSelection,
    scopeText: '',
    discover: false,
    eligible: false,
    userId: 0,
    total: 0,
    page: 0,
    requestId: 0,
    loading: false,
    error: '',
  },
  onShow() {
    this.getTabBar?.()?.setData({ value: 'directory' })
    this.init()
  },
  async init() {
    const user = await ensureLogin().catch(() => null)
    if (!user || session.isGuest()) { goLogin(); return }
    try {
      const [tree, affiliation, options] = await Promise.all([
        getDirectoryTree(), getMyAffiliation(), getAffiliationOptions(),
      ])
      const classes = academicClasses(options)
      const school = classes.find(row => row.id === affiliation.class_id)?.school.id
      const eligible = school !== undefined
      this.setData({
        userId: user.id, eligible,
        discover: eligible && this.data.discover,
        scopedClasses: academicClasses(tree.nodes),
        schoolClasses: eligible ? classes.filter(row => row.school.id === school) : [],
        scopeText: SCOPE[tree.scope_level] || '',
      })
      await this.loadMembers(1)
    } catch (error) {
      this.setData({ error: (error as Error).message || '通讯录载入失败' })
    }
  },
  async loadMembers(page: number) {
    const id = this.data.requestId + 1
    const { appliedKeyword, discover, filters } = this.data
    this.setData({ requestId: id, loading: true, error: '', ...(page === 1 ? { members: [], page: 0, total: 0 } : {}) })
    if (discover && !appliedKeyword && !Object.keys(filters).length) {
      this.setData({ loading: false })
      return
    }
    try {
      const result = await searchMembers(appliedKeyword, page, PAGE_SIZE, filters, discover)
      if (this.data.requestId !== id) return
      const members = result.items.map(item => ({ ...item, initial: item.name.charAt(0) || '·' }))
      this.setData({ members: page === 1 ? members : [...this.data.members, ...members], page, total: result.total })
    } catch (error) {
      if (this.data.requestId === id) this.setData({ error: (error as Error).message || '查询失败，请重试' })
    } finally {
      if (this.data.requestId === id) this.setData({ loading: false })
    }
  },
  changeMode(e: WechatMiniprogram.BaseEvent) {
    const discover = e.currentTarget.dataset.mode === 'discover'
    if (this.data.discover === discover || (discover && !this.data.eligible)) return
    this.setData({ discover, filters: {} })
    this.loadMembers(1)
  },
  onSearchInput(e: WechatMiniprogram.Input) { this.setData({ keyword: e.detail.value }) },
  onSearchClear() {
    this.setData({ keyword: '', appliedKeyword: '' })
    this.loadMembers(1)
  },
  onSearchSubmit() {
    this.setData({ appliedKeyword: normalizeAcademicKeyword(this.data.keyword) })
    this.loadMembers(1)
  },
  onFilter(e: WechatMiniprogram.CustomEvent<AcademicSelection>) {
    this.setData({ filters: e.detail, appliedKeyword: normalizeAcademicKeyword(this.data.keyword) })
    this.loadMembers(1)
  },
  onReachBottom() {
    if (!this.data.loading && this.data.page > 0 && this.data.members.length < this.data.total) {
      this.loadMembers(this.data.page + 1)
    }
  },
  onMemberTap(e: WechatMiniprogram.BaseEvent) {
    const member = this.data.members.find(row => row.id === Number(e.currentTarget.dataset.id))
    if (!member) return
    if (member.can_view_profile !== false) {
      wx.navigateTo({ url: `/pages/member-detail/member-detail?id=${member.id}` })
    } else {
      this.addMember(e)
    }
  },
  addMember(e: WechatMiniprogram.BaseEvent) {
    const member = this.data.members.find(row => row.id === Number(e.currentTarget.dataset.id))
    if (member && member.id !== this.data.userId && this.data.eligible) requestAlumniContact(member.id, member.name)
  },
  goFindClass() { wx.navigateTo({ url: '/pages/org-select/org-select' }) },
})
