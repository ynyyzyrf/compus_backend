# 校友組織微信小程序 PRD V1.0

> 文檔用途：產品需求基線 / UI 原型依據 / Codex 或 Claude Code 開發輸入  
> 產品形態：微信小程序（用戶端 + 手機管理端）  
> 管理角色：普通用戶 + 超級管理員  
> 核心能力：組織通訊錄、活動、報名、簽到、相冊、新聞公告、接龍、AI 數據分析

---

## 1. 項目背景

需求方希望建設一個面向校友 / 校園組織的微信小程序，首期以「通訊錄 + 組織運營」為核心，後續持續承載活動、內容發布、互動和 AI 數據分析能力。

原始需求包括：

- 做一個小程序通訊錄
- 預留活動宣傳平台
- 支持活動報名
- 支持活動簽到
- 支持圖片上傳
- 支持生成圖片分享到朋友圈
- 後台也使用手機端
- AI 可接入業務數據進行分析
- 支持新聞、公告
- 支持接龍
- 組織需要區分分院、系、班
- 班級通訊錄可按組織層級開放可讀權限

---

## 2. 產品定位

本產品定位為：

> **以組織架構和通訊錄為底座，承載活動、內容、互動與 AI 分析的微信小程序。**

產品不是單純的電子通訊錄，而是一個輕量級校友 / 校園組織運營平台。

---

## 3. 產品目標

### 3.1 V1 目標

V1 需要完成以下閉環：

1. 建立完整組織架構
2. 管理組織成員
3. 實現通訊錄查詢與權限控制
4. 發布新聞與公告
5. 創建活動
6. 用戶完成活動報名
7. 用戶完成活動簽到
8. 支持活動相冊與圖片上傳
9. 支持接龍
10. 超級管理員可在手機端完成管理
11. AI 可基於系統數據進行分析與問答

### 3.2 非 V1 核心目標

以下能力可後續擴展，不作為 V1 必須完整實現的內容：

- 多級管理員
- 分院管理員 / 系管理員 / 班級管理員
- 複雜 RBAC 權限系統
- PC Web 管理後台
- 支付能力
- 複雜工作流審批
- 完整問卷平台
- 自動代發朋友圈

---

## 4. 用戶角色

V1 僅保留兩種角色。

### 4.1 普通用戶

普通用戶可以：

- 查看首頁
- 查看自己有權限訪問的組織通訊錄
- 搜索成員
- 查看新聞 / 公告
- 查看活動
- 報名活動
- 完成簽到
- 查看活動相冊
- 上傳活動圖片
- 生成活動分享海報
- 參與接龍
- 查看自己的活動 / 接龍 / 上傳記錄

### 4.2 超級管理員

超級管理員擁有全部管理權限。

可管理：

- 組織架構
- 人員
- 通訊錄可讀權限
- 新聞
- 公告
- 活動
- 報名
- 簽到
- 接龍
- 活動圖片
- AI 數據分析

V1 不設置其他管理角色。

---

# 5. 信息架構

## 5.1 小程序底部導航

建議底部 Tab：

1. 首頁
2. 通訊錄
3. 活動
4. 我的

示意：

```text
首頁 | 通訊錄 | 活動 | 我的
```

---

# 6. 組織架構

## 6.1 組織層級

組織架構固定支持：

```text
學校 / 總組織
└── 分院
    └── 系
        └── 班
            └── 成員
```

示例：

```text
XX 校友組織
├── 信息工程分院
│   ├── 計算機系
│   │   ├── 2016級1班
│   │   └── 2017級2班
│   └── 軟件工程系
│       └── 2018級3班
├── 商學分院
└── 藝術設計分院
```

---

## 6.2 組織樹

用戶端與管理端均採用樹狀結構展示。

支持：

- 展開 / 收起分院
- 展開 / 收起系
- 展開 / 收起班級
- 顯示成員數量
- 點擊班級查看成員
- 搜索姓名 / 分院 / 系 / 班級

---

# 7. 通訊錄

## 7.1 通訊錄展示

通訊錄以組織樹為主。

示意：

```text
信息工程分院            [院可讀]
├── 計算機系             [系可讀]
│   ├── 2016級1班         [同班可讀]
│   │   ├── 張晨
│   │   └── 黃俊傑
│   └── 2017級2班
└── 軟件工程系
```

---

## 7.2 成員基本字段

建議包含：

