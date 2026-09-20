import { getDirectoryTree } from '../../services/directory'
import {
  adminCreateArticle,
  adminGetArticle,
  adminUpdateArticle,
} from '../../services/articles'
import { ensureLogin } from '../../services/auth'
import { session } from '../../utils/session'
import type { OrgNode } from '../../types/api'

Page({
  data: {
    isEdit: false,
    articleId: 0,
    type: 'announcement' as 'news' | 'announcement' | 'notice',
    status: 'draft' as 'draft' | 'published' | 'offline',
    title: '',
    summary: '',
    content: '',
    is_pinned: false,
    scope_ids: [] as number[],
    orgCandidates: [] as Array<{ id: number; name: string; path: string; checked: boolean }>,
    saving: false,
  },

  onLoad(opts: Record<string, string | undefined>) {
    const id = Number(opts.id)
    if (Number.isFinite(id) && id > 0) {
      this.setData({ isEdit: true, articleId: id })
      wx.setNavigationBarTitle({ title: '編輯文章' })
    } else {
      wx.setNavigationBarTitle({ title: '新建文章' })
    }
    this.init()
  },

  async init() {
    const user = await ensureLogin().catch(() => session.getUser())
    if (!user || user.role !== 'super_admin') {
      wx.showToast({ title: '僅超級管理員可訪問', icon: 'none' })
      setTimeout(() => wx.navigateBack(), 800)
      return
    }
    await this.loadOrgs()
    if (this.data.isEdit) await this.loadArticle()
  },

  async loadOrgs() {
    const tree = await getDirectoryTree()
    // Only college / department as scope candidates (class scope rarely useful)
    const candidates = tree.nodes
      .filter((n) => n.type !== 'school' && n.type !== 'class')
      .map((n) => ({ id: n.id, name: n.name, path: '', checked: false }))
    // build path label
    const byId = new Map(tree.nodes.map((n) => [n.id, n]))
    candidates.forEach((c) => {
      const path: string[] = []
      let cur: OrgNode | undefined = byId.get(c.id)
      while (cur) {
        path.unshift(cur.name)
        cur = cur.parent_id != null ? byId.get(cur.parent_id) : undefined
      }
      c.path = path.slice(1).join(' · ')
    })
    this.setData({ orgCandidates: candidates })
  },

  async loadArticle() {
    const article = await adminGetArticle(this.data.articleId)
    const checked = new Set(article.scope_ids)
    const candidates = this.data.orgCandidates.map((c) => ({
      ...c,
      checked: checked.has(c.id),
    }))
    this.setData({
      type: article.type,
      status: article.status,
      title: article.title,
      summary: article.summary || '',
      content: article.content,
      is_pinned: article.is_pinned,
      scope_ids: article.scope_ids,
      orgCandidates: candidates,
    })
  },

  onTypeChange(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ type: e.detail.value as 'news' | 'announcement' | 'notice' })
  },
  onStatusChange(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ status: e.detail.value as 'draft' | 'published' | 'offline' })
  },
  onTitle(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ title: e.detail.value })
  },
  onSummary(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ summary: e.detail.value })
  },
  onContent(e: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ content: e.detail.value })
  },
  onPinnedChange(e: WechatMiniprogram.CustomEvent<{ value: boolean }>) {
    this.setData({ is_pinned: e.detail.value })
  },
  onScopeChange(e: WechatMiniprogram.CustomEvent<{ value: number[] }>) {
    const values = e.detail.value
    const setIds = new Set(values)
    const candidates = this.data.orgCandidates.map((c) => ({
      ...c,
      checked: setIds.has(c.id),
    }))
    this.setData({ scope_ids: values, orgCandidates: candidates })
  },

  async onSave() {
    const { isEdit, articleId, title, content, summary, type, status, is_pinned, scope_ids } =
      this.data
    if (!title.trim()) {
      wx.showToast({ title: '請填寫標題', icon: 'none' })
      return
    }
    if (!content.trim()) {
      wx.showToast({ title: '請填寫正文', icon: 'none' })
      return
    }
    const payload = {
      type,
      title: title.trim(),
      summary: summary.trim() || null,
      content,
      is_pinned,
      status,
      scope_ids,
    }
    this.setData({ saving: true })
    try {
      if (isEdit) {
        await adminUpdateArticle(articleId, payload)
      } else {
        await adminCreateArticle(payload)
      }
      wx.showToast({ title: '已保存', icon: 'success' })
      setTimeout(() => wx.navigateBack(), 600)
    } catch (err) {
      wx.showToast({ title: (err as Error).message || '保存失敗', icon: 'none' })
    } finally {
      this.setData({ saving: false })
    }
  },
})
