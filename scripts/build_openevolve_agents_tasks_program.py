"""
Build config/openevolve_agents_tasks.yaml from:
  - config/agents_evolving.yaml (flat agent map)
  - config/tasks_simulator.yaml (flat task map)

Run from repo root:
  uv run python scripts/build_openevolve_agents_tasks_program.py
"""
from __future__ import annotations

from pathlib import Path

import yaml

from src.utils.yaml_sanitize import sanitize_agents_yaml_text

REPO = Path(__file__).resolve().parent.parent
AGENTS_SRC = REPO / "config" / "agents_evolving.yaml"
TASKS_SRC = REPO / "config" / "tasks_simulator.yaml"
OUT = REPO / "config" / "openevolve_agents_tasks.yaml"


def main() -> None:
    agents = yaml.safe_load(
        sanitize_agents_yaml_text(AGENTS_SRC.read_text(encoding="utf-8"))
    )
    tasks = yaml.safe_load(
        sanitize_agents_yaml_text(TASKS_SRC.read_text(encoding="utf-8"))
    )
    if not isinstance(agents, dict) or not isinstance(tasks, dict):
        raise SystemExit("agents_evolving / tasks_simulator must parse to YAML mappings")

    body = yaml.dump(
        {"agents": agents, "tasks": tasks},
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=120,
    )
    header = (
        "# OpenEvolve 聯合進化：agents + tasks（檔內僅此一段 EVOLVE-BLOCK）。\n"
        "# 重新產生：uv run python scripts/build_openevolve_agents_tasks_program.py\n\n"
        "# EVOLVE-BLOCK-START\n"
    )
    footer = "\n# EVOLVE-BLOCK-END\n"
    OUT.write_text(header + body + footer, encoding="utf-8")
    print(f"Wrote {OUT.relative_to(REPO)} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
