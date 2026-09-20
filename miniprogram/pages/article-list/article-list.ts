import { listArticles } from '../../services/articles'
import type { ArticleListItem } from '../../types/api'
import { locale, t } from '../../utils/i18n'

const TAB_KEYS = ['', 'announcement', 'news', 'notice'] as const
type ArticleTabKey = (typeof TAB_KEYS)[number]
type ArticleView = ArticleListItem & { typeLabel: string }

function articleTypeLabel(type: ArticleListItem['type']): string {
  if (type === 'news') return t('articles.type.news')
  if (type === 'announcement') return t('articles.type.announcement')
  return t('articles.type.notice')
}

function buildTabs(): Array<{ key: ArticleTabKey; label: string }> {
  return [
    { key: '', label: t('articles.tab.all') },
    { key: 'announcement', label: t('articles.tab.announcement') },
    { key: 'news', label: t('articles.tab.news') },
    { key: 'notice', label: t('articles.tab.notice') },
  ]
}

Page({
  data: {
    lang: locale.get(),
    tabs: buildTabs(),
    current: 0,
    articles: [] as ArticleView[],
    loading: false,
  },

  onLoad() {
    this.fetch()
  },

  onPullDownRefresh() {
    this.fetch().finally(() => wx.stopPullDownRefresh())
  },

  onShow() {
    this.setData({ lang: locale.get(), tabs: buildTabs() })
  },

  async fetch() {
    const type = (TAB_KEYS[this.data.current] || undefined) as
      | 'news'
      | 'announcement'
      | 'notice'
      | undefined
    this.setData({ loading: true })
    try {
      const items = await listArticles({ type, page_size: 50 })
      this.setData({ articles: items.map((item) => ({ ...item, typeLabel: articleTypeLabel(item.type) })) })
    } finally {
      this.setData({ loading: false })
    }
  },

  onTabChange(e: WechatMiniprogram.CustomEvent<{ value: number }>) {
    this.setData({ current: e.detail.value })
    this.fetch()
  },

  onItemTap(e: WechatMiniprogram.BaseEvent) {
    const id = e.currentTarget.dataset.id as number
    wx.navigateTo({ url: `/pages/article-detail/article-detail?id=${id}` })
  },
})
