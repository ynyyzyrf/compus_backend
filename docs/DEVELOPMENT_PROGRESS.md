# Campus Platform 開發進度

> 文件用途：項目當前狀態基線，方便不同會話/接手者快速對齊。
> 最後更新：2026-09-20（含 P1 相冊審核、分享海報、AI 數據助手、顯式登錄流程）

## 一、項目定位

- **產品**：校友 / 校園組織微信小程序（AppID `wxc2b7726dfb13895b`）
- **角色**：普通用戶 + 超級管理員（V1 僅兩種）
- **核心**：組織架構（分院 → 系 → 班）+ 通訊錄權限化 + 活動閉環 + 內容 + AI
- **需求基線**：[PRD V1.0](V1.0/campus_platform_PRD_V1.0.md)、[HTML 原型 V1.0](V1.0/wechat_campus_platform_demo.html)

## 二、已鎖定技術決策（不可推翻）

| 維度 | 結論 |
|---|---|
| 後端 | 獨立 `backend/`，FastAPI + SQLAlchemy2 (sync, psycopg3) + Alembic + PostgreSQL |
| 不用微信雲開發，不改 PRD §23 的 13 張表 |
| P0 只做本地 FastAPI + Docker Postgres + Mock 登錄跑業務閉環；正式服務器/域名/HTTPS/Zeabur 部署後續階段 |
| 小程序 UI | TDesign Miniprogram + 自定義藍色校友商會視覺風格，強視覺頁少量自定義 |
| `services/` 統一封裝 API，dev/prod Base URL 在 [miniprogram/config/env.ts](../miniprogram/config/env.ts) |
| 渲染 | P0 全頁 WebView（`skylineRenderEnable: false`），與 TDesign 兼容性最穩 |
| 數據庫端口 | 容器映射**宿主 5433**（本機 5432 已被另一個 Postgres 佔用） |
| 構建 npm | 已預生成 [miniprogram/miniprogram_npm/](../miniprogram/miniprogram_npm/)，通常無需手動構建 |
| 啟動模式 | dev mock 登錄默認：建超管 MAG，AppSecret 不下前端，生產自動關閉 |
| 一個主職班級（PRD §32 採納默認值，可否決） |

## 三、後端（[backend/](../backend/)）— ✅ 完成 Walking Skeleton

### 3.1 數據層
- 13 張表模型已建好：[app/models/](../backend/app/models/) 全部按 PRD §23 字段命名
- 一次性 Alembic 遷移 [0001_initial_schema.py](../backend/migrations/versions/0001_initial_schema.py)
- 種子腳本 [seed_dev.py](../backend/app/seeds/seed_dev.py)：1 校 3 院 7 系 9 班 + 7 名用戶
  - 超管 MAG = user_id 8
  - 6 名普通用戶 = user_id 9–14
- 修復了同名的兩個 UniqueConstraint（改成 `signup_activity_user` / `checkin_activity_user`）

### 3.2 業務層（已實現）
| 模塊 | 文件 | 狀態 |
|---|---|---|
| 配置（pydantic-settings） | [app/core/config.py](../backend/app/core/config.py) | ✅ |
| JWT 簽發/解碼 | [app/core/security.py](../backend/app/core/security.py) | ✅ |
| 依賴（current_user / super_admin） | [app/core/deps.py](../backend/app/core/deps.py) | ✅ |
| 微信登錄（真實 + mock） | [app/services/auth_service.py](../backend/app/services/auth_service.py) | ✅ |
| 組織樹加載/遍歷 | [app/services/org_tree.py](../backend/app/services/org_tree.py) | ✅ |
| **通訊錄可讀權限核心** | [app/services/directory_permission.py](../backend/app/services/directory_permission.py) | ✅ |
| 通訊錄查詢（樹/分頁/詳情） | [app/services/directory_service.py](../backend/app/services/directory_service.py) | ✅ |
| API 路由 | [app/api/v1/auth.py](../backend/app/api/v1/auth.py) / [directory.py](../backend/app/api/v1/directory.py) / [router.py](../backend/app/api/v1/router.py) | ✅ |
| FastAPI 入口 | [app/main.py](../backend/app/main.py) | ✅ |

### 3.3 測試
- [tests/](../backend/tests/) 14 個用例全綠：
  - 三檔可讀權限（class / department / college）— [test_directory_permissions.py](../backend/tests/test_directory_permissions.py)
  - 成員列表/搜索/越權 — [test_directory_service.py](../backend/tests/test_directory_service.py)
  - API 層（401/404/scope 裁剪）— [test_directory_api.py](../backend/tests/test_directory_api.py)
