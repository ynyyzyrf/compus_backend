# 小程序端（miniprogram）

微信原生 + TypeScript + TDesign Miniprogram。當前為 Walking Skeleton：
登錄態、統一請求層、4 個 tab、通訊錄頁已接真實後端；活動/接龍/公告/管理中心為佔位。

## 首次運行（微信開發者工具）

1. 先按 [backend/README.md](../backend/README.md) 啟動後端（默認 `:8000`）。
2. 開發者工具導入本項目根目錄（AppID 用測試號或 `wx42d74cdbd19566ff`）。
3. **npm 構建**：運行時依賴在 `miniprogram/package.json`，已安裝到
   `miniprogram/node_modules`，並按構建產物規則預生成了 `miniprogram/miniprogram_npm/`，
   **通常可直接編譯，無需手動構建**。若新增/升級依賴，在開發者工具菜單
   「工具 → 構建 npm」重新生成即可（注意 node_modules 必須位於 `miniprogram/` 內）。
4. 本地走 HTTP，已在 `project.private.config.json` 設置 `urlCheck:false`
   （即「不校驗合法域名」），僅開發期有效。

## 接口地址

見 `miniprogram/config/env.ts`：

- `ENV='development'` 時 Base URL 為 `http://<本機LAN IP>:8000/api/v1`，
  已預填 `192.168.31.177`；換網絡/電腦後改 `DEV_HOST`。
- 模擬器可用 `localhost:8000`；**真機預覽**必須用與手機同網段的 LAN IP，
  且 Windows 防火牆放行 8000 入站。
- 上線時把 `ENV` 改為 `production` 並配置 HTTPS 域名（小程序後台 request 合法域名）。

## 目錄

```
config/env.ts        環境 / Base URL
services/request.ts  統一封裝 wx.request（注入 JWT、401 重登重試、錯誤提示）
services/auth.ts     wx.login 換 token、dev 身份切換
services/directory.ts 通訊錄接口
utils/session.ts     token / 用戶緩存
custom-tab-bar/      TDesign 自定義底部導航
pages/               home / directory / activities / mine
types/api.ts         與後端 schemas 對齊的類型
```

## 驗證權限

「我的」頁底部有「開發：切換登錄身份」面板，可在超管與各普通用戶間切換；
切到「通訊錄」頁觀察可見組織/名錄範圍變化（後端裁剪）。