| 字段 | 說明 |
|---|---|
| 姓名 | 必填 |
| 頭像 | 可選 |
| 分院 | 必填 |
| 系 | 必填 |
| 班級 | 必填 |
| 入學年份 | 可由班級解析或單獨存儲 |
| 手機號 | 可選 |
| 微信號 | 可選 |
| 郵箱 | 可選 |
| 個人簡介 | 可選 |
| 是否公開聯絡方式 | 可配置 |
| 狀態 | 正常 / 停用 |

---

# 8. 通訊錄可讀權限

## 8.1 權限原則

通訊錄權限不採用複雜角色制。

核心邏輯：

> **按組織範圍控制「誰可以看到哪一層通訊錄」。**

V1 支持三種可讀範圍：

1. 同班可讀
2. 某系可讀
3. 某分院可讀

---

## 8.2 默認規則

默認：

```text
同班可讀 = 開啟
```

即：

> 同一班級成員之間可以查看本班通訊錄。

---

## 8.3 系級可讀

超級管理員可以針對某個系開啟：

```text
計算機系可讀 = 開啟
```

開啟後：

> 計算機系內所有班級成員可以查看本系其他班級的通訊錄。

---

## 8.4 分院級可讀

超級管理員可以針對某個分院開啟：

```text
信息工程分院可讀 = 開啟
```

開啟後：

> 該分院下面所有系、所有班級成員均可以查看本分院內的通訊錄。

---

## 8.5 權限繼承

高層級權限覆蓋低層級。

例如：

```text
信息工程分院 = 可讀
```

則自動表示：

```text
信息工程分院
├── 計算機系        可讀
├── 軟件工程系      可讀
└── 下屬所有班級    可讀
```

不需要逐班級重複配置。

---

## 8.6 用戶端展示原則

普通用戶：

- 僅看到自己有權限查看的組織節點
- 無權限的節點可選擇完全隱藏
- 不應依賴前端隱藏實現權限
- 後端 API 必須再次驗證用戶可讀範圍

---

# 9. 首頁

首頁承擔信息聚合與主要入口。

## 9.1 首頁模塊

建議包含：

### 頂部

- 組織名稱
- 歡迎語
- 通訊錄搜索入口

### 快捷入口

- 通訊錄
- 活動
- 接龍
- 公告

### 最新活動

展示：

- 活動封面
- 活動名稱
- 時間
- 地點
- 報名人數
- 活動狀態

### 最新公告

展示：

- 標題
- 摘要
- 是否置頂
- 發布時間

### 正在進行的接龍

展示：

- 接龍名稱
- 參與人數
- 截止時間
- 狀態

---

# 10. 活動中心

## 10.1 活動列表

活動按狀態展示：

- 全部
- 報名中
- 即將開始
- 已結束

活動卡片展示：

- 封面
- 名稱
- 日期
- 地點
- 報名人數
- 人數上限
- 狀態

---

## 10.2 活動詳情

字段：

| 字段 | 說明 |
|---|---|
| 活動名稱 | 必填 |
| 封面 | 必填 |
| 活動介紹 | 必填 |
| 開始時間 | 必填 |
| 結束時間 | 必填 |
| 活動地點 | 必填 |
| 主辦方 | 可選 |
| 報名開始時間 | 必填 |
| 報名截止時間 | 必填 |
| 人數上限 | 可選 |
| 活動狀態 | 草稿 / 報名中 / 即將開始 / 進行中 / 已結束 |

活動詳情頁功能：

- 查看活動信息
- 立即報名
- 掃碼簽到
- 查看活動相冊
- 生成分享海報

---

# 11. 活動報名

## 11.1 基礎流程

```text
用戶
↓
活動詳情
↓
立即報名
↓
填寫報名資料
↓
提交
↓
報名成功
```

## 11.2 V1 報名字段

默認：

- 姓名
- 手機號
- 所屬組織
- 備註

後續可擴展自定義報名字段。

## 11.3 報名規則

需要支持：

- 截止時間控制
- 人數上限控制
- 防止重複報名
- 管理員查看報名名單
- 取消報名可作配置項

---

# 12. 活動簽到

## 12.1 V1 方案

V1 採用：

> **活動 QR Code 掃碼簽到**

流程：

```text
超級管理員生成活動簽到碼
↓
活動現場展示 QR Code
↓
用戶微信掃碼
↓
系統驗證身份
↓
驗證是否符合簽到條件
↓
寫入簽到記錄
```

---

