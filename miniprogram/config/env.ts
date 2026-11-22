// 服务层统一从这里读取 API 地址。

export type AppEnv = 'development' | 'production'

function isLocalSimulator() {
  if (typeof wx === 'undefined' || wx.getAccountInfoSync?.().miniProgram.envVersion !== 'develop') {
    return false
  }

  const sdk = wx as typeof wx & { getDeviceInfo?: () => { platform: string } }
  const platform = sdk.getDeviceInfo?.().platform ?? sdk.getSystemInfoSync?.().platform
  return platform === 'devtools'
}

export const ENV: AppEnv = isLocalSimulator() ? 'development' : 'production'

const BASE_URLS: Record<AppEnv, string> = {
  development: 'http://127.0.0.1:18000/api/v1',
  production: 'https://compus.zeabur.app/api/v1',
}

export const BASE_URL = BASE_URLS[ENV]
export const IS_DEV = ENV === 'development'
