import { getMyAffiliation } from './affiliation'
import { session } from '../utils/session'

let pending: { token: string; task: Promise<boolean> } | null = null

/** Recheck affiliation on every foreground entry, including a cached login. */
export function routeUnassignedUser(): Promise<boolean> {
  const token = session.getToken()
  if (!token || !session.getUser() || session.isGuest()) return Promise.resolve(false)
  if (pending?.token === token) return pending.task
  const task = (async () => {
    try {
      const affiliation = await getMyAffiliation()
      if (session.getToken() !== token || affiliation.class_id || affiliation.pending_class_id) return false
      const pages = getCurrentPages()
      const route = pages[pages.length - 1]?.route
      if (!route || route === 'pages/login/login' || route === 'pages/org-select/org-select') return false
      wx.reLaunch({ url: '/pages/org-select/org-select' })
      return true
    } catch {
      // A failed request cannot establish that the user has no organization.
      return false
    }
  })()
  pending = { token, task }
  void task.finally(() => { if (pending?.task === task) pending = null })
  return task
}