- 測試自動創建 `campus_test` 庫（如不存在），每個用例在事務中種數據並回滾

### 3.4 驗證證據
- `alembic upgrade head` ✓ 建 13 表
- `pytest` ✓ 14 passed
- API 冒煙（curl，無 token→401；超管樹 `all`/20 節點；周可欣同班只見自己+4 導航節點、跨院看成員→404；張晨分院可見全院 4 人、按「軟件」搜索→陳思遠）
- 後端運行中：`http://localhost:8000` 與 `http://192.168.31.177:8000` 都 200

## 四、小程序（[miniprogram/](../miniprogram/)）— ✅ P0 代碼基本完成，待完整驗收

### 4.1 已完成
| 模塊 | 文件 | 狀態 |
|---|---|---|
| 環境配置（dev/prod Base URL） | [config/env.ts](../miniprogram/config/env.ts) | ✅ |
| 通用類型（API 對齊） | [types/api.ts](../miniprogram/types/api.ts) | ✅ |
| 本地登錄態緩存 | [utils/session.ts](../miniprogram/utils/session.ts) | ✅ |
| 統一請求封裝（JWT/401重試/錯誤提示） | [services/request.ts](../miniprogram/services/request.ts) | ✅ |
| 登錄服務（wx.login/ensureLogin/dev-impersonate） | [services/auth.ts](../miniprogram/services/auth.ts) | ✅ |
| 通訊錄服務 | [services/directory.ts](../miniprogram/services/directory.ts) | ✅ |
| TDesign 自定義 tabBar | [custom-tab-bar/](../miniprogram/custom-tab-bar/) | ✅ |
| 首頁（校友商會風格、快捷入口、活動/公告卡片） | [pages/home/](../miniprogram/pages/home/) | ✅ |
| 通訊錄頁（搜索、分院篩選、會員卡片、名片詳情跳轉） | [pages/directory/](../miniprogram/pages/directory/) | ✅ |
| 會員名片詳情頁 | [pages/member-detail/](../miniprogram/pages/member-detail/) | ✅ |
| 活動頁（狀態 tab、活動卡片、報名入口） | [pages/activities/](../miniprogram/pages/activities/) | ✅ |
| 我的頁（超管入口、dev 身份切換、語言切換） | [pages/mine/](../miniprogram/pages/mine/) | ✅ |
| 全局 app 入口 | [app.ts](../miniprogram/app.ts) / [app.json](../miniprogram/app.json) / [app.wxss](../miniprogram/app.wxss) | ✅ |
| TDesign 預構件 | [miniprogram_npm/](../miniprogram/miniprogram_npm/)（102 個組件） | ✅ |

### 4.2 移除/清理
- 刪除 quickstart 的 index/logs 頁與 getUserProfile 示範
- TDesign 組件從全局 usingComponents 改為按需單頁註冊（避免污染）

### 4.3 工程性配置
- `tsconfig.json` 加 `skipLibCheck: true`（規避第三方微信類型舊版約束衝突）
- `project.config.json` + `project.private.config.json` 關閉 Skyline、關閉 `urlCheck`（僅開發期 HTTP）

### 4.4 最近修復

- 參考設計圖將整體視覺調整為藍色校友商會風格，首頁、活動中心、通訊錄、我的頁完成首輪樣式更新。
- 修復首頁六個快捷入口圖標不顯示問題，移除首頁對不穩定 `t-icon` 渲染的依賴。
- 修復活動中心 tab 與首張活動卡片重疊問題。
- 修復 TDesign `search/search.json` 缺失導致的編譯報錯，通訊錄搜索改為原生 input。
- 修復 WXML `{{'key' | t}}` 管道語法導致多語言不生效的問題，改為顯式 `t.t(key, lang)`。
- 修復 WXS `try is not defined` 渲染層錯誤，移除不兼容寫法。
- 壓縮首屏大圖資源，將超 2MB 的 PNG 替換為 JPG，避免「source size exceed max limit 2MB」上傳失敗。
- 新增會員名片詳情頁，通訊錄點擊校友卡片可查看詳細資料。
- 活動中心已從靜態 demo 列表改為調用 `/activities` 真實接口；活動卡片點擊進入活動詳情，沿用報名/簽到閉環。
- 會員名片、活動中心、文章列表/詳情、通訊錄權限、管理中心首頁完成新一輪簡繁體文案接入。
- P1 接龍已完成首個可用閉環：超管創建/編輯/刪除接龍，普通用戶查看/提交，超管查看提交結果。
- 首次進入小程序已改為顯式登錄頁；移除 `App.onLaunch` 靜默登錄，用戶點擊「微信快捷登錄」後才調用 `wx.login` 換取 token。
- P1 活動相冊已完成：普通用戶投稿默認待審，超管上傳直接通過，公開相冊只展示已通過照片；我的上傳、管理端相冊審核頁已接通。
- P1 分享海報已完成首版：活動詳情可進入 canvas 海報頁，包含組織、活動、時間、地點、報名數、小程序碼占位，支持保存到相冊。
- P1 AI 數據助手已完成後端真 LLM 入口與受控工具邊界：`/admin/ai/chat` 僅超管可用，缺少 `OPENAI_API_KEY` / `OPENAI_MODEL` 時返回清晰配置錯誤；小程序管理中心已接通 AI 助手頁。

