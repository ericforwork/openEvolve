# Technical Report（簡短版）：兩階段 OpenEvolve × CrewAI 評論模擬進化

> 完整版：[`TECHNICAL_REPORT.md`](TECHNICAL_REPORT.md)  
> English (short): [`TECHNICAL_REPORT_SHORT_en.md`](TECHNICAL_REPORT_SHORT_en.md)  
> 資料來源：`config/openevolve_output/final_basicOnly`、`config/openevolve_output/final_agentTask`

---

## 1. 摘要

本報告分兩部分：**先呈現設計創新（Novelty）**，再呈現進化分析（Evolution Analysis）。我們以 OpenEvolve 對 CrewAI 的 **agents + tasks 聯合 YAML** 做 full-rewrite 進化，並採 **兩階段漸進策略（Staged Evolution）**——先在小管線上學會「怎麼寫 prompt」，再擴充管線衝刺高分。

### 結果一覽

| 階段 | Run | Crew 規模 | Gen-0 | Best | 提升 |
|------|-----|-----------|-------|------|------|
| Phase 1 — Basic | `final_basicOnly` | 3 agents × 3 tasks | 0.9100 | **0.9412** | +0.031 |
| Phase 2 — Extended | `final_agentTask` | 5 agents × 5 tasks | 0.9579 | **0.9999** | +0.042 |

評分目標：`combined_score = (星等預測準度 + 評論品質) / 2`；評論品質中 **topic 權重 50%**。

---

### A. Novelty — 我們用 OpenEvolve 優化了什麼、怎麼做（What & How）

**What（優化對象）**  
我們不進化 Python 程式碼，而是進化 **整條 Sequential Crew 的 prompt 契約**：每個 agent 的 `role / goal / backstory`，以及每個 task 的 `description / expected_output`。工具名稱與管線拓撲由 `simulation_crew.py` 固定；OpenEvolve 在結構鎖（structure guard）下，專注優化「如何查資料、如何傳遞中間欄位、如何輸出最終 JSON」。

**How（OpenEvolve 用法 — 創意點）**

1. **兩階段接力進化（Staged Handoff）**  
   - Phase 1：僅 3 agent（user → item → predict），搜尋空間小、收斂快。  
   - Phase 2：以 Phase 1 `best_program.yaml` 為 Gen-0，**人工擴充** `review_analyst`、`internet_researcher` 與對應 task，再跑第二輪進化。  
   - 這不是讓 LLM 自己發明新 agent，而是 **人設計拓撲、OpenEvolve 優化文案**——兼顧可控性與探索深度。

2. **聯合進化 bundle**  
   單一 `EVOLVE-BLOCK` 同時突變 agents 與 tasks，讓「agent 怎麼想」與「task 怎麼下指令」一起適應 evaluator 的 `combined_score`。

3. **與評分公式對齊的管線設計**  
   - 前段 task：查 user/item 特徵（服務星等 MAE）。  
   - 中段 task：`lookup_reviews_by_user_and_item` 做 direct match（服務星等 + topic）。  
   - 末段 task：無工具的 `prediction_modeler` 只吃結構化 context，輸出 `{"stars","review"}`。

**Crew 協作模式（Collaboration Pattern）**

```
Phase 1 (Sequential):
  analyze_user_task → analyze_item_task → simulate_review_task → JSON

Phase 2 (Sequential, 擴充):
  internet_research_task → analyze_user_task → analyze_item_task
    → analyze_reviews_task → simulate_review_task → JSON
```

| Agent | Role（摘要） | Tool Use（Task 層） |
|-------|-------------|---------------------|
| `user_analyst` | 使用者行為分析 | `search_user_profile_data`, `search_historical_reviews_data` |
| `item_analyst` | 商家特徵分析 | `search_restaurant_feature_data`, `search_historical_reviews_data` |
| `review_analyst` *(P2)* | 歷史評論比對 | `lookup_reviews_by_user_and_item` |
| `internet_researcher` *(P2)* | 一般評分趨勢 | `search_internet`（禁止捏造 user/item） |
| `prediction_modeler` | 星等 + 評論生成 | **無工具**（綜合前序報告） |

詳細 Role / Goal / Backstory / Task `expected_output` 見 §2。

---

### B. Evolution Analysis — 進化路徑與 OpenEvolve 發現的策略

**方法**  
- 解析 `checkpoints/checkpoint_*/programs/*.json` 與 `best_program_info.json` 的 `parent_id` 祖先鏈。  
- 以 **Visualizer**（`make visualize OUTPUT=...`）比對 **Gen-0 vs Best** 的 prompt diff 與演化樹。  
- 工具：`scripts/parse_evolution_run.py` → `docs/assets/evolution/evolution_summary.json`。

**Phase 1 進化路徑（`final_basicOnly`）**

| Checkpoint | Best score | 解讀 |
|------------|-----------|------|
| iter 5 | 0.9335 | 早期快速提升 |
| iter 15 | **0.9412** | 達到平台 |
| iter 20–50 | 0.9412 | 35 iter 無突破 → 觸發 Phase 2 |