## 12.2 簽到數據

管理員可查看：

- 報名人數
- 已簽到人數
- 未簽到人數
- 簽到率
- 各分院簽到數
- 各系簽到數
- 各班級簽到數

---

# 13. 活動相冊

## 13.1 圖片來源

支持：

- 超級管理員上傳
- 普通用戶投稿

---

## 13.2 圖片審核

建議普通用戶投稿圖片進入：

```text
待審核
↓
超級管理員審核
↓
通過
↓
活動相冊公開展示
```

V1 可根據需求選擇是否開啟審核。

---

## 13.3 圖片存儲

圖片不直接存入數據庫。

推薦：

```text
微信小程序
↓
後端 / 臨時上傳憑證
↓
COS / OSS / S3
```

數據庫只保存：

- 圖片 URL
- 活動 ID
- 上傳人
- 審核狀態
- 上傳時間

---

# 14. 分享朋友圈

## 14.1 分享方式

不設計「系統自動代發朋友圈」。

V1 採用：

> **生成活動分享海報 → 保存圖片 → 用戶自行分享到朋友圈**

海報建議包含：

- 組織名稱
- 活動名稱
- 活動時間
- 活動地點
- 活動圖片
- 小程序碼

---

# 15. 新聞 / 公告

## 15.1 類型

支持：

- 新聞
- 公告
- 通知

---

## 15.2 字段

| 字段 | 說明 |
|---|---|
| 類型 | 新聞 / 公告 / 通知 |
| 標題 | 必填 |
| 封面 | 可選 |
| 摘要 | 可選 |
| 正文 | 必填 |
| 發布時間 | 必填 |
| 是否置頂 | 是 / 否 |
| 狀態 | 草稿 / 已發布 / 已下架 |

---

## 15.3 發布範圍

V1 可支持：

- 全部成員
- 指定分院
- 指定系
- 指定班級

這裡可復用組織樹。

---

# 16. 接龍

## 16.1 產品定位

接龍不做成固定格式。

定義為：

> **輕量級表單信息收集能力。**

---

## 16.2 接龍字段類型

V1 建議支持：

- 單行文字
- 多行文字
- 數字
- 單選
- 多選
- 日期
- 圖片

---

## 16.3 接龍流程

```text
超級管理員創建接龍
↓
設定標題 / 截止時間 / 字段
↓
發布
↓
普通用戶填寫
↓
提交
↓
管理員查看結果
```

---

## 16.4 示例

```text
國慶返校聚餐接龍

姓名：
是否參加：
同行人數：
飲食需求：
備註：
```

---

# 17. 我的

普通用戶「我的」頁建議包含：

- 個人資料
- 所屬組織
- 我的活動
- 我的接龍
- 我的上傳
- 資料與隱私

如果當前用戶是超級管理員：

增加：

```text
管理中心 >
```

---

# 18. 手機管理中心

## 18.1 產品原則

不做 PC Web 後台。

管理端直接內嵌在同一個微信小程序。

只有超級管理員可進入。

---

## 18.2 管理中心首頁

建議展示核心數據：

- 通訊錄人數
- 當前活動報名人數
- 最近活動簽到率
- 當前接龍數量

功能入口：

```text
AI 數據助手
活動管理
新聞公告
接龍管理
相冊管理
人員管理
組織架構
通訊錄權限
```

---

# 19. 超級管理員能力

## 19.1 人員管理

支持：

- 新增成員
- 編輯成員
- 停用成員
- 綁定組織
- 批量導入成員（建議後續支持 Excel）

---

## 19.2 組織管理

支持：

- 新增分院
- 新增系
- 新增班級
- 修改名稱
- 調整父級
- 停用節點
- 查看節點人數

---

## 19.3 通訊錄權限管理

使用組織樹配置。

例如：

```text
XX校友組織

▾ 信息工程分院                   [ON]
   ▾ 計算機系                    [ON]
      2016級1班                 [同班可讀]
      2017級2班                 [同班可讀]
   ▸ 軟件工程系

▸ 商學分院                       [OFF]

▸ 藝術設計分院                   [OFF]
```

---

# 20. AI 數據助手

## 20.1 AI 定位

AI 不單獨作為普通聊天機器人。

AI 應直接讀取系統內的結構化業務數據。

支持分析：

- 人員
- 組織
- 活動
- 報名
- 簽到
- 接龍
- 新聞 / 公告
- 活動圖片元數據

---

