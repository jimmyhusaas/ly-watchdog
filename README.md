# 立委行為觀測站 LY Watchdog
> 給記者與公民媒體用的立法院長期數據後端基礎設施  
> A long-term legislative behavior data backend for journalists and civic media

---

## 這是什麼 / What is this

台灣立法院的公開資料分散、格式不一、缺乏跨會期的長期視角。  
現有工具（如 api.ly.g0v.tw）建立於 2013–2016 年，技術架構老舊且不再積極維護。

**LY Watchdog** 的目標是提供一個現代化、穩定、可查詢的後端 API，讓報導者、沃草等公民媒體能夠直接串接，用數據說立委的故事。

---

## 為誰而做 / Who is this for

- **記者與公民媒體**：快速查詢立委出缺席、投票紀錄、法案進度，支援報導素材生產
- **公民科技開發者**：提供結構化 API，方便串接其他前端或視覺化工具
- **研究人員與 NGO**：跨會期長期資料，支援量化分析

---

## 核心問題 / The Problem

| 現況痛點 | LY Watchdog 的應對 |
|---------|-------------------|
| 資料散落在立法院各子系統 | 統一爬取、正規化、集中儲存 |
| 只能查「當下」，無法看「趨勢」 | Bi-temporal 資料模型，支援「時間旅行查詢」 |
| api.ly 用 LiveScript 寫成，難以維護 | 使用 Python，爬蟲生態成熟、社群貢獻門檻低 |
| 沒有 CI/CD，部署靠人工 | GitHub Actions + Docker Compose，自動化部署 |

---

## 功能規劃 / Roadmap

### Phase 1 ✅
- [x] 立委基本資料 API（姓名、選區、黨籍、屆別）
- [x] 出缺席紀錄爬取與儲存
- [x] 出缺席排行榜查詢 API（依會期、黨籍篩選）
- [x] Docker Compose 一鍵啟動開發環境

### Phase 2 ✅
- [x] 投票紀錄爬取與儲存
- [x] 黨紀一致性分析（某立委在黨團表決中的異動率）
- [x] 跨會期趨勢查詢 API

### Phase 3 ✅
- [x] 法案進度追蹤
- [x] 提案數量與類型統計
- [x] 質詢關鍵字索引

---

## 技術架構 / Tech Stack

```
立法院開放資料 API (data.ly.gov.tw)
        ↓
  排程爬蟲 (Scrapy + APScheduler)
        ↓
  PostgreSQL（Bi-temporal 資料模型）
        ↓
  REST API (FastAPI + SQLAlchemy)
        ↓
  消費端：報導者 / 沃草 / 其他前端
```

- **後端**：Python 3.12 + FastAPI（自動產生 OpenAPI 文件，對 API 消費者友善）
- **爬蟲**：Scrapy + httpx + Playwright（需要 JS 渲染時 fallback）
- **資料庫**：PostgreSQL（bi-temporal：`valid_time` + `transaction_time` 雙時間軸）
- **ORM / 資料驗證**：SQLAlchemy 2.0 + Pydantic
- **排程**：APScheduler（未來可升級 Celery + Redis）
- **型別安全**：mypy + Pydantic（彌補動態型別風險）
- **容器化**：Docker Compose
- **CI/CD**：GitHub Actions
- **資料來源**：[立法院開放資料服務平台](https://data.ly.gov.tw/odw/)

### 為什麼選 Python 而不是 Java？

本專案為**個人開源專案**且希望貢獻 g0v 社群，選型考量如下：

- **爬蟲生態**：Scrapy / Playwright / BeautifulSoup 是 Python 的強項，Java 在此領域明顯落後
- **社群貢獻門檻**：g0v 社群以 Python / Node.js 為主流，降低貢獻者入場成本
- **資料分析擴展性**：Phase 3 的質詢關鍵字索引、黨紀一致性分析天然需要 pandas / spaCy 生態
- **部署資源**：個人專案維運成本考量，Python image 遠小於 JVM

---

## 資料模型 / Data Model

本專案採用 **bi-temporal**（雙時間軸）資料模型，這是與 api.ly 的關鍵差異。

每筆資料記錄兩個時間維度：

- **`valid_time`**（業務時間）：這筆資料在現實世界中的有效區間，例如某立委在某屆會期的黨籍
- **`transaction_time`**（記錄時間）：系統何時記錄/修改這筆資料，例如某次爬取寫入的時間

這讓系統能支援「**時間旅行查詢**」——例如：

> 「2024-03-15 當下，系統記錄某立委的黨籍是什麼？」

對記者與研究人員而言，這個能力能追溯「報導當時的依據」，是傳統覆蓋式資料庫無法提供的。API 將以 `as_of=YYYY-MM-DD` 查詢參數對外暴露此能力。

---

## 與 api.ly.g0v.tw 的關係

本專案受 [api.ly](https://github.com/g0v/api.ly) 啟發，致謝 g0v 社群的先行工作。**無意取代，期望能作為補強方案與 g0v 資料生態協作。**

差異在於：

- 語言從 LiveScript → Python（爬蟲生態、社群貢獻門檻、資料分析擴展性）
- 新增 bi-temporal 資料模型，支援歷史時點查詢
- 以記者工作流程為主要設計目標，而非通用 API

---

## 快速開始 / Quick Start

### 1. 啟動服務

```bash
git clone https://github.com/jimmyhusaas/ly-watchdog.git
cd ly-watchdog
docker compose up --build -d
docker compose run --rm migrate
```

### 2. 抓取資料

```bash
docker compose exec app bash
python -m scrapers.legislators
python -m scrapers.attendance
python -m scrapers.votes
python -m scrapers.bills
python -m scrapers.interpellations
```

### 3. 驗證 API

```bash
# 健康檢查
curl http://localhost:8000/health

# 立委基本資料（第 11 屆）
curl "http://localhost:8000/v1/legislators?term=11"

# 出缺席排行榜
curl "http://localhost:8000/v1/attendance/ranking?term=11&session_period=1"

# 投票紀錄
curl "http://localhost:8000/v1/votes?term=11&legislator_name=柯建銘"

# 黨紀偏離率排行榜
curl "http://localhost:8000/v1/votes/party-discipline?term=11&session_period=1"

# 法案列表（依審查進度篩選）
curl "http://localhost:8000/v1/bills?term=11&bill_status=完成立法"

# 提案類型統計
curl "http://localhost:8000/v1/bills/stats?term=11"

# 質詢關鍵字搜尋（中文需 URL encode）
curl -G "http://localhost:8000/v1/interpellations" \
  --data-urlencode "term=11" \
  --data-urlencode "keyword=預算"
```

API 文件（Swagger UI）：`http://localhost:8000/docs`

### 4. 時間旅行查詢（as_of）

所有端點支援 `as_of` 參數，查詢特定時點的資料快照：

```bash
# 查詢 2024-06-01 當時的立委資料（可追溯黨籍變動）
curl "http://localhost:8000/v1/legislators?term=11&as_of=2024-06-01T00:00:00Z"
```

---

## 資料來源聲明 / Data Source

資料來自[立法院開放資料服務平台](https://data.ly.gov.tw/odw/)，遵循其開放授權條款使用。

---

## 參與貢獻 / Contributing

專案目前處於早期開發階段。歡迎：
- 提 Issue 討論功能需求或資料缺口
- 送 PR 改善爬蟲邏輯或 API 設計
- 如果你是記者或媒體工作者，歡迎告訴我你最需要哪種查詢

聯絡：（待補）  
g0v Slack：#data 頻道

---

*本專案為個人開源專案，與任何政黨或政治立場無關。*