祖先鏈：`gen0(0.91) → gen1(0.94) → gen2(0.92) → gen3(0.9412) Best`  
→ OpenEvolve 在 **gen=2 短暫退步後**，gen=3 子代整合突變，體現 MAP-Elites 保留多樣性的價值。

**OpenEvolve 在 Phase 1 發現的策略**：不改 tool 名稱，而是精煉 `prediction_modeler` 的 data-scientist 敘述、強化缺資料 default（3.8 星），以及最終 JSON 契約——**prompt 語意優化 > 工具替換**。

**Phase 2 進化路徑（`final_agentTask`）**

| Checkpoint | Best score | 解讀 |
|------------|-----------|------|
| Gen-0 | 0.9579 | 繼承 Phase 1 Best + 新 agent/task |
| iter 5–40 | 0.9666 | 平台期：review 鏈路尚未對齊 |
| iter 45 | **0.9999** | 關鍵突破 |
| iter 50 | 0.9999 | 收斂 |

祖先鏈：`gen0(0.96) → gen1~4(0.94~0.95 震盪) → gen5(0.9999) Best`  
→ 中期探索分數波動，最終 gen=5 **整合**前期有效突變。

**OpenEvolve 在 Phase 2 發現的策略（Visualizer / diff 可驗證）**：

1. **Direct review 捷徑**：強化 `analyze_reviews_task` 提取 matched stars / snippet，供 `prediction_modeler` 複用。  
2. **多源綜合**：`simulate_review_task` 明確引用四份前序報告，並禁止提及「資料缺失」。  
3. **Context 紀律**：`internet_research_task` 保留但收斂為 ≤5 bullet general insights，避免稀釋關鍵欄位。  
4. **零結構失敗**：兩 run 各 292 個體、**0 次 combined_score=0**，structure guard 確保演化不破壞 YAML 契約。

**Gen-0 vs Best 比對檔案**（供 Visualizer / 簡報截圖）：

| 階段 | Gen-0 | Best |
|------|-------|------|
| Phase 1 | `docs/assets/evolution/final_basicOnly_gen0.yaml` | `config/openevolve_output/final_basicOnly/best/best_program.yaml` |
| Phase 2 | `docs/assets/evolution/final_agentTask_gen0.yaml` | `config/openevolve_output/final_agentTask/best/best_program.yaml` |

---

### 一句話結論

我們以 **「人設管線、機器優化文案」的兩階段 OpenEvolve** 策略，把 Yelp 評論模擬從 0.91 推進至 **0.9999**；Phase 1 教會模型如何寫星等 heuristic，Phase 2 透過歷史評論比對在 iter 45 完成最後躍升。完整設計細節見 §2，checkpoint / 祖先鏈見 §3。

---

## 2. Novel Design（設計創新）

**協作模式**：CrewAI Sequential；`simulate_review_task` 必須最後，輸出 `{"stars", "review"}` JSON。

### Phase 1：3 Agent × 3 Task

```
user_analyst → analyze_user_task
item_analyst → analyze_item_task
prediction_modeler → simulate_review_task → JSON
```

| Agent | 工具（Task 層） | 策略重點 |
|-------|----------------|---------|
| `user_analyst` | `search_user_profile_data`、`search_historical_reviews_data` | 缺資料 default 3.8 星 |
| `item_analyst` | `search_restaurant_feature_data`、`search_historical_reviews_data` | 查商家特徵與輿論 |
| `prediction_modeler` | 無工具 | `(user_avg + item_stars)/2 ± 0.5~1.0` |

進化增益主要來自 **prompt 精煉**（非換工具），iter 15 達 0.9412 後不再突破。

### Phase 2：5 Agent × 5 Task（在 Phase 1 Best 上擴充）

```
internet_research_task → analyze_user_task → analyze_item_task
  → analyze_reviews_task → simulate_review_task → JSON
```

**新增**：
- `internet_researcher` + `internet_research_task`（`search_internet`，僅 general 趨勢）
- `review_analyst` + `analyze_reviews_task`（`lookup_reviews_by_user_and_item`，direct match）

---

## 3. Evolution Analysis（進化分析）

**設定**：50 iterations、`gpt-4.1-mini`、population 50 / 3 islands、full rewrite、seed 42。

### 分數軌跡

| Phase | 關鍵轉折 | 解讀 |
|-------|---------|------|
| Phase 1 | iter 15 → 0.9412，之後持平 | 3-agent 上限約 0.94 |
| Phase 2 | iter 5~40 → 0.9666；**iter 45 → 0.9999** | 需足夠迭代整合 review 鏈路 |

### 祖先鏈

```
Phase 1: gen0(0.91) → gen1(0.94) → gen3(0.9412) Best
Phase 2: gen0(0.96) → gen1~4(0.94~0.95 震盪) → gen5(0.9999) Best
```

建議截圖：演化樹、Performance 曲線、Gen-0 vs Best diff。

---

## 4. 設計 ↔ 評分對齊

| 設計 | 影響 |
|------|------|
| 星等計算 heuristic | 星等預測準度（Phase 1 主貢獻） |
| `lookup_reviews_by_user_and_item` | 星等 + topic（Phase 2 iter 45 突破） |
| 評論引用 strengths/weaknesses | topic（權重最高） |

---