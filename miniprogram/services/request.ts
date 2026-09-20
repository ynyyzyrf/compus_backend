// 統一 API 請求層：業務 service 不直接接觸部署地址或 token 細節。
import { BASE_URL } from '../config/env'
import { session } from '../utils/session'

type Method = 'GET' | 'POST' | 'PUT' | 'DELETE'

export interface RequestOptions {
  url: string
  method?: Method
  data?: Record<string, unknown> | string
  /** 是否展示載入與錯誤提示，默認 true */
  silent?: boolean
  /** 內部使用：401 重試標記 */
  _retry?: boolean
}

// 由 services/auth 註冊，避免循環依賴。
let unauthorizedHandler: (() => Promise<void>) | null = null
export function setUnauthorizedHandler(handler: () => Promise<void>) {
  unauthorizedHandler = handler
}

export class ApiError extends Error {
  statusCode: number
  constructor(message: string, statusCode: number) {
    super(message)
    this.statusCode = statusCode
  }
}

export function request<T = unknown>(options: RequestOptions): Promise<T> {
  const { url, method = 'GET', data, silent = false, _retry = false } = options
  const token = session.getToken()

  if (!silent) wx.showLoading({ title: '加載中', mask: true })

  return new Promise<T>((resolve, reject) => {
    wx.request({
      url: BASE_URL + url,
      method,
      data,
      timeout: 10000,
      header: {
        'content-type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      success: async (res) => {
        const status = res.statusCode
        if (status >= 200 && status < 300) {
          resolve(res.data as T)
          return
        }

        // 401：清理登錄態，靜默重登後重試一次。
        if (status === 401 && !_retry && unauthorizedHandler) {
          try {
            await unauthorizedHandler()
            resolve(await request<T>({ ...options, _retry: true }))
            return
          } catch {
            // fall through to normal error handling
          }
        }

        const detail =
          (res.data as { detail?: string } | undefined)?.detail ||
          `請求失敗（${status}）`
        if (!silent) wx.showToast({ title: detail, icon: 'none' })
        reject(new ApiError(detail, status))
      },
      fail: (err) => {
        const msg = '網絡異常，請檢查後端是否啟動'
        if (!silent) wx.showToast({ title: msg, icon: 'none' })
        reject(new ApiError(err.errMsg || msg, 0))
      },
      complete: () => {
        if (!silent) wx.hideLoading()
      },
    })
  })
}
