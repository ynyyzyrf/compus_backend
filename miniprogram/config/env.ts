// 環境配置：services 層只依賴 BASE_URL，不寫死部署地址。

export type AppEnv = 'development' | 'production'

/** 切換環境只需改這一行。 */
export const ENV: AppEnv = 'development'

/**
 * development：本機 FastAPI。
 *  - 開發者工具模擬器可用 localhost
 *  - 真機預覽必須用與手機同網段的本機 LAN IP，且電腦防火牆放行 8000 端口
 * production：日後改為正式 HTTPS 域名（在小程序後台配置 request 合法域名）。
 */
const DEV_HOST = '192.168.31.177:8000'

const BASE_URLS: Record<AppEnv, string> = {
  development: `http://${DEV_HOST}/api/v1`,
  production: 'https://api.example.com/api/v1',
}

export const BASE_URL = BASE_URLS[ENV]
export const IS_DEV = ENV === 'development'