### 4.5 待驗收風險

- 微信開發者工具 CLI 的 IDE Service Port 未開啟，暫時無法用 CLI 做完整小程序構建/模擬器截圖驗證。
- 多語言核心頁已修復，但深層管理頁（如組織管理、人員管理、活動/文章編輯器）和部分 toast 仍需逐頁掃描硬編碼文案。
- 仍需在微信開發者工具/真機中驗證活動列表接口數據、圖片回退、tab 篩選與詳情跳轉。
- 仍需在微信開發者工具/真機中驗證首次登錄頁、登錄成功跳首頁、401 失效後回登錄頁、首次名片引導跳轉。

## 五、基礎設施 — ✅ 完成

| 項 | 位置 |
|---|---|
| Docker Compose（Postgres 16） | [docker-compose.yml](../docker-compose.yml) |
| 環境變量範例 | [backend/.env.example](../backend/.env.example) / [backend/.env](../backend/.env) |
| .gitignore | [.gitignore](../.gitignore) |
| git init | 已執行，未做任何提交 |
| 後端 README | [backend/README.md](../backend/README.md) |
| 小程序 README | [miniprogram/README.md](../miniprogram/README.md) |

## 六、P0 待辦（Walking Skeleton 之後的縱切）

| 切片 | 內容 | 對應 PRD | 預計工作量 | 狀態 |
|---|---|---|---|---|
| 切片 2 | 文章/公告（articles + scopes）— 列表/詳情/置頂/發布範圍/管理端編輯 | §15、§24.4 | 中 | ✅ 完成 |
| 切片 3 | 活動閉環（activities → signups → `wx.scanCode` 簽到 → 名單/簽到率） | §10–12、§22.3、§24.3 | 大 | ✅ 完成 |
| 切片 4 | 手機管理中心（人員/組織 CRUD、權限可視化開關、dashboard） | §18–19、§24.6 | 中 | ✅ 完成 |
| 多語言 | 簡體/繁體中文切換（i18n util + wxs 過濾器 + 我的頁切換器） | §5 PRD 默認 zh | 小 | ✅ 完成 |

### 切片 4 交付清單

**後端**（測試 7 個新增，全量 64 通過）：
- [schemas/admin.py](../backend/app/schemas/admin.py) DashboardStats / MemberAdminOut / OrgNodeAdminOut / DirectoryPermissionOut 等
- [services/admin_service.py](../backend/app/services/admin_service.py) members CRUD、organizations CRUD（含 cycle 防護）、permissions 批量 upsert、dashboard 統計（近三場簽到率）
- [api/v1/admin.py](../backend/app/api/v1/admin.py) `/admin/dashboard`、`/admin/members`、`/admin/organizations`、`/admin/directory-permissions`（含 403/400/404 全覆蓋）
- [tests/test_admin_api.py](../backend/tests/test_admin_api.py) 7 個用例

**小程序**（5 個新頁面）：
- [admin-dashboard](../miniprogram/pages/admin-dashboard/) — 4 個 stats + 8 個管理卡片
- [admin-members](../miniprogram/pages/admin-members/) + [admin-member-edit](../miniprogram/pages/admin-member-edit/) — 搜索 / 啟用停用 / 編輯（含 role/position/chamber_score）
- [admin-orgs](../miniprogram/pages/admin-orgs/) — 樹狀顯示，新建頂層/子節點、改名、刪除（有成員則軟刪除）
- [admin-permissions](../miniprogram/pages/admin-permissions/) — 每個分院/系一行 switch，實時保存

