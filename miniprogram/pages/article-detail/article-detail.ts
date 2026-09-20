import { getArticle } from '../../services/articles'
import type { ArticleDetail } from '../../types/api'
import { locale, t } from '../../utils/i18n'

function fmt(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

Page({
  data: {
    lang: locale.get(),
    article: null as ArticleDetail | null,
    loading: true,
    typeLabel: '',
    dateText: '',
  },

  onLoad(opts: Record<string, string | undefined>) {
    const id = Number(opts.id)
    if (!Number.isFinite(id)) {
      this.setData({ loading: false })
      return
    }
    this.load(id)
  },

  async load(id: number) {
    try {
      const article = await getArticle(id)
      const typeLabel =
        article.type === 'news'
          ? t('articles.type.news')
          : article.type === 'announcement'
            ? t('articles.type.announcement')
            : t('articles.type.notice')
      this.setData({
        lang: locale.get(),
        article,
        typeLabel,
        dateText: fmt(article.publish_at || article.created_at),
      })
      wx.setNavigationBarTitle({ title: typeLabel })
    } catch {
      this.setData({ article: null })
    } finally {
      this.setData({ loading: false })
    }
  },
})
