interface TabBarComponentOptions {
  data: Record<string, unknown>
  setData: (data: Record<string, unknown>) => void
}

Component({
  data: {
    value: 'home',
    list: [
      { value: 'home', label: '首頁', icon: 'home' },
      { value: 'directory', label: '名錄', icon: 'usergroup' },
      { value: 'activities', label: '活動', icon: 'calendar' },
      { value: 'mine', label: '我的', icon: 'user' },
    ],
  },
  methods: {
    onChange(this: TabBarComponentOptions, e: WechatMiniprogram.CustomEvent<{ value: string }>) {
      const value = e.detail.value
      this.setData({ value })
      wx.switchTab({ url: `/pages/${value}/${value}` })
    },
  },
})
