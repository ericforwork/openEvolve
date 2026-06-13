# Makefile — AgentSocietyChallenge_OpenEvolve
#
# 統一封裝常用指令，避免重複輸入冗長的 uv 命令。
# 所有 target 都會自動讀取 .env 內的環境變數。

.DEFAULT_GOAL := help

# OpenEvolve 進化參數（可由 CLI 覆寫，例如：make evolve ITERS=20 TASKS=3）
ITERS ?= 10
TASKS ?= 5
# 所有進化 run 的根目錄；每次 make evolve 預設會在下面再建 YYYYMMDD_HHMMSS 子資料夾
OUTPUT_BASE ?= config/openevolve_output
# 精確輸出路徑（留空＝evolve 自動時間戳子資料夾；visualize / 手動覆寫時可指定）
OUTPUT ?=

# 傳給 evaluator / OpenEvolve（Windows cmd 不支援「VAR=value cmd」前綴，用 export 跨平台）
export OPENEVOLVE_NUM_TASKS := $(TASKS)
# OpenEvolve 以 open(..., "r") 讀 YAML 未指定 UTF-8；繁中 Windows 預設 cp950 會解碼失敗
export PYTHONUTF8 := 1

# ============================================================================
# 環境
# ============================================================================
.PHONY: install
install:  ## 同步依賴（uv sync）
	uv sync

# ============================================================================
# 測試
# ============================================================================
.PHONY: test-mock
test-mock:  ## Mock 模式整合測試（零成本）
	uv run --env-file .env python run_test.py --mock

.PHONY: test
test:  ## 真實 LLM 整合測試（全部 task）
	uv run --env-file .env python run_test.py

.PHONY: smoke
smoke:  ## Smoke test（只跑 1 個 task）
	uv run --env-file .env python run_test.py --tasks 1

# ============================================================================
# OpenEvolve 進化
# ============================================================================
# evolve：預設輸出至 $(OUTPUT_BASE)/YYYYMMDD_HHMMSS/（其下含 best、checkpoints）
ifeq ($(strip $(OUTPUT)),)
.PHONY: evolve
evolve:  ## 啟動 OpenEvolve 進化（可調 ITERS=N TASKS=N；輸出至 OUTPUT_BASE/時間戳）
	@$(eval EVOLVE_OUT := $(OUTPUT_BASE)/$(shell uv run python scripts/evolve_timestamp.py))
	@echo [evolve] OpenEvolve 輸出目錄: $(EVOLVE_OUT)
	uv run --env-file .env python -m openevolve.cli \
	    config/tasks_simulator.yaml \
	    openevolve_evaluator.py \
	    --config config/openevolve_config.yaml \
	    --output $(EVOLVE_OUT) \
	    --iterations $(ITERS)
else
.PHONY: evolve
evolve:  ## 啟動 OpenEvolve 進化（可調 ITERS=N TASKS=N；已指定 OUTPUT=固定路徑）
	uv run --env-file .env python -m openevolve.cli \
	    config/tasks_simulator.yaml \
	    openevolve_evaluator.py \
	    --config config/openevolve_config.yaml \
	    --output $(OUTPUT) \
	    --iterations $(ITERS)
endif

# evolve-resume：CHECKPOINT 須在命令列指定（Windows 無 bash 的 [ -z ... ]）
ifeq ($(strip $(CHECKPOINT)),)
.PHONY: evolve-resume
evolve-resume:  ## 從 checkpoint 繼續（須指定 CHECKPOINT=path）
	@echo ERROR: 必須指定 CHECKPOINT，例如：
	@echo   make evolve-resume CHECKPOINT=config/openevolve_output/20250612_143022/checkpoints/checkpoint_10
	@echo （可選）若 checkpoint 不在預設 run 根下，請加 OUTPUT=該次 run 根目錄
	@exit 1
else
# 未指定 OUTPUT 時，由 .../run_id/checkpoints/checkpoint_N 推回 run 根目錄
ifneq ($(strip $(OUTPUT)),)
RESUME_OUTPUT := $(OUTPUT)
else
RESUME_OUTPUT := $(patsubst %/,%,$(dir $(dir $(CHECKPOINT))))
endif
.PHONY: evolve-resume
evolve-resume:  ## 從 checkpoint 繼續（CHECKPOINT=...；OUTPUT 可省略，會自動推導）
	uv run --env-file .env python -m openevolve.cli \
	    config/tasks_simulator.yaml \
	    openevolve_evaluator.py \
	    --config config/openevolve_config.yaml \
	    --output $(RESUME_OUTPUT) \
	    --checkpoint $(CHECKPOINT) \
	    --iterations $(ITERS)
endif

.PHONY: evolve-test
evolve-test:  ## 本地整合測試 evaluator（不啟動進化）
	uv run --env-file .env python openevolve_evaluator.py

.PHONY: visualize
visualize:  ## 啟動視覺化（--path 須指向單次 run，例如 OUTPUT=config/openevolve_output/20250612_143022）
	uv run python scripts/run_openevolve_visualizer.py --path $(if $(strip $(OUTPUT)),$(OUTPUT),$(OUTPUT_BASE))

.PHONY: visualizer
visualizer: visualize  ## 同 visualize（常見拼錯別名）

# ============================================================================
# 資料處理
# ============================================================================
.PHONY: sample-dataset
sample-dataset:  ## 從 data/test_review_subset.json 取樣評估資料集
	uv run python src/utils/create_sampled_dataset.py --n 5

# ============================================================================
# 維護
# ============================================================================
.PHONY: clean
clean:  ## 清理 __pycache__ 與 .pyc
	find . -type d -name __pycache__ ! -path "./.venv/*" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" ! -path "./.venv/*" -delete 2>/dev/null || true

.PHONY: clean-output
clean-output:  ## 清除所有 OpenEvolve 輸出（⚠️ 刪除 OUTPUT_BASE 下含各次時間戳資料夾）
	@echo "⚠️  這會刪除整個 $(OUTPUT_BASE)（含歷次進化結果）。確定？(Ctrl+C 取消，Enter 繼續)"
	@read CONFIRM
	rm -rf $(OUTPUT_BASE)

# ============================================================================
# Help
# ============================================================================
.PHONY: help
help:  ## 列出所有 target
	@echo "可用指令："
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	    awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
