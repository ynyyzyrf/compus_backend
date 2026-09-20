import { locale } from './utils/i18n'

App<IAppOption>({
  globalData: {
    pendingOnboarding: false,
    locale: locale.get(),
  },
  onLaunch() {
    // 同步當前語言到 globalData（wxs 過濾器讀這裡）
    this.globalData.locale = locale.get()
  },
})