## 20.2 使用場景

超級管理員可以直接問：

```text
這次活動報名情況如何？
```

```text
哪個系最近活動最活躍？
```

```text
有哪些人報名但沒有簽到？
```

```text
最近三個月活動參與率如何？
```

```text
哪個分院參與率最低？
```

```text
幫我生成本月運營總結。
```

```text
根據這次活動的數據生成一篇新聞稿。
```

---

## 20.3 AI Tool 設計

不建議：

```text
LLM → 直接連接 Database
```

建議：

```text
LLM / Agent
↓
受控業務 Tool
↓
Backend Service
↓
Database
```

V1 建議 Tool：

```text
get_activity_stats
get_signup_stats
get_checkin_stats
get_org_stats
search_members
get_relay_stats
get_content_stats
generate_activity_summary
```

---

## 20.4 AI 安全要求

AI：

- 不直接修改業務數據
- 讀取數據應經後端權限控制
- 僅超級管理員可使用完整數據分析
- AI 回答涉及人員資料時應遵守通訊錄隱私規則
- 所有 Tool 調用可記錄日誌

---

# 21. 頁面清單

## 21.1 普通用戶端

```text
pages/
├── home
├── directory
├── activities
├── activity-detail
├── signup
├── checkin
├── album
├── poster
├── article-list
├── article-detail
├── relay-list
├── relay-detail
└── mine
```

---

## 21.2 超級管理員端

```text
pages/admin/
├── dashboard
├── members
├── organizations
├── directory-permissions
├── activities
├── activity-editor
├── signup-list
├── checkin-list
├── articles
├── article-editor
├── relays
├── relay-editor
├── albums
└── ai-assistant
```

---

# 22. 核心業務流程

## 22.1 通訊錄

```text
微信登入
↓
識別用戶
↓
讀取用戶所屬班級 / 系 / 分院
↓
讀取通訊錄可讀規則
↓
計算可訪問組織節點
↓
返回組織樹與成員
```

---

## 22.2 活動報名

```text
查看活動
↓
立即報名
↓
填資料
↓
校驗截止時間 / 名額 / 重複報名
↓
創建報名記錄
↓
報名成功
```

---

## 22.3 活動簽到

```text
掃描活動簽到碼
↓
解析活動
↓
驗證登錄
↓
驗證報名
↓
驗證是否重複簽到
↓
寫入簽到記錄
```

---

## 22.4 圖片投稿

```text
選擇活動
↓
上傳圖片
↓
文件存儲
↓
寫入圖片記錄
↓
待審核 / 直接發布
↓
活動相冊展示
```

---

# 23. 數據模型

## 23.1 users

```text
id
openid
unionid
name
avatar_url
phone
wechat_id
email
bio
role
status
created_at
updated_at
```

`role`：

```text
user
super_admin
```

---

## 23.2 organizations

所有組織節點使用一張表。

```text
id
name
type
parent_id
status
sort_order
created_at
updated_at
```

`type`：

```text
school
college
department
class
```

---

## 23.3 memberships

```text
id
user_id
organization_id
is_primary
created_at
```

---

## 23.4 directory_permissions

```text
id
organization_id
scope_type
is_enabled
created_at
updated_at
```

`scope_type`：

```text
class
department
college
```

---

## 23.5 activities

```text
id
title
cover_url
description
location
organizer
start_at
end_at
signup_start_at
signup_end_at
capacity
status
created_by
created_at
updated_at
```

---

## 23.6 activity_signups

```text
id
activity_id
user_id
phone
remark
status
created_at
```

---

## 23.7 activity_checkins

```text
id
activity_id
user_id
signup_id
checkin_at
checkin_method
created_at
```

---

## 23.8 photos

```text
id
activity_id
uploader_id
file_url
status
created_at
reviewed_at
```

---

## 23.9 articles

```text
id
type
title
cover_url
summary
content
is_pinned
status
publish_at
created_by
created_at
updated_at
```

---

## 23.10 article_scopes

```text
id
article_id
organization_id
```

---

## 23.11 relays

```text
id
title
description
deadline
status
created_by
created_at
updated_at
```

---

## 23.12 relay_fields

```text
id
relay_id
label
field_type
required
options_json
sort_order
```

---

## 23.13 relay_responses

```text
id
relay_id
user_id
response_json
created_at
updated_at
```

---

# 24. API 分層建議

API 建議統一：

```text
/api/v1/
```

---

## 24.1 Auth