### 多語言交付

- [utils/i18n.ts](../miniprogram/utils/i18n.ts) — TS 端 `t(key, params)` 函數 + `locale.get/set`，持久化到 wx.storage
- [utils/i18n.wxs](../miniprogram/utils/i18n.wxs) — WXML 翻譯工具，與 TS 字典保持同步；頁面顯式傳入 `lang`
- 字典：~110 個鍵，覆蓋 home / directory / activities / articles / profile / mine
- **我的頁新增「語言」菜單項**，點擊在 `zh-CN ↔ zh-TW` 之間切換，頁面重新載入後讀取新語言

### 切片 2 交付清單

**後端**（測試 13 個新增，全量 27 通過）：
- [schemas/article.py](../backend/app/schemas/article.py) — 用戶端 / 管理端 Pydantic 契約
- [services/article_service.py](../backend/app/services/article_service.py) — 範圍裁剪邏輯（每篇文章獨立判定，無 scope=全可見，有 scope=需命中）
- [api/v1/articles.py](../backend/app/api/v1/articles.py) — `GET /articles`、`GET /articles/{id}`（用戶端）
- [api/v1/admin_articles.py](../backend/app/api/v1/admin_articles.py) — `POST/GET/PUT/DELETE /admin/articles`（超管 CRUD，scope_ids 一併替換）
- [tests/test_articles.py](../backend/tests/test_articles.py) — 服務層（11 個：可見性、scope 命中、置頂排序、CRUD）
- [tests/test_articles_api.py](../backend/tests/test_articles_api.py) — API 層（4 個：401/403/404/正常）

**小程序**：
- [services/articles.ts](../miniprogram/services/articles.ts) — 用戶端 + 管理端 API 封裝
- [pages/article-list/](../miniprogram/pages/article-list/) — 用戶端列表（類型 tab、置頂標識、跳詳情）
- [pages/article-detail/](../miniprogram/pages/article-detail/) — 用戶端詳情（類型/置頂/摘要/正文）
- [pages/admin-articles/](../miniprogram/pages/admin-articles/) — 管理列表（狀態 tab、新建/編輯/刪除）
- [pages/admin-article-editor/](../miniprogram/pages/admin-article-editor/) — 新建/編輯器（類型/狀態/標題/摘要/正文/置頂/範圍多選）
- 首頁「公告」快捷入口接通文章列表；「我的」超管入口接通管理列表

**端到端冒煙（curl）**：
- 超管創建兩篇文章（一篇全校可見、一篇僅計算機系）
- 周可欣（商學）→ 只見全校可見 ✓
- 張晨（信工/計算機）→ 兩篇都見 ✓
- 普通用戶 POST → 403 ✓
- 類型/type 過濾正確 ✓

### 切片 3 交付清單（活動閉環）

**後端**（測試 24 個新增，全量 57 通過）：
- [schemas/activity.py](../backend/app/schemas/activity.py) — ActivityListItem/Detail/Create/Update/Signup/Checkin/CheckinCode/SignupList
- [services/activity_service.py](../backend/app/services/activity_service.py) — 狀態自動計算 / 報名規則（窗口/容量/重複）/ 簽到窗口/取消過期 / 簽到碼簽發 / 名單統計
- [services/qr_token.py](../backend/app/services/qr_token.py) — 短時 JWT checkin token（含活動 ID 綁定）
- [api/v1/activity.py](../backend/app/api/v1/activity.py) — 用戶端：`GET /activities`、`GET /activities/{id}`、`POST /activities/{id}/signup`、`DELETE /activities/{id}/signup`、`POST /activities/{id}/checkin`
- [api/v1/admin_activity.py](../backend/app/api/v1/admin_activity.py) — 管理端 CRUD + `/checkin-code` + `/signups` 名單
- [tests/test_activities.py](../backend/tests/test_activities.py) 服務層（15 個：狀態計算、報名容量/重複、簽到窗口、QR 偽造、名單統計）
- [tests/test_activities_api.py](../backend/tests/test_activities_api.py) API 層（9 個：401/403/409、報名取消、簽到防重複、超管越權）

