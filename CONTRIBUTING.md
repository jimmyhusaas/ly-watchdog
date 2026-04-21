# 貢獻指南 / Contributing

感謝你對 LY Watchdog 有興趣！本專案目標是做為 g0v 社群的公民科技基礎設施，歡迎任何形式的貢獻——程式碼、Issue、資料缺口回報、或是告訴我們你的使用情境。

---

## 開發環境

### 需求

- Docker + Docker Compose
- （本地執行時）Python 3.12 + [uv](https://docs.astral.sh/uv/)

### 三步驟啟動

```bash
# 1. 複製環境變數範本
cp .env.example .env

# 2. 啟動 Postgres + 執行 migration + 啟動 API
docker compose up --build

# 3. 打開 http://localhost:8000/docs 看 API 文件
```

看到 `{"status":"ok"}` 回應 `GET /health` 就代表環境 OK。

### 本地跑測試（不進 Docker）

```bash
make install          # 建立 venv + 安裝依賴
make check            # lint + mypy + pytest
```

---

## Coding Style

- **Lint + Format**：`ruff`
- **Type check**：`mypy --strict`
- **Tests**：`pytest`，async 測試用 `pytest-asyncio`
- 提交前請跑 `make check` 確保 CI 會過

---

## PR 流程

1. Fork → 新 branch（建議 `feat/xxx`, `fix/xxx`, `docs/xxx` 命名）
2. 送 PR 到 `main`
3. CI 綠燈後會有人 review
4. 合併前請把 branch rebase 到最新的 `main`

小 PR 比大 PR 好——有疑問先開 Issue 討論比埋頭寫三千行後被退件好。

---

## 資料模型注意事項

本專案採用 **bi-temporal** 資料模型（`valid_from/valid_to` + `recorded_at/superseded_at`）。

**寫入資料時的鐵律：**

- 所有 table 採用 **append-only**——不要 UPDATE，發現變動就 INSERT 新 row 並把舊 row 的 `superseded_at` 設為當下時間
- 刪除不是真的 DELETE，而是設定 `valid_to`（代表現實世界中該事實結束）
- 爬蟲 pipeline 必須要有「我看到的 payload 和上一次有什麼不同」的 diff 邏輯

詳見 [`docs/data-model.md`](docs/data-model.md)。

---

## Good First Issues

歡迎從 GitHub 上標 `good first issue` 的 Issue 開始。如果沒有合適的，歡迎：

- 回報資料缺口（你需要查某個資訊但 API 沒有）
- 改善 API 文件 / 範例
- 補測試覆蓋率
- 中英文翻譯潤飾

---

## 聯絡

- GitHub Issues（偏好）
- g0v Slack `#data` 頻道