```text
POST /auth/wechat-login
GET  /me
```

---

## 24.2 Directory

```text
GET /directory/tree
GET /directory/members
GET /directory/members/{id}
```

後端需根據當前用戶自動裁剪可讀範圍。

---

## 24.3 Activities

```text
GET  /activities
GET  /activities/{id}
POST /activities/{id}/signup
POST /activities/{id}/checkin
GET  /activities/{id}/photos
POST /activities/{id}/photos
```

---

## 24.4 Articles

```text
GET /articles
GET /articles/{id}
```

---

## 24.5 Relay

```text
GET  /relays
GET  /relays/{id}
POST /relays/{id}/responses
```

---

## 24.6 Admin

```text
GET    /admin/dashboard
GET    /admin/members
POST   /admin/members
PUT    /admin/members/{id}

GET    /admin/organizations
POST   /admin/organizations
PUT    /admin/organizations/{id}

GET    /admin/directory-permissions
PUT    /admin/directory-permissions

POST   /admin/activities
PUT    /admin/activities/{id}
GET    /admin/activities/{id}/signups
GET    /admin/activities/{id}/checkins

POST   /admin/articles
PUT    /admin/articles/{id}

POST   /admin/relays
PUT    /admin/relays/{id}

GET    /admin/photos/pending
POST   /admin/photos/{id}/approve
POST   /admin/photos/{id}/reject
```

---

## 24.7 AI

```text
POST /admin/ai/chat
```

AI 後端再調用受控 Tools。

---

# 25. 微信登入

建議流程：

```text
wx.login()
↓
獲得 code
↓
小程序請求 Backend
↓
Backend 調微信接口
↓
獲得 openid / unionid
↓
匹配 users
↓
返回系統 access_token
```

要求：

- AppSecret 不得存放在小程序前端
- AppSecret 僅存後端環境變量
- API 必須驗證 access_token

---

# 26. 非功能要求

## 26.1 安全

必須：

- 管理 API 後端校驗 `super_admin`
- 通訊錄 API 後端校驗可讀範圍
- 禁止只靠前端隱藏頁面實現權限
- AppSecret 不下發前端
- 文件上傳限制類型和大小
- 敏感操作記錄日誌

---

## 26.2 隱私

需要考慮：

- 手機號
- 微信身份
- 頭像
- 姓名
- 組織信息
- 圖片

聯絡方式建議支持：

```text
公開 / 不公開
```

正式上線前需要完成微信小程序隱私配置。

---

## 26.3 性能

建議：

- 首頁首次加載避免一次拉取全部數據
- 通訊錄按組織節點按需讀取
- 圖片使用 CDN / 對象存儲
- 列表全部分頁
- AI 數據統計優先使用聚合接口，不讓模型讀取大量原始記錄

---

# 27. 推薦技術棧

## 27.1 小程序

```text
微信原生小程序
TypeScript
TDesign Miniprogram
```

---

## 27.2 Backend

```text
Python
FastAPI
SQLAlchemy
Alembic
```

---

## 27.3 Database

推薦：

```text
PostgreSQL
```

MySQL 亦可。

---

## 27.4 Cache

```text
Redis
```

V1 可按實際需求決定是否立即使用。

---

## 27.5 文件存儲

優先：

```text
騰訊 COS
```

或：

```text
S3 / OSS
```

---

## 27.6 部署

可採用：

```text
Zeabur
+
Docker
+
HTTPS
```

---

# 28. 系統架構

```text
┌──────────────────────────────┐
│        微信小程序             │
│                              │
│ 普通用戶端 + 手機管理端       │
└───────────────┬──────────────┘
                │ HTTPS REST API
                ▼
┌──────────────────────────────┐
│         FastAPI Backend      │
│                              │
│ Auth                         │
│ Directory                    │
│ Organization                 │
│ Activity                     │
│ Article                      │
│ Relay                        │
│ Admin                        │
│ AI Tools                     │
└───────┬────────┬─────────────┘
        │        │
        ▼        ▼
 PostgreSQL    Redis
        │
        ├──────────────► COS / OSS
        │
        └──────────────► AI Model / Agent
```

---

# 29. V1 優先級

## P0

必須完成：

- 微信登入
- 用戶
- 超級管理員
- 組織樹
- 分院 / 系 / 班
- 通訊錄
- 同班 / 系 / 院可讀權限
- 新聞公告
- 活動
- 報名
- QR Code 簽到
- 手機管理中心

