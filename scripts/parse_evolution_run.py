"""Parse OpenEvolve run directories for technical report data."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_programs(run_dir: Path) -> dict[str, dict]:
    programs: dict[str, dict] = {}
    for cp in sorted(run_dir.glob("checkpoints/checkpoint_*")):
        prog_dir = cp / "programs"
        if not prog_dir.exists():
            continue
        for jf in prog_dir.glob("*.json"):
            data = json.loads(jf.read_text(encoding="utf-8"))
            pid = data.get("id", jf.stem)
            programs[pid] = data
    return programs


def trace_ancestry(programs: dict[str, dict], start_id: str) -> list[dict]:
    chain: list[dict] = []
    cur: str | None = start_id
    seen: set[str] = set()
    while cur and cur not in seen:
        seen.add(cur)
        if cur not in programs:
            break
        p = programs[cur]
        score = p.get("metrics", {}).get("combined_score")
        chain.append(
            {
                "id": cur,
                "generation": p.get("generation"),
                "iteration": p.get("iteration"),
                "combined_score": score,
                "parent_id": p.get("parent_id"),
            }
        )
        cur = p.get("parent_id")
    return chain


def checkpoint_trajectory(run_dir: Path) -> list[dict]:
    rows: list[dict] = []
    for cp in sorted(
        run_dir.glob("checkpoints/checkpoint_*"),
        key=lambda p: int(p.name.split("_")[1]),
    ):
        bi_path = cp / "best_program_info.json"
        if not bi_path.exists():
            continue
        bi = json.loads(bi_path.read_text(encoding="utf-8"))
        rows.append(
            {
                "checkpoint": cp.name,
                "iteration": bi.get("current_iteration") or bi.get("iteration"),
                "best_id": bi.get("id"),
                "generation": bi.get("generation"),
                "combined_score": bi.get("metrics", {}).get("combined_score"),
            }
        )
    return rows


def analyze_run(run_dir: Path) -> dict:
    programs = load_programs(run_dir)
    best_info = json.loads(
        (run_dir / "best" / "best_program_info.json").read_text(encoding="utf-8")
    )
    gen0 = [p for p in programs.values() if p.get("generation") == 0]
    gen0_sorted = sorted(gen0, key=lambda p: p.get("iteration", 0))
    return {
        "run_name": run_dir.name,
        "num_programs": len(programs),
        "gen0": gen0_sorted[0] if gen0_sorted else None,
        "best_info": best_info,
        "ancestry": trace_ancestry(programs, best_info["id"]),
        "checkpoint_trajectory": checkpoint_trajectory(run_dir),
    }


def main() -> int:
    runs = sys.argv[1:] or [
        "config/openevolve_output/final_basicOnly",
        "config/openevolve_output/final_agentTask",
    ]
    for rel in runs:
        run_dir = REPO_ROOT / rel
        if not run_dir.is_dir():
            print(f"SKIP (not found): {rel}")
            continue
        r = analyze_run(run_dir)
        print(f"\n{'='*60}")
        print(f"Run: {r['run_name']}")
        print(f"Programs in checkpoints: {r['num_programs']}")
        if r["gen0"]:
            g = r["gen0"]
            print(
                f"Gen-0: iter={g.get('iteration')} "
                f"score={g.get('metrics', {}).get('combined_score')}"
            )
        b = r["best_info"]
        print(
            f"Best: gen={b['generation']} iter={b['iteration']} "
            f"score={b['metrics']['combined_score']:.6f}"
        )
        print("\nCheckpoint trajectory:")
        for row in r["checkpoint_trajectory"]:
            sc = row["combined_score"] or 0.0
            print(
                f"  {row['checkpoint']:16s} iter={row['iteration']:3} "
                f"score={sc:.4f}"
            )
        print("\nAncestry (best → ancestors):")
        for node in r["ancestry"]:
            sc = node["combined_score"] or 0.0
            pid = node["parent_id"] or "—"
            print(
                f"  gen={node['generation']} iter={node['iteration']} "
                f"score={sc:.4f} "
                f"id={node['id'][:8]} parent={pid[:8] if pid != '—' else '—'}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
