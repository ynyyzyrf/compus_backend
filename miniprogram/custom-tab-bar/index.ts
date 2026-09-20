import { locale, t } from '../utils/i18n'

interface TabBarComponentOptions {
  data: Record<string, unknown>
  setData: (data: Record<string, unknown>) => void
}

function buildList() {
  return [
    { value: 'home', label: t('tab.home'), icon: 'home' },
    { value: 'directory', label: t('tab.directory_short'), icon: 'usergroup' },
    { value: 'activities', label: t('tab.activities'), icon: 'calendar' },
    { value: 'mine', label: t('tab.mine'), icon: 'user' },
  ]
}

Component({
  data: {
    value: 'home',
    lang: locale.get(),
    list: buildList(),
  },
  pageLifetimes: {
    show(this: TabBarComponentOptions) {
      this.setData({ lang: locale.get(), list: buildList() })
    },
  },
  methods: {
    refreshLocale(this: TabBarComponentOptions) {
      this.setData({ lang: locale.get(), list: buildList() })
    },
    onChange(this: TabBarComponentOptions, e: WechatMiniprogram.CustomEvent<{ value: string }>) {
      const value = e.detail.value
      this.setData({ value })
      wx.switchTab({ url: `/pages/${value}/${value}` })
    },
  },
})