---

## P1

建議 V1 一併完成：

- 接龍
- 活動相冊
- 用戶圖片投稿
- 分享海報
- AI 數據助手

---

## P2

後續版本：

- Excel 批量導入
- 訂閱消息
- 更細粒度隱私配置
- 更多管理角色
- 更完整數據看板
- AI 自動生成週報 / 月報
- AI 新聞稿生成
- H5 / App 多端

---

# 30. 驗收標準

## 30.1 登錄

- 用戶可正常微信登錄
- 首次登錄可建立用戶資料
- 超級管理員可識別管理身份

---

## 30.2 通訊錄

- 正確展示組織樹
- 可按姓名搜索
- 可按組織瀏覽
- 同班可讀規則生效
- 系級可讀規則生效
- 分院級可讀規則生效
- 無權限用戶無法通過 API 獲得數據

---

## 30.3 活動

- 管理員可發布活動
- 普通用戶可報名
- 不允許重複報名
- 名額控制有效
- 報名截止有效
- QR Code 簽到可用
- 不允許重複簽到

---

## 30.4 新聞公告

- 管理員可發布
- 普通用戶可查看
- 置頂有效
- 發布範圍有效

---

## 30.5 接龍

- 管理員可創建
- 普通用戶可提交
- 可查看已提交結果
- 截止時間有效

---

## 30.6 相冊

- 可上傳圖片
- 圖片正常保存至對象存儲
- 相冊可瀏覽
- 若開啟審核，未通過圖片不可公開

---

## 30.7 AI

AI 至少可以回答：

- 當前活動報名人數
- 當前活動簽到率
- 各分院 / 系活動參與情況
- 已報名未簽到名單
- 活動 / 組織基礎統計

---

# 31. 正式上線準備

需要需求方提供 / 申請：

- 微信小程序正式帳號
- 公司主體
- 正式 AppID
- 小程序名稱
- Logo
- 管理員微信
- 營業執照
- 主體認證
- 小程序備案
- 服務類目
- 隱私保護指引
- 正式 API 域名
- HTTPS
- 如涉及特殊服務，補充相關資質

---

# 32. 待需求方確認

以下內容在正式開發前建議再次確認：

1. 組織最高層是「學校」「校友會」還是其他名稱？
2. 一個人是否只屬於一個班級？
3. 是否存在跨班、跨系、跨院身份？
4. 通訊錄默認是否確定為「同班可讀」？
5. 手機號是否對有通訊錄權限的人直接可見？
6. 是否需要隱藏部分個人聯絡方式？
7. 活動是否允許取消報名？
8. 簽到是否必須先報名？
9. 普通用戶上傳活動照片是否需要審核？
10. 接龍是否需要限制可參與的組織範圍？
11. 新聞 / 公告是否需要定時發布？
12. AI 首期使用哪個模型 / 供應商？
13. 是否需要批量 Excel 導入歷史通訊錄？
14. 是否需要微信訂閱消息提醒活動或公告？

---

# 33. 開發原則

1. 先完成 P0 閉環，再做 P1。
2. 每個模塊完成後必須保證微信開發者工具正常編譯。
3. 小程序與 Backend 分層開發。
4. 不在前端寫死超級管理員 OpenID。
5. 所有管理權限由 Backend 驗證。
6. 通訊錄可讀權限由 Backend 計算。
7. AI 不直接連 Database。
8. 圖片不存 Database，只保存 URL。
9. 組織架構使用樹結構，不將分院 / 系 / 班寫死成多套邏輯。
10. 預留後續擴展更多管理角色，但 V1 不增加複雜度。

---

# 34. 建議項目目錄

```text
campus_platform/
├── PRD.md
├── miniprogram/
│   ├── app.ts
│   ├── app.json
│   ├── app.wxss
│   ├── pages/
│   ├── components/
│   ├── services/
│   ├── utils/
│   └── types/
│
└── backend/
    ├── app/
    │   ├── api/
    │   ├── models/
    │   ├── schemas/
    │   ├── services/
    │   ├── core/
    │   └── main.py
    ├── migrations/
    ├── tests/
    ├── Dockerfile
    └── requirements.txt
```

---

# 35. V1 產品一句話

> **一個以「分院 → 系 → 班」組織樹和權限化通訊錄為底座，集活動、報名、簽到、相冊、新聞公告、接龍與 AI 數據分析於一體的微信小程序。**
