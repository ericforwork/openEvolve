"""
進化程式結構檢查：只允許在「與底稿相同的 key 集合」下改文字，
禁止增刪頂層 agent／task、禁止改名、禁止改 task 的 `agent:` 欄位、禁止在區塊內增刪子 key（子 key 集合須與底稿逐項一致，只改字串值）。

違規時 evaluate() 直接給 0 分，避免浪費模擬與誤導 MAP-Elites。
可用環境變數 OPENEVOLVE_SKIP_STRUCTURE_GUARD=1 關閉（除錯用）。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Set, Tuple

import yaml

from src.utils.yaml_sanitize import sanitize_agents_yaml_text

# 專案根目錄：本檔在 src/utils/，故 parent ×3
_REPO = Path(__file__).resolve().parent.parent.parent
_AGENTS_BASE = _REPO / "config" / "agents.yaml"
_TASKS_BASE = _REPO / "config" / "tasks_simulator.yaml"

# 與 openevolve_evaluator._TASK_ROOT_KEYS 一致：用於辨識「僅 tasks」扁平檔
_TASK_ROOT_KEYS: frozenset[str] = frozenset(
    {
        "analyze_user_task",
        "analyze_item_task",
        "simulate_review_task",
    }
)


def _load_mapping(path: Path) -> Dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(sanitize_agents_yaml_text(raw))
    return data if isinstance(data, dict) else {}


def _exact_key_sets(
    evolved: Dict[str, Any],
    base: Dict[str, Any],
    label: str,
) -> str | None:
    be, bb = set(evolved.keys()), set(base.keys())
    if be != bb:
        only_e, only_b = sorted(be - bb), sorted(bb - be)
        parts = [f"{label} 頂層 key 必須與底稿完全一致。"]
        if only_e:
            parts.append(f"多出（不允許）: {only_e}")
        if only_b:
            parts.append(f"缺少（不允許）: {only_b}")
        return "".join(parts)
    return None


def _nested_keys_exact(
    evolved: Dict[str, Any],
    base: Dict[str, Any],
    label: str,
) -> str | None:
    """每個區塊的子 key 集合須與底稿完全一致（只允許改值，不刪不增子欄位）。"""
    for name, ev_block in evolved.items():
        if not isinstance(ev_block, dict):
            return f"{label}[{name!r}] 必須為 mapping"
        bb = base.get(name)
        if not isinstance(bb, dict):
            return f"{label} 底稿缺少 {name!r}"
        if set(ev_block.keys()) != set(bb.keys()):
            only_e = sorted(set(ev_block.keys()) - set(bb.keys()))
            only_b = sorted(set(bb.keys()) - set(ev_block.keys()))
            parts = [f"{label}[{name!r}] 子 key 須與底稿完全一致。"]
            if only_e:
                parts.append(f"多出: {only_e}; ")
            if only_b:
                parts.append(f"缺少: {only_b}")
            return "".join(parts)
    return None


def _tasks_agent_unchanged(evolved: Dict[str, Any], base: Dict[str, Any]) -> str | None:
    for name in base:
        if name not in evolved:
            continue
        eb, bb = evolved[name], base[name]
        if not isinstance(eb, dict) or not isinstance(bb, dict):
            continue
        ea, ba = eb.get("agent"), bb.get("agent")
        if ea != ba:
            return f"tasks[{name!r}] 的 agent 不可修改：底稿為 {ba!r}，突變為 {ea!r}"
    return None


def validate_evolved_program_structure(program_path: str) -> Tuple[bool, str]:
    """
    回傳 (True, "") 表示通過；(False, 說明) 表示應拒絕此次個體。
    """
    if os.environ.get("OPENEVOLVE_SKIP_STRUCTURE_GUARD", "").lower() in (
        "1",
        "true",
        "yes",
    ):
        return True, ""

    p = Path(program_path)
    if not p.is_file():
        return False, f"找不到程式檔: {program_path}"

    try:
        data = yaml.safe_load(sanitize_agents_yaml_text(p.read_text(encoding="utf-8")))
    except yaml.YAMLError as e:
        return False, f"YAML 解析失敗: {e}"

    if not isinstance(data, dict):
        return False, "根節點必須為 mapping"

    base_agents = _load_mapping(_AGENTS_BASE)
    base_tasks = _load_mapping(_TASKS_BASE)

    # --- bundle: agents + tasks ---
    if isinstance(data.get("agents"), dict) and isinstance(data.get("tasks"), dict):
        ea, et = data["agents"], data["tasks"]
        if err := _exact_key_sets(ea, base_agents, "agents"):
            return False, err
        if err := _exact_key_sets(et, base_tasks, "tasks"):
            return False, err
        if err := _nested_keys_exact(ea, base_agents, "agents"):
            return False, err
        if err := _nested_keys_exact(et, base_tasks, "tasks"):
            return False, err
        if err := _tasks_agent_unchanged(et, base_tasks):
            return False, err
        return True, ""

    # --- tasks-only（扁平 task map）---
    keys: Set[str] = set(data.keys())
    if _TASK_ROOT_KEYS & keys:
        if err := _exact_key_sets(data, base_tasks, "tasks"):
            return False, err
        if err := _nested_keys_exact(data, base_tasks, "tasks"):
            return False, err
        if err := _tasks_agent_unchanged(data, base_tasks):
            return False, err
        return True, ""

    # --- agents-only（扁平 agent map）---
    if err := _exact_key_sets(data, base_agents, "agents"):
        return False, err
    if err := _nested_keys_exact(data, base_agents, "agents"):
        return False, err
    return True, ""
