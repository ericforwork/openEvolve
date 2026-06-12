# 對話整理：OpenEvolve、Git、執行與專案結構筆記

> 本檔由對話內容彙整，方便日後查閱；實際指令請以專案內 `CLAUDE.md`、`Makefile` 為準。

---

## 1. GitHub 與 Git

### 將本機專案接到新的 GitHub 儲存庫

1. 在 GitHub 建立**空** repo（勿勾 README，避免無關初始 commit）。
2. `git init`、`git branch -M main`、`git add .`、`git commit`。
3. `git remote add origin <HTTPS>`、`git push -u origin main`。

### 刪除本機 Git

刪除專案根目錄的 **`.git`** 即不再為儲存庫；歷史與遠端設定一併消失。

### `.env`

`.gitignore` 已含 `.env`。若仍出現在 `git status`，使用 `git rm --cached .env`。

### Push 被拒：`workflow` scope

若錯誤為 PAT 無法更新 `.github/workflows/*.yml`，可選：

- 為 PAT 加上 **`workflow`** 權限；或  
- 刪除該 workflow 檔後再 push（本專曾刪 `python-publish.yml`）。

### SourceTree

**檔案 → 加入** 現有資料夾；遠端設 `origin`；在 **工具 → 選項 → 驗證** 設定 GitHub 或 PAT。

---

## 2. 執行專案

- 依賴：**`uv sync`**（或 `make install`）。
- Mock：`make test-mock` 或 `uv run --env-file .env python run_test.py --mock`。
- 真實 LLM：`make test`；單題煙霧：`make smoke`。
- 專案規範：使用 **`uv run`**，見 `CLAUDE.md`。

### 曾修正的語法錯誤

`src/crews/simulation_crew.py` 中 **`item_analyst`** 的 `Agent(...)`：`tools=[...]` 與 **`max_rpm=10`** 之間需有**逗號**，否則 `SyntaxError`。

---

## 3. `make evolve` 在做什麼

- 呼叫 **`openevolve.cli`**，演化 **`config/agents_evolving.yaml`** 內 **EVOLVE-BLOCK**（預設 full rewrite）。
- **`openevolve_evaluator.py`** 的 **`evaluate(program_path)`**：用 Simulator 跑模擬，回傳 **`combined_score`**（即 **`overall_quality`**）。
- 預設參數可見 `Makefile`：`ITERS`、`TASKS`、`OUTPUT_BASE` 等。
- 評分細項（星等 MAE、評論情緒／情緒／主題等）見 **`websocietysimulator/tools/evaluation_tool.py`** 內 `SimulationEvaluator`。

---

## 4. OpenEvolve 輸出位置與是否覆寫

### 輸出目錄（已改 Makefile 後）

- 根目錄：**`OUTPUT_BASE`**，預設 `config/openevolve_output`。
- 每次 **`make evolve`**（未指定 **`OUTPUT=`**）會建立 **`YYYYMMDD_HHMMSS`** 子資料夾，其下有 **`best/`**、**`checkpoints/`**、**`logs/`** 等，避免覆寫前一次 run。
- 終端機會印：`[evolve] OpenEvolve 輸出目錄: ...`
- 固定路徑：`make evolve OUTPUT=config/openevolve_output`。
- **`make evolve-resume`**：可省略 **`OUTPUT`**，Makefile 會由 **`CHECKPOINT`** 路徑推回該次 run 根目錄。
- **`make visualize`**：需指向單次 run，例如 **`OUTPUT=config/openevolve_output/20250612_143022`**。
- **`make clean-output`**：會刪除整個 **`OUTPUT_BASE`**（含所有時間戳子資料夾）。

### 行為補充（套件層級）

- 不會先整包刪除輸出根目錄。
- **`best/`** 內固定檔名每次跑完會**覆寫**。
- **`checkpoints/checkpoint_N`**：同名子資料夾會再寫入時**覆寫**；較大輪次的舊子資料夾可能仍留在磁碟上。

### 本次對話中曾修改的檔案（時間戳輸出）

1. **`Makefile`**  
2. **`CLAUDE.md`**  
3. **`docs/student_integration_guide.md`**  

另曾修正：**`src/crews/simulation_crew.py`**（逗號）。

---

## 5. 進化會改哪些區塊

以 **`config/agents_evolving.yaml`** 為準：**`# EVOLVE-BLOCK-START` ～ `# EVOLVE-BLOCK-END`** 之間的 agent 定義會被演化（例如 **`prediction_modeler`**、**`reviewer`**、**`internet_researcher`**、**`project_manager`** 等，以檔案實際內容為準）。

**`openevolve_config.yaml`** 內 `system_message` 若仍寫其他 agent 名稱，可能與目前 YAML 不一致，必要時應自行改文案對齊。

---

## 6. 四份 `tasks_*.yaml` 與進化路徑

| 檔案 | 用途摘要 |
|------|------------|
| **`tasks_simulator.yaml`** | 對齊 AgentSociety **InteractionTool** 查詢格式；三 task 串行。 |
| **`tasks_sequential.yaml`** | 給 **`crew_sequential.py`** 的線性流程。 |
| **`tasks_hierarchical.yaml`** | 給 **`crew_hierarchical.py`** 的階層流程。 |
| **`tasks_collaborative.yaml`** | 給 **`crew_collaborative.py`** 的協作流程。 |

### 進化／`run_test` 實際走的 Crew 路徑

**`crewai_simulation_agent.py` → `AgentSocietyServingFlow` → `SimulationCrew`**

- **會用**：`src/crews/simulation_crew.py` + **`config/tasks_simulator.yaml`**（寫死在 `SimulationCrew`）+ 當下的 **`agents_evolving.yaml`（或 `agents.yaml`）** 中，**僅有在 `SimulationCrew` 內宣告的三個 agent**：**`user_analyst`**、**`item_analyst`**、**`prediction_modeler`**。
- **不會**載入另三份 `tasks_*.yaml`，也**不會**跑 `crew_sequential` / `crew_hierarchical` / `crew_collaborative`。
- YAML 內其他 agent 若無對應 `@agent`，**不會進 crew**。

整體進化評分另含 **`websocietysimulator.Simulator`**、`dummy_dataset` / `dummy_tasks` / `dummy_groundtruth` 等模擬本體。

---

## 7. 快速核對清單

| 問題 | 摘要答案 |
|------|----------|
| 進化時 Crew 用哪幾個設定檔？ | `simulation_crew.py` + `tasks_simulator.yaml` +（突變後的）`agents_evolving.yaml`。 |
| 每次 evolve 輸出會蓋掉嗎？ | 預設改為時間戳子資料夾；`best` 與同名 `checkpoint_N` 在**該次 run 資料夾內**仍會覆寫。 |
| 如何保留每次結果？ | 使用預設 `make evolve` 的時間戳目錄，或自訂 `OUTPUT=`。 |

---

*文件產生自對話整理，若與程式後續變更不一致，請以倉庫內最新檔案為準。*
