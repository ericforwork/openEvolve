import os
import sys
import logging
import tempfile
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

import yaml

project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.append(project_dir)

from src.utils.evolve_yaml_guard import validate_evolved_program_structure
from websocietysimulator import Simulator
from crewai_simulation_agent import CrewAISimulationAgent
from src.utils.yaml_sanitize import sanitize_agents_yaml_text

# 整個 simulation 的 hard timeout（秒）。超時則回傳 fallback fitness 讓 OpenEvolve 繼續。
# 預設 15 分鐘，可由 OPENEVOLVE_SIM_TIMEOUT env var 覆寫。
SIM_TIMEOUT_SEC = int(os.environ.get("OPENEVOLVE_SIM_TIMEOUT", "900"))

# 扁平「僅 tasks」程式檔偵測用（與 SimulationCrew._TASK_ORDER 一致）
_TASK_ROOT_KEYS = frozenset(
    {
        "analyze_user_task",
        "analyze_item_task",
        "simulate_review_task",
    }
)

# ---------------------------------------------------------------------------
# Lazy singleton: Simulator is expensive to initialize (loads LMDB dataset).
# OpenEvolve imports this module once and calls evaluate() many times, so we
# initialize on the first call and reuse the same instance afterward.
# ---------------------------------------------------------------------------
_simulator: Simulator = None


def _get_simulator() -> Simulator:
    global _simulator
    if _simulator is None:
        logging.getLogger().setLevel(logging.WARNING)
        print("[Evaluator] Initializing Simulator with sampled dataset (one-time)...")
        _simulator = Simulator(data_dir="dummy_dataset", device="cpu", cache=True)
        _simulator.set_task_and_groundtruth(
            task_dir="dummy_tasks",
            groundtruth_dir="dummy_groundtruth",
        )
        _simulator.set_agent(CrewAISimulationAgent)
        print("[Evaluator] Simulator ready.")
    return _simulator


def _prepare_evolve_env(program_path: str) -> tuple[str | None, str | None, list[str], str]:
    """
    依程式檔格式設定 OPENEVOLVE_* 路徑：
    - `agents` + `tasks` 兩個頂層 key → 聯合 bundle，寫兩個暫存檔。
    - 根層含任一固定 task 名 → 視為僅 tasks（路徑即 program_path）。
    - 否則 → 視為僅 agents（路徑即 program_path）。
    回傳 (agents_yaml_path|None, tasks_yaml_path|None, 要刪除的暫存路徑列表, 人類可讀標籤)。
    """
    with open(program_path, encoding="utf-8") as f:
        raw = f.read()
    data = yaml.safe_load(sanitize_agents_yaml_text(raw))
    if not isinstance(data, dict):
        data = {}

    temp_paths: list[str] = []

    if isinstance(data.get("agents"), dict) and isinstance(data.get("tasks"), dict):
        fa = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        )
        yaml.dump(
            data["agents"],
            fa,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )
        fa.close()
        temp_paths.append(fa.name)
        ft = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        )
        yaml.dump(
            data["tasks"],
            ft,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )
        ft.close()
        temp_paths.append(ft.name)
        return fa.name, ft.name, temp_paths, "agents+tasks bundle"

    if _TASK_ROOT_KEYS & data.keys():
        return None, program_path, [], "tasks-only"

    return program_path, None, [], "agents-only"


def evaluate(program_path: str) -> dict:
    """
    Module-level function required by OpenEvolve.

    OpenEvolve writes the mutated YAML to a temp file (suffix configured as
    .yaml) and passes the FILE PATH here as the sole argument.

    Program formats:
    - Joint: root keys `agents` and `tasks` (see config/openevolve_agents_tasks.yaml).
    - Tasks-only: flat task map (e.g. config/tasks_simulator.yaml).
    - Agents-only: flat agent map (e.g. config/agents_evolving.yaml).

    Returns a dict with 'combined_score' as the primary fitness metric (required
    by OpenEvolve), plus individual sub-metrics for MAP-Elites feature tracking.

    combined_score = overall_quality (0–1):
      overall_quality = (preference_estimation + review_generation) / 2
    where preference_estimation = 1 - normalized_star_MAE.
    """
    simulator = _get_simulator()
    ok, guard_msg = validate_evolved_program_structure(program_path)
    if not ok:
        print(f"[Evaluator] Structure guard: REJECTED — {guard_msg}")
        return {"combined_score": 0.0}

    temp_paths: list[str] = []
    try:
        agents_path, tasks_path, temp_paths, label = _prepare_evolve_env(program_path)

        if agents_path:
            os.environ["OPENEVOLVE_AGENTS_YAML"] = agents_path
        else:
            os.environ.pop("OPENEVOLVE_AGENTS_YAML", None)

        if tasks_path:
            os.environ["OPENEVOLVE_TASKS_YAML"] = tasks_path
        else:
            os.environ.pop("OPENEVOLVE_TASKS_YAML", None)

        num_tasks = int(os.environ.get("OPENEVOLVE_NUM_TASKS", "5"))
        print(
            f"\n[Evaluator] program={program_path}  mode={label}  "
            f"sim_tasks={num_tasks}  timeout={SIM_TIMEOUT_SEC}s"
        )

        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    simulator.run_simulation,
                    number_of_tasks=num_tasks,
                    enable_threading=True,
                    max_workers=2,
                )
                future.result(timeout=SIM_TIMEOUT_SEC)
        except FuturesTimeout:
            print(
                f"[Evaluator] ⏱  Simulation exceeded {SIM_TIMEOUT_SEC}s — returning fallback score"
            )
            return {"combined_score": 0.0}

        print("[Evaluator] Calculating official metrics...")
        eval_results = simulator.evaluate()

        metrics = eval_results.get("metrics", {}) if isinstance(eval_results, dict) else {}
        overall_quality = metrics.get("overall_quality", 0.0)
        pref_estimation = metrics.get("preference_estimation", 0.0)
        review_generation = metrics.get("review_generation", 0.0)

        print(
            f"[Evaluator] preference_estimation={pref_estimation:.4f}, "
            f"review_generation={review_generation:.4f}, "
            f"overall_quality={overall_quality:.4f}  →  combined_score={overall_quality:.4f}"
        )

        return {"combined_score": float(overall_quality)}

    except Exception as e:
        print(f"[Evaluator] ❌ Error during evaluation: {e}")
        import traceback

        traceback.print_exc()
        return {"combined_score": 0.0}
    finally:
        os.environ.pop("OPENEVOLVE_AGENTS_YAML", None)
        os.environ.pop("OPENEVOLVE_TASKS_YAML", None)
        for p in temp_paths:
            try:
                os.unlink(p)
            except OSError:
                pass


if __name__ == "__main__":
    bundle = os.path.join(project_dir, "config", "openevolve_agents_tasks.yaml")
    fallback = os.path.join(project_dir, "config", "tasks_simulator.yaml")
    yaml_path = bundle if os.path.isfile(bundle) else fallback
    if os.path.exists(yaml_path):
        with open(yaml_path, encoding="utf-8") as f:
            content = f.read()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            fitness = evaluate(tmp_path)
            print(f"Test execution completed with evaluated fitness score: {fitness}")
        finally:
            os.remove(tmp_path)
