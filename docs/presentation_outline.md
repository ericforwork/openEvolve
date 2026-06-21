# Presentation Outline — 兩階段 OpenEvolve 進化

> 對應完整報告：`docs/TECHNICAL_REPORT.md`

---

## Slide 1 — 標題

- **標題**：OpenEvolve × CrewAI：兩階段 Yelp 評論模擬進化
- **副標**：Basic（3-agent）→ Extended（5-agent）
- **結果**：0.9412 → **0.9999** `combined_score`

---

## Slide 2 — 評分目標

- `combined_score = (preference_estimation + review_generation) / 2`
- 星等 MAE + 評論 topic（權重最高）
- 輸出契約：`{"stars": float, "review": str}`

---

## Slide 3 — Novelty：兩階段策略（重點）

```
Phase 1 (final_basicOnly)     Phase 2 (final_agentTask)
3 agents × 3 tasks      →     5 agents × 5 tasks
Gen-0: 0.910                    Gen-0: 0.958 (繼承 P1 Best)
Best:  0.941                    Best:  0.9999
```

- **先簡後繁**：避免一次進化過大搜尋空間
- Phase 2 Gen-0 三核心 agent = Phase 1 Best（已驗證）

---

## Slide 4 — Phase 1 Crew Diagram

```
user_analyst → analyze_user_task
item_analyst → analyze_item_task
prediction_modeler → simulate_review_task → JSON
```

- Sequential、lookup backstory + search task tools
- 無 review 比對、無網搜

---

## Slide 5 — Phase 2 Crew Diagram

```
internet_researcher → internet_research_task
user_analyst → analyze_user_task
item_analyst → analyze_item_task
review_analyst → analyze_reviews_task  ← 新增
prediction_modeler → simulate_review_task → JSON
```

- `lookup_reviews_by_user_and_item` 為 iter 45 突破關鍵

---

## Slide 6 — Agent & Tool 對照（一頁表）

| Agent | Phase 1 | Phase 2 新增/變更 |
|-------|---------|------------------|
| user_analyst | search_user_profile_data | 沿用 |
| item_analyst | search_restaurant_feature_data | 沿用 |
| prediction_modeler | 無工具 | 綜合 4 份前序報告 |
| review_analyst | — | lookup_reviews_by_user_and_item |
| internet_researcher | — | search_internet |

---

## Slide 7 — Evolution Analysis：分數軌跡

**Phase 1**：iter 15 達 0.9412 後平台  
**Phase 2**：iter 5–40 維持 0.9666 → **iter 45 躍升至 0.9999**

（附 checkpoint 折線圖或 visualizer Performance tab 截圖）

---

## Slide 8 — Visualizer 發現

- Evolution tree：Phase 2 更深（gen=5）
- 3 islands、無 0 分突變（structure guard 穩定）
- Diff viewer：Gen-0 vs Best 的 `analyze_reviews_task` / `simulate_review_task` 變化

```bash
make visualize OUTPUT=config/openevolve_output/final_basicOnly
make visualize OUTPUT=config/openevolve_output/final_agentTask
```

---

## Slide 9 — 祖先鏈（Evolution Path）

**Phase 1 Best**：gen0(0.91) → gen1(0.94) → gen3(0.941)  
**Phase 2 Best**：gen0(0.96) → … → gen5(0.9999)

- 中期分數震盪 = 探索期
- 最終子代整合前期有效突變

---

## Slide 10 — 結論 & Takeaways

1. **漸進式進化**優於一次到位（3-agent 上限 ≈0.94）
2. **歷史評論比對**是 Phase 2 最大邊際效益
3. **結構鎖 + JSON 契約**確保 292 個體零失敗
4. 後續：全量 41 題驗證、統一 lookup-first 工具鏈

---

## 備用 Q&A

- **為何 Phase 1 用 search 而非 lookup？** 初期擴大演化空間，backstory 已引導 lookup 思維。
- **為何 iter 45 才突破？** 5-task 管線需更多迭代讓 review 鏈路與 predictor 對齊。
- **internet_research 有無幫助？** Best 仍保留但收斂為 5 bullet general insights。
