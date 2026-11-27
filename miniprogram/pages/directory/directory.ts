import { ensureLogin, goLogin } from '../../services/auth'
import { getAffiliationOptions, getMyAffiliation } from '../../services/affiliation'
import { getDirectoryTree, searchMembers } from '../../services/directory'
import type { DirectoryRelation } from '../../services/directory'
import type { MemberBrief } from '../../types/api'
import { academicClasses, normalizeAcademicKeyword } from '../../utils/academic'
import type { AcademicClass, AcademicSelection } from '../../utils/academic'
import { requestAlumniContact } from '../../utils/connection-actions'
import { session } from '../../utils/session'

const PAGE_SIZE = 20
const RELATIONS: { id: DirectoryRelation; label: string }[] = [
  { id: 'class', label: '同班' }, { id: 'year', label: '同级' },
  { id: 'department', label: '同系' }, { id: 'college', label: '同院' },
]
const SCOPE: Record<string, string> = {
  class: '同班可见', department: '同系可见', college: '同院可见', all: '全部组织', none: '入组后开放通讯录',
}

Page({
  data: {
    keyword: '',
    appliedKeyword: '',
    relation: 'class' as DirectoryRelation | '',
    relations: RELATIONS,
    members: [] as MemberBrief[],
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
    const { globalData } = getApp<IAppOption>()
    const openDiscovery = globalData.openDirectoryDiscovery
    delete globalData.openDirectoryDiscovery
    const user = await ensureLogin().catch(() => null)
    if (!user || session.isGuest()) { goLogin(); return }
    try {
      const [tree, affiliation, options] = await Promise.all([
        getDirectoryTree(), getMyAffiliation(), getAffiliationOptions(),
      ])
      const classes = academicClasses(options)
      const school = classes.find(row => row.id === affiliation.class_id)?.school.id
      const eligible = school !== undefined
      const discover = eligible && (this.data.discover || !!openDiscovery)
      this.setData({
        userId: user.id, eligible,
        relation: eligible ? (user.id !== this.data.userId ? 'class' : this.data.relation || 'class') : '',
        discover,
        ...(discover !== this.data.discover ? { filters: {} } : {}),
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
    const { appliedKeyword, discover, filters, relation } = this.data
    this.setData({ requestId: id, loading: true, error: '', ...(page === 1 ? { members: [], page: 0, total: 0 } : {}) })
    if (discover && !appliedKeyword && !relation && !Object.keys(filters).length) {
      this.setData({ loading: false })
      return
    }
    try {
      const result = await searchMembers(appliedKeyword, page, PAGE_SIZE, filters, discover, 'all', relation || undefined)
      if (this.data.requestId !== id) return
      const members = result.items
      this.setData({ members: page === 1 ? members : [...this.data.members, ...members], page, total: result.total })
    } catch (error) {
      if (this.data.requestId === id) {
        this.setData({
          error: (error as Error).message || '查询失败，请重试',
        })
      }
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
  changeRelation(e: WechatMiniprogram.BaseEvent) {
    const id = RELATIONS.find(item => item.id === e.currentTarget.dataset.id)?.id
    if (!id) return
    if (!this.data.eligible) {
      wx.showToast({ title: '请先确认所属班级后使用筛选', icon: 'none' })
      return
    }
    if (this.data.relation === id) return
    this.setData({ relation: id, appliedKeyword: normalizeAcademicKeyword(this.data.keyword) })
    this.loadMembers(1)
  },
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
  onAvatarError(e: WechatMiniprogram.BaseEvent) {
    const { id, src } = e.currentTarget.dataset
    const index = this.data.members.findIndex(member => member.id === Number(id) && member.avatar_url === src)
    if (index >= 0) this.setData({ [`members[${index}].avatar_url`]: null })
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
})
