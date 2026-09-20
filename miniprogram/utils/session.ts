// 本地登錄態緩存。
import type { UserProfile } from '../types/api'

const TOKEN_KEY = 'campus_token'
const USER_KEY = 'campus_user'
const ONBOARDED_KEY = 'campus_onboarded'
const GUEST_KEY = 'campus_guest'

export const session = {
  getToken(): string {
    return wx.getStorageSync(TOKEN_KEY) || ''
  },
  setToken(token: string) {
    wx.setStorageSync(TOKEN_KEY, token)
    wx.removeStorageSync(GUEST_KEY)
  },
  clearToken() {
    wx.removeStorageSync(TOKEN_KEY)
  },

  getUser(): UserProfile | null {
    return (wx.getStorageSync(USER_KEY) as UserProfile) || null
  },
  setUser(user: UserProfile) {
    wx.setStorageSync(USER_KEY, user)
    wx.removeStorageSync(GUEST_KEY)
  },
  clearUser() {
    wx.removeStorageSync(USER_KEY)
  },

  /** 首次進入是否已完成個人名片引導（profile-setup 頁保存或跳過後置 true） */
  hasOnboarded(): boolean {
    return !!wx.getStorageSync(ONBOARDED_KEY)
  },
  markOnboarded() {
    wx.setStorageSync(ONBOARDED_KEY, true)
  },
  resetOnboarded() {
    wx.removeStorageSync(ONBOARDED_KEY)
  },

  enterGuest() {
    this.clearToken()
    this.clearUser()
    wx.setStorageSync(GUEST_KEY, true)
  },
  isGuest(): boolean {
    return !!wx.getStorageSync(GUEST_KEY)
  },
  clearGuest() {
    wx.removeStorageSync(GUEST_KEY)
  },

  clear() {
    this.clearToken()
    this.clearUser()
    this.clearGuest()
  },
}