**小程序**：
- [services/activities.ts](../miniprogram/services/activities.ts)
- 用戶端：[pages/activities/](../miniprogram/pages/activities/)（狀態 tab）、[pages/activity-detail/](../miniprogram/pages/activity-detail/)（底部彈窗：報名 / 取消 / 掃碼簽到）
- 管理端：[admin-activities](../miniprogram/pages/admin-activities/)、[admin-activity-editor](../miniprogram/pages/admin-activity-editor/)、[admin-activity-roster](../miniprogram/pages/admin-activity-roster/)、[admin-activity-checkin](../miniprogram/pages/admin-activity-checkin/)
- 「我的」頁新增「📅 活動管理」入口（超管可見）

**端到端冒煙**：
- 超管建活動、issue 簽到碼；張晨報名 → 簽到 → 名單 50%；周可欣（未報名）→ 403 ✓
- 狀態自動計算（draft / signing / upcoming / ongoing / finished）
- 報名截止後取消 → 400 ✓
- 重複報名 → 409 ✓
- 過期 token → 400 ✓

## 七、P1 進度

| 模塊 | 對應 PRD | 狀態 |
|---|---|---|
| 接龍（7 字段類型 + 截止時間 + 結果展示） | §16 | ✅ 已完成首版閉環 |
| 活動相冊（投稿審核流程） | §13 | ✅ 已完成首版閉環 |
| 分享海報（canvas 生成保存） | §14 | ✅ 已完成首版 |
| COS 對象存儲驅動（替換本地 driver） | §13.3、§27.5 | 本輪採用本地模擬 driver，COS 待接入 |
| AI 助手（`/admin/ai/chat` + 8 個受控 Tools + 真 LLM 配置） | §20、§24.7 | ✅ 已完成首版閉環 |

### 接龍交付清單

**後端**（測試 3 個新增，全量 67 通過）：
- [schemas/relay.py](../backend/app/schemas/relay.py) — 接龍列表、詳情、字段、提交、管理端結果契約
- [services/relay_service.py](../backend/app/services/relay_service.py) — 字段校驗、截止/關閉判定、重複提交攔截、提交結果聚合
- [api/v1/relay.py](../backend/app/api/v1/relay.py) — 用戶端：`GET /relays`、`GET /relays/{id}`、`POST /relays/{id}/responses`
- [api/v1/admin_relays.py](../backend/app/api/v1/admin_relays.py) — 管理端：`POST/GET/PUT/DELETE /admin/relays`、`GET /admin/relays/{id}/responses`
- [tests/test_relays_api.py](../backend/tests/test_relays_api.py) — API 層（創建/提交/重複/必填/截止/權限/登錄）

**小程序**：
- [services/relays.ts](../miniprogram/services/relays.ts)
- 用戶端：[pages/relay-list](../miniprogram/pages/relay-list/)、[pages/relay-detail](../miniprogram/pages/relay-detail/)
- 管理端：[pages/admin-relays](../miniprogram/pages/admin-relays/)、[pages/admin-relay-editor](../miniprogram/pages/admin-relay-editor/)、[pages/admin-relay-responses](../miniprogram/pages/admin-relay-responses/)
- 首頁「接龍投票」、我的頁「我的接龍」、管理中心「接龍管理」已接通

### 相冊 / 海報 / AI 交付清單

**後端**（新增測試 8 個，全量 75 通過）：
- [schemas/photo.py](../backend/app/schemas/photo.py) — PhotoCreate / PhotoOut / PhotoPage
- [services/photo_storage.py](../backend/app/services/photo_storage.py) — 本地模擬 storage driver 抽象，只保存 URL/元數據
- [services/photo_service.py](../backend/app/services/photo_service.py) — 公開相冊、投稿、我的上傳、待審核、通過/拒絕
- [api/v1/photos.py](../backend/app/api/v1/photos.py) — `GET/POST /activities/{id}/photos`、`GET /me/photos`
- [api/v1/admin_photos.py](../backend/app/api/v1/admin_photos.py) — `GET /admin/photos/pending`、`POST /admin/photos/{id}/approve|reject`
- [services/ai_tools.py](../backend/app/services/ai_tools.py) — 8 個只讀工具：活動、報名、簽到、組織、成員搜索、接龍、內容、活動總結
- [services/ai_service.py](../backend/app/services/ai_service.py) — LLM 只接收受控 tool context，不直連 DB；API key 僅後端環境變量
- [api/v1/admin_ai.py](../backend/app/api/v1/admin_ai.py) — `POST /admin/ai/chat`，僅超管
- [tests/test_photos_api.py](../backend/tests/test_photos_api.py)、[tests/test_ai_api.py](../backend/tests/test_ai_api.py)

