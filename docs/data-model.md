# 資料模型 / Data Model

本文說明 LY Watchdog 採用的 **bi-temporal**（雙時間軸）資料模型，以及為什麼這個設計對新聞工作流重要。

---

## 為什麼是 bi-temporal？

一般資料庫只存「現在」——你 UPDATE 一筆資料，舊值就不見了。這對立法院資料不夠用，因為記者常常需要回答：

> 「2024-03-15 那天，我當時引用的資料說林某某是無黨籍——現在系統寫民進黨，到底是資料錯了還是後來改了？」

Bi-temporal 同時追蹤兩個時間軸：

| 時間軸 | 欄位 | 意義 |
|-------|------|------|
| **Business time**（業務時間） | `valid_from` / `valid_to` | 事實在**現實世界**有效的區間。例：林某某從 2024-02-01 到 2024-05-30 是民進黨籍 |
| **Transaction time**（記錄時間） | `recorded_at` / `superseded_at` | 系統**何時知道**這件事。例：系統在 2024-03-20 寫入這筆資料，2024-04-10 被新版本取代 |

兩個軸正交。讓我們可以回答以下**任一**問題：

1. 現在的事實是什麼？→ 最新業務時間 + 最新記錄時間
2. 過去某天的事實（根據最新資料）是什麼？→ 指定業務時間 + 最新記錄時間
3. **某天我們系統當時「以為」的事實是什麼？**→ 指定業務時間 + 指定記錄時間（報導追溯的關鍵場景）

---

## 單表 append-only 設計

每筆「立委」資料都存在 `legislators` 表中，**永不 UPDATE，只 INSERT**。

```
┌─────────────────────────────────────────────────────────────────────┐
│ legislators                                                         │
├─────────────────────────────────────────────────────────────────────┤
│ id              UUID  PK                                            │
│ legislator_uid  TEXT        ← 立法院的自然鍵                         │
│ name / district / party / term / raw_data (JSONB)                   │
│ valid_from      TIMESTAMPTZ NOT NULL  ← business time               │
│ valid_to        TIMESTAMPTZ           ← NULL = 事實仍有效            │
│ recorded_at     TIMESTAMPTZ NOT NULL  ← transaction time            │
│ superseded_at   TIMESTAMPTZ           ← NULL = 系統仍以此筆為準      │
└─────────────────────────────────────────────────────────────────────┘
```

### 寫入演算法（爬蟲 pipeline 要遵守）

```
For each legislator scraped today:
    current_row = SELECT * WHERE legislator_uid = X AND superseded_at IS NULL

    if current_row is None:
        # 新發現的立委
        INSERT new row (valid_from=today, recorded_at=now)

    elif current_row.values != scraped.values:
        # 資料有變動
        UPDATE current_row SET superseded_at = now(), valid_to = today
        INSERT new row (valid_from=today, recorded_at=now)

    else:
        # 無變動 — 什麼都不做
        pass
```

---

## 查詢範例

### 現在的立委清單

```sql
SELECT * FROM legislators
WHERE valid_to IS NULL
  AND superseded_at IS NULL;
```

### 時間旅行：2024-03-15 當下系統記錄的狀態

```sql
SELECT * FROM legislators
WHERE valid_from    <= '2024-03-15'
  AND (valid_to     IS NULL OR valid_to     > '2024-03-15')
  AND recorded_at   <= '2024-03-15'
  AND (superseded_at IS NULL OR superseded_at > '2024-03-15');
```

這個就是 API 的 `as_of=2024-03-15` 參數背後在做的事。

### 某立委的完整歷史變動記錄

```sql
SELECT name, party, valid_from, valid_to, recorded_at, superseded_at
FROM legislators
WHERE legislator_uid = 'XXXX'
ORDER BY recorded_at;
```

---

## 為什麼不用 Event Sourcing？

Event sourcing 只存變化事件、查詢靠 replay——儲存省、但查詢複雜、排序 replay 邊界難處理。對這個專案：

- 資料量不大（約數百位立委 × 變動次數）——儲存成本不是問題
- 記者查詢是 read-heavy、ad-hoc、希望 SQL 能直接打——single-table bi-temporal 勝出
- event sourcing 的複雜度會提高社群貢獻者的進入門檻

---

## 為什麼 `raw_data` JSONB 欄位必須存在？

立法院開放資料平台偶爾會調整欄位結構、甚至撤回某些資訊。保留原始 payload 讓我們可以：

- 事後驗證爬蟲解析邏輯是否正確
- 若上游刪除欄位，歷史資料還原得回來
- Debug 跨會期資料不一致的問題

**這是可稽核性（auditability）的地基，不可省略。**

---

## 參考

- Snodgrass, R. T. (1999). *Developing Time-Oriented Database Applications in SQL*
- Johnston, T. (2014). *Bitemporal Data: Theory and Practice*
