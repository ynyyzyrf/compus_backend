import { locale } from './utils/i18n'

App<IAppOption>({
  globalData: {
    pendingOnboarding: false,
    locale: 'zh-CN',
  },
  onLaunch() {
    // 每次進入小程序默認使用簡體中文；本次會話內仍可在「我的」頁切換。
    locale.set('zh-CN')
    this.globalData.locale = 'zh-CN'
  },
})