**小程序**：
- [services/photos.ts](../miniprogram/services/photos.ts)、[services/ai.ts](../miniprogram/services/ai.ts)
- 用戶端：[pages/activity-album](../miniprogram/pages/activity-album/)、[pages/my-uploads](../miniprogram/pages/my-uploads/)、[pages/activity-poster](../miniprogram/pages/activity-poster/)
- 管理端：[pages/admin-photos](../miniprogram/pages/admin-photos/)、[pages/admin-ai](../miniprogram/pages/admin-ai/)
- 活動詳情接入「活動相冊 / 分享海報」，我的頁接入「我的上傳」，管理中心接入「相冊審核 / AI 數據助手」。

**本輪驗證**：
- `backend/.venv/Scripts/python.exe -m pytest -q` → 75 passed
- `cd miniprogram && npx tsc --noEmit --pretty false` → passed
- `Get-ChildItem -Path miniprogram -Recurse -File | Where-Object { $_.Length -gt 2MB }` → 無輸出

## 八、PRD §32 採納的默認值

| 項 | 默認 |
|---|---|
| 一個人 V1 屬幾個班 | 1 個主職（模型保留多屬掛靠） |
| 手機號/微信號可見性 | 對有通訊錄可讀權限者可見；逐人開關屬 P2 |
| 報名取消 | 報名截止前可取消，截止後不可 |
| 簽到 | 必須先報名 |
| 照片審核 | 用戶投稿默認需審核，管理員上傳直接公開（P1 落地） |
| 新聞公告發布 | V1 手動發布，不做定時發布（`publish_at` 照存） |
| 項目性質 | 校友 + 商會混合；個人名片包含商會/BNI 字段 |
| 用戶名片字段 | 15 個新字段一次性建在 users 表（單表，chamber_ 前綴） |
| 首次錄入強制 | 不強制，可「稍後填寫」；完成或跳過後不再彈出 |

## 九、下一步明確動作

1. 按 [P0 驗收清單](P0_ACCEPTANCE_CHECKLIST.md) 在微信開發者工具/真機中逐項跑通，記錄截圖與剩餘 bug。
2. 手工驗收新增 P1：相冊投稿 → 待審 → 通過/拒絕 → 公開相冊；海報保存到相冊；AI 助手在缺 key 與有 key 兩種狀態下的提示/回答。
3. 後續接入正式對象存儲：以 `photo_storage.py` driver 為邊界替換為騰訊 COS，不改業務 API。
4. 補齊深層頁面的簡繁體文案，尤其是活動詳情、文章詳情、會員名片、管理端頁面與 toast。

## 十、本次提交摘要（個人名片擴展）

- 數據庫：users 表新增 15 列（name_en、company_*、profession/profession_en、position、business_description、referrals_needed、personal_experience、resources_offered、chamber_*）；Alembic 遷移 `0002_extend_user_profile_for_chamber_and_.py` 已應用
- 後端：
  - [schemas/profile.py](../backend/app/schemas/profile.py) MyProfile / MyProfileUpdate
  - [schemas/directory.py](../backend/app/schemas/directory.py) MemberDetail 擴充完整名片字段
  - [services/profile_service.py](../backend/app/services/profile_service.py) get_my_profile / update_my_profile
  - [api/v1/profile.py](../backend/app/api/v1/profile.py) GET/PUT `/me/profile`
  - [services/directory_service.py](../backend/app/services/directory_service.py) `get_member` 返回完整字段
- 測試：[tests/test_profile.py](../backend/tests/test_profile.py) 6 個新增，全量 33 通過
- 小程序：
  - [types/api.ts](../miniprogram/types/api.ts) MyProfile / MyProfileUpdate，MemberDetail 重寫
  - [services/profile.ts](../miniprogram/services/profile.ts)
  - [pages/profile-setup/](../miniprogram/pages/profile-setup/) 首次引導（含「稍後填寫」）
  - [pages/profile-edit/](../miniprogram/pages/profile-edit/) 我的 → 個人名片
  - [pages/mine/mine](../miniprogram/pages/mine/) 新增「個人名片」菜單 + 開發模式「重置首次引導」
  - [utils/session.ts](../miniprogram/utils/session.ts) 新增 onboarded 標記
  - [app.ts](../miniprogram/app.ts) 首次啟動設置 pendingOnboarding
  - [pages/home/home.ts](../miniprogram/pages/home/) onShow 自動跳轉到 setup
- 端到端：MAG 完整名片保存、張晨（同院）可見完整字段、周可欣/林嘉怡（跨院）→ 404
