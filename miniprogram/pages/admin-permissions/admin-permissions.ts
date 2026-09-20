import {
  listDirectoryPermissions,
  saveDirectoryPermissions,
} from '../../services/admin'
import type { DirectoryPermissionOut } from '../../types/api'
import { locale, t } from '../../utils/i18n'

interface Decorated extends DirectoryPermissionOut {
  scopeLabel: string
}

Page({
  data: {
    lang: locale.get(),
    items: [] as Decorated[],
    loading: false,
    saving: false,
  },

  onShow() {
    this.setData({ lang: locale.get() })
    this.fetch()
  },

  async fetch() {
    this.setData({ loading: true })
    try {
      const list = await listDirectoryPermissions()
      const items = list.map((p) => ({
        ...p,
        scopeLabel:
          p.organization_type === 'college' ? t('directory.scope.college')
            : p.organization_type === 'department' ? t('directory.scope.department')
            : t('directory.scope.class'),
      }))
      this.setData({ items })
    } finally {
      this.setData({ loading: false })
    }
  },

  async onToggle(e: WechatMiniprogram.CustomEvent<{ value: boolean }>) {
    const index = e.currentTarget.dataset.index as number
    const next = e.detail.value
    const nextItems = this.data.items.map((it, i) =>
      i === index ? { ...it, is_enabled: next } : it,
    )
    this.setData({ items: nextItems })
    try {
      await saveDirectoryPermissions(
        nextItems.map((p) => ({
          organization_id: p.organization_id,
          scope_type: p.scope_type,
          is_enabled: p.is_enabled,
        })),
      )
      wx.showToast({ title: t('common.saved'), icon: 'success' })
    } catch (err) {
      wx.showToast({ title: (err as Error).message || t('common.fail'), icon: 'none' })
      this.fetch()
    }
  },

  async onSaveAll() {
    this.setData({ saving: true })
    try {
      await saveDirectoryPermissions(
        this.data.items.map((p) => ({
          organization_id: p.organization_id,
          scope_type: p.scope_type,
          is_enabled: p.is_enabled,
        })),
      )
      wx.showToast({ title: t('common.saved'), icon: 'success' })
    } finally {
      this.setData({ saving: false })
    }
  },
})
