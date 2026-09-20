import { IS_DEV } from '../config/env'
import type { DevUser, LoginResult, UserProfile } from '../types/api'
import { session } from '../utils/session'
import { request, setUnauthorizedHandler } from './request'

function wxLoginCode(): Promise<string> {
  return new Promise((resolve, reject) => {
    wx.login({ success: (res) => resolve(res.code), fail: reject })
  })
}

/** wx.login -> 後端換 token（dev 為 mock 通道，默認進入種子超管）。 */
export async function loginWithWechat(): Promise<UserProfile> {
  const code = await wxLoginCode()
  const result = await request<LoginResult>(
    {
      url: '/auth/wechat-login', method: 'POST',
      data: { code },
      silent: true,
    },
  )
  session.setToken(result.access_token)
  session.setUser(result.user)
  return result.user
}

/** 保證有可用登錄態；不做靜默登錄，首次進入需跳到登錄頁由用戶觸發。 */
export function ensureLogin(force = false): Promise<UserProfile> {
  const cached = session.getUser()
  if (!force && session.getToken() && cached) {
    return Promise.resolve(cached)
  }
  if (!force && session.isGuest()) {
    return Promise.resolve({
      id: 0,
      name: '訪客',
      avatar_url: null,
      role: 'user',
      status: 'active',
    })
  }
  return Promise.reject(new Error('login_required'))
}

export async function refreshProfile(): Promise<UserProfile> {
  const user = await request<UserProfile>({ url: '/auth/me' })
  session.setUser(user)
  return user
}

export function logout() {
  session.clear()
}

export function goLogin() {
  const pages = getCurrentPages()
  const current = pages[pages.length - 1]
  const route = current?.route || ''
  if (route === 'pages/login/login') return
  wx.reLaunch({ url: '/pages/login/login' })
}

// ---- 僅開發模式：身份切換面板 ----

export async function listDevUsers(): Promise<DevUser[]> {
  if (!IS_DEV) return []
  return request<DevUser[]>({ url: '/auth/dev-users', silent: true })
}

export async function devImpersonate(userId: number): Promise<UserProfile> {
  const result = await request<LoginResult>({
    url: '/auth/dev-impersonate',
    method: 'POST',
    data: { user_id: userId },
  })
  session.setToken(result.access_token)
  session.setUser(result.user)
  return result.user
}

// 401 時回到登錄頁，不再靜默重登。
setUnauthorizedHandler(() => {
  if (session.isGuest()) {
    return Promise.reject(new Error('guest_requires_login'))
  }
  logout()
  goLogin()
  return Promise.reject(new Error('login_required'))
})
