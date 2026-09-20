# Campus Platform Backend

校友組織小程序後端 — FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL。
P0 階段僅本地開發，不涉及正式部署 / 域名 / HTTPS。

## 環境要求

- Python 3.11+（本機 3.13，使用 [uv](https://docs.astral.sh/uv/)）
- Docker（用 Compose 起 PostgreSQL 16）

## 一次性啟動

```bash
# 1. 起 Postgres（宿主端口 5433，避開本機已佔用的 5432）
docker compose up -d            # 在項目根目錄執行

# 2. 安裝依賴（以下均在 backend/ 目錄）
uv sync

# 3. 複製環境變量（庫中已帶一份可用的開發 .env）
cp .env.example .env            # Windows: copy .env.example .env

# 4. 數據庫遷移
uv run alembic upgrade head

# 5. 灌入開發種子數據（組織樹 + 7 名用戶 + 通訊錄權限）
uv run python -m app.seeds.seed_dev

# 6. 啟動 API（監聽 0.0.0.0:8000，方便真機預覽）
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- 接口文檔：<http://localhost:8000/docs>
- 健康檢查：<http://localhost:8000/health>

## 測試

```bash
uv run pytest
```

測試自動確保 `campus_test` 庫存在（docker 初始化腳本也會創建），每個用例在事務中
種入數據並回滾。重點覆蓋通訊錄「同班 / 系 / 分院」三檔可讀、高層級繼承與越權。

## 登錄說明（本地 mock）

本地沒有正式 AppSecret，`.env` 中 `WECHAT_MOCK_LOGIN=true`：

- `POST /api/v1/auth/wechat-login`：忽略 code 真實性，返回種子超管 **MAG** 的 token。
- `POST /api/v1/auth/dev-impersonate`：傳 `{ "user_id": 8..14 }` 切換身份，便於驗權限。
- `GET  /api/v1/auth/dev-users`：列出可切換的用戶（小程序「我的」頁開發面板使用）。
- 生產部署時設置 `WECHAT_MOCK_LOGIN=false` 並配置 `WECHAT_APPID/WECHAT_SECRET`，
  後端會走真實 `jscode2session`，上述 dev 接口自動關閉。

## 已驗證手機號登入

`users.phone` 是可編輯的聯絡電話，不可用於證明身份。遷移 `0003` 新增
`users.verified_phone` 唯一索引；只有微信 `getPhoneNumber` 授權碼經後端核驗後
才會寫入此欄位。`wx.login` 的 code 與手機號授權的 code 不可混用。

正式啟用前，確認新 AppID 已具備微信「獲取手機號」能力，並上傳包含新登入頁的
體驗版。可在登入頁點「使用手機號登入」測試授權及舊帳號合併。完成真機測試後，
才在 Zeabur 設定
`WECHAT_PHONE_LOGIN_REQUIRED=true`。預設 `false` 保持現有登入流程。
啟用後，尚未綁定手機號的用戶會收到 HTTP 428，前端才顯示微信手機號授權按鈕。

同一已驗證手機號只對應一個用戶。普通舊帳號若有唯一匹配的聯絡電話，登入時會
合併到該舊帳號；重複號碼、已停用帳號和超級管理員帳號須人工核對。

種子用戶 id：8=MAG(超管) 9=張晨 10=黃俊傑 11=陳思遠 12=林嘉怡 13=周可欣 14=王子謙。

權限示例：信工分院整院開放（張晨可見全院）；工商管理系本系開放（林嘉怡）；
其餘用戶僅同班可見（周可欣、王子謙）。

## 目錄

```
app/
├── core/        config / security(JWT) / deps(登錄態、超管校驗)
├── db/          Base、engine/session
├── models/      PRD §23 全部 13 張表
├── schemas/     Pydantic 契約
├── services/    組織樹、通訊錄可讀權限、登錄
├── api/v1/      auth / directory（後續切片增加 activities/articles/...）
└── seeds/       開發種子數據
migrations/      Alembic
tests/           權限與接口測試
```

> 權限一律由後端在 `services/directory_permission.py` 計算並裁剪，前端隱藏不作為安全邊界。
