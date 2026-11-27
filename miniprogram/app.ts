import { routeUnassignedUser } from './services/startup'

App<IAppOption>({
  globalData: {
    pendingOnboarding: false,
  },
  onShow() {
    wx.nextTick(() => {
      const pages = getCurrentPages()
      const route = pages[pages.length - 1]?.route
      // These pages already load affiliation and route themselves.
      if (route && ['pages/login/login', 'pages/org-select/org-select'].includes(route)) return
      void routeUnassignedUser()
    })
  },
})
