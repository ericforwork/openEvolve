"""
SimulationCrew — 對齊 config/tasks_simulator.yaml 的完整任務鏈與
config/agents.yaml（或 OPENEVOLVE_AGENTS_YAML / serving_flow 覆寫）內全部 agent。

OpenEvolve 演化 tasks 時會設定 OPENEVOLVE_TASKS_YAML；缺漏的 task 會與底稿
config/tasks_simulator.yaml 合併。任務順序與 task 名稱與 tasks_simulator.yaml 一致。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

import yaml
from crewai import Agent, Crew, Process, Task

from src.utils.yaml_sanitize import sanitize_agents_yaml_text
from src.tools.simulator_bound_tools import (
    lookup_item_by_id,
    lookup_user_by_id,
    search_historical_reviews_data,
    search_restaurant_feature_data,
    search_user_profile_data,
)

# 與 config/tasks_simulator.yaml 中定義順序一致（依檔案由上而下；最後一步必須輸出 JSON）
_TASK_ORDER: List[str] = [
    "analyze_user_task",
    "analyze_item_task",
    "simulate_review_task",
]

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_AGENTS_PATH = _PROJECT_ROOT / "config" / "agents.yaml"
_DEFAULT_TASKS_PATH = _PROJECT_ROOT / "config" / "tasks_simulator.yaml"

# 與 tasks_simulator.yaml 中 task.agent 指派一致
_REQUIRED_AGENT_KEYS: frozenset[str] = frozenset(
    {
        "user_analyst",
        "item_analyst",
        "prediction_modeler",
    }
)


def _validate_agents_mapping(cfg: Dict[str, Any], *, source: str) -> None:
    """確保底稿或合併後 mapping 含齊必填 agent，且每個為 dict（避免 KeyError）。"""
    missing = sorted(_REQUIRED_AGENT_KEYS - cfg.keys())
    if missing:
        raise ValueError(
            f"agents 設定不完整（來源：{source}）。缺少下列 top-level key：{missing}。\n"
            f"請檢查並還原 `config/agents.yaml`（或 OpenEvolve 覆寫檔）中的對應區塊。"
        )
    bad: List[str] = []
    for k in _REQUIRED_AGENT_KEYS:
        v = cfg.get(k)
        if not isinstance(v, dict):
            bad.append(f"{k!r} -> {type(v).__name__}")
    if bad:
        raise ValueError(
            f"agents 設定型別錯誤（來源：{source}）。下列 key 必須為 mapping（role/goal/backstory 等）："
            + "; ".join(bad)
        )


def _parse_agents_yaml_text(
    text: str,
    *,
    path_for_error: str,
    validate_required_keys: bool,
) -> Dict[str, Any]:
    """
    sanitize + yaml.safe_load；失敗時附檔名與簡短除錯提示。
    validate_required_keys=True 時檢查 _REQUIRED_AGENT_KEYS。
    """
    sanitized = sanitize_agents_yaml_text(text)
    try:
        data = yaml.safe_load(sanitized)
    except yaml.YAMLError as e:
        raise ValueError(
            f"YAML 解析失敗（檔案：{path_for_error}）。常見原因：縮排錯誤、少冒號、"
            f"兩份 root 黏在一起、或字串未結束。\n"
            f"原始錯誤：{e}"
        ) from e
    if data is None:
        raise ValueError(
            f"YAML 無有效內容（檔案：{path_for_error}）：解析結果為 null（檔案空白或僅註解）。"
        )
    if not isinstance(data, dict):
        raise TypeError(
            f"agents YAML 根節點必須為 mapping（檔案：{path_for_error}），實際為 {type(data).__name__}。"
        )
    if validate_required_keys:
        _validate_agents_mapping(data, source=path_for_error)
    return data


def _load_default_agents_base() -> Dict[str, Any]:
    text = _DEFAULT_AGENTS_PATH.read_text(encoding="utf-8")
    return _parse_agents_yaml_text(
        text,
        path_for_error=str(_DEFAULT_AGENTS_PATH),
        validate_required_keys=True,
    )


def _merge_agents_with_defaults(cfg: Any) -> Dict[str, Any]:
    """OpenEvolve 可能只輸出部分 agent；缺鍵時從 config/agents.yaml 補齊。"""
    base = _load_default_agents_base()
    if not isinstance(cfg, dict):
        return base
    merged = dict(base)
    for k, v in cfg.items():
        if isinstance(v, dict) and k in merged:
            merged[k] = v
    _validate_agents_mapping(
        merged,
        source=f"合併結果（底稿 {_DEFAULT_AGENTS_PATH} + 覆寫檔中的 agent 區塊）",
    )
    return merged


def _resolve_agents_config(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return _merge_agents_with_defaults(raw)
    if isinstance(raw, str):
        p = Path(raw)
        if not p.is_absolute():
            p = (_PROJECT_ROOT / raw).resolve()
        text = p.read_text(encoding="utf-8")
        loaded = _parse_agents_yaml_text(
            text,
            path_for_error=str(p),
            validate_required_keys=False,
        )
        return _merge_agents_with_defaults(loaded)
    return _merge_agents_with_defaults({})


def _validate_tasks_mapping(cfg: Dict[str, Any], *, source: str) -> None:
    """確保底稿或合併後 tasks 含齊 _TASK_ORDER，且每個 task 為 dict、含 agent。"""
    missing = [k for k in _TASK_ORDER if k not in cfg]
    if missing:
        raise ValueError(
            f"tasks 設定不完整（來源：{source}）。缺少下列 task key：{missing}。\n"
            f"請檢查 `config/tasks_simulator.yaml`（或 OpenEvolve 覆寫檔），勿刪除或改名這些 task。"
        )
    bad: List[str] = []
    for k in _TASK_ORDER:
        v = cfg.get(k)
        if not isinstance(v, dict):
            bad.append(f"{k!r} -> {type(v).__name__}")
            continue
        if "agent" not in v:
            bad.append(f"{k!r} 缺少 'agent' 欄位")
    if bad:
        raise ValueError(
            f"tasks 設定錯誤（來源：{source}）：" + "; ".join(bad)
        )


def _parse_tasks_yaml_text(
    text: str,
    *,
    path_for_error: str,
    validate_required_keys: bool,
) -> Dict[str, Any]:
    sanitized = sanitize_agents_yaml_text(text)
    try:
        data = yaml.safe_load(sanitized)
    except yaml.YAMLError as e:
        raise ValueError(
            f"YAML 解析失敗（檔案：{path_for_error}）。常見原因：縮排錯誤、少冒號、"
            f"兩份 root 黏在一起。\n原始錯誤：{e}"
        ) from e
    if data is None:
        raise ValueError(
            f"YAML 無有效內容（檔案：{path_for_error}）：解析結果為 null。"
        )
    if not isinstance(data, dict):
        raise TypeError(
            f"tasks YAML 根節點必須為 mapping（檔案：{path_for_error}），實際為 {type(data).__name__}。"
        )
    if validate_required_keys:
        _validate_tasks_mapping(data, source=path_for_error)
    return data


def _load_default_tasks_base() -> Dict[str, Any]:
    text = _DEFAULT_TASKS_PATH.read_text(encoding="utf-8")
    return _parse_tasks_yaml_text(
        text,
        path_for_error=str(_DEFAULT_TASKS_PATH),
        validate_required_keys=True,
    )


def _merge_tasks_with_defaults(cfg: Any) -> Dict[str, Any]:
    """OpenEvolve 可能只輸出部分 task；缺鍵時從 config/tasks_simulator.yaml 補齊。"""
    base = _load_default_tasks_base()
    if not isinstance(cfg, dict):
        return base
    merged = dict(base)
    for k, v in cfg.items():
        if isinstance(v, dict) and k in merged:
            merged[k] = v
    _validate_tasks_mapping(
        merged,
        source=f"合併結果（底稿 {_DEFAULT_TASKS_PATH} + OpenEvolve 覆寫）",
    )
    return merged


def _resolve_tasks_config() -> Dict[str, Any]:
    """一般執行用底稿；evaluate() 會設 OPENEVOLVE_TASKS_YAML 指向突變檔。"""
    path = os.environ.get("OPENEVOLVE_TASKS_YAML")
    if not path:
        return _merge_tasks_with_defaults({})
    p = Path(path)
    if not p.is_absolute():
        p = (_PROJECT_ROOT / path).resolve()
    text = p.read_text(encoding="utf-8")
    loaded = _parse_tasks_yaml_text(
        text,
        path_for_error=str(p),
        validate_required_keys=False,
    )
    return _merge_tasks_with_defaults(loaded)


def parse_agents_yaml_file_for_flow(path: str) -> Dict[str, Any]:
    """
    供 serving_flow 讀取 agents_config_path：與 SimulationCrew 相同 sanitize + 錯誤訊息。
    覆寫檔可為部分 agent；合併與必填檢查在 crew() 內 _resolve_agents_config 完成。
    """
    p = Path(path)
    if not p.is_absolute():
        p = (_PROJECT_ROOT / path).resolve()
    text = p.read_text(encoding="utf-8")
    return _parse_agents_yaml_text(
        text,
        path_for_error=str(p),
        validate_required_keys=False,
    )


class SimulationCrew:
    """由 tasks_simulator.yaml 驅動的 Sequential Crew（3 task / 3 agent）。"""

    agents_config: Any = str(_DEFAULT_AGENTS_PATH.relative_to(_PROJECT_ROOT))

    def __init__(self) -> None:
        # 與 CrewBase 相容：允許 serving_flow 直接指派 agents_config 為 dict
        pass

    def _build_agents(self, agents_cfg: Dict[str, Any]) -> Dict[str, Agent]:
        return {
            "user_analyst": Agent(
                config=agents_cfg["user_analyst"],
                verbose=False,
                tools=[
                    lookup_user_by_id,
                    search_user_profile_data,
                    search_historical_reviews_data,
                ],
            ),
            "item_analyst": Agent(
                config=agents_cfg["item_analyst"],
                verbose=False,
                tools=[
                    lookup_item_by_id,
                    search_restaurant_feature_data,
                    search_historical_reviews_data,
                ],
                max_rpm=10,
            ),
            "prediction_modeler": Agent(
                config=agents_cfg["prediction_modeler"],
                verbose=False,
            ),
        }

    def crew(self) -> Crew:
        agents_cfg = _resolve_agents_config(
            getattr(self, "agents_config", None) or SimulationCrew.agents_config
        )
        tasks_cfg = _resolve_tasks_config()

        by_name = self._build_agents(agents_cfg)
        agents_list = [
            by_name["user_analyst"],
            by_name["item_analyst"],
            by_name["prediction_modeler"],
        ]

        tasks_list: List[Task] = []
        for key in _TASK_ORDER:
            if key not in tasks_cfg:
                raise KeyError(f"tasks 設定缺少 task 定義: {key}")
            block = tasks_cfg[key]
            if not isinstance(block, dict):
                raise TypeError(f"task {key} 必須為 mapping")
            agent_key = block.get("agent")
            if agent_key not in by_name:
                raise KeyError(f"task {key} 的 agent={agent_key!r} 無對應 Agent")
            cfg_copy = {k: v for k, v in block.items() if k != "agent"}
            tasks_list.append(
                Task(config=cfg_copy, agent=by_name[agent_key]),
            )

        return Crew(
            agents=agents_list,
            tasks=tasks_list,
            process=Process.sequential,
            verbose=os.environ.get("SIMULATION_CREW_VERBOSE", "true").lower() in ("1", "true", "yes"),
        )
