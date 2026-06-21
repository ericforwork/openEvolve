# Technical Report (Short): Two-Stage OpenEvolve × CrewAI Review Simulation Evolution

## 1. Summary

This report is organized in two parts: **Novelty first**, then **Evolution Analysis**. We evolve a joint **agents + tasks YAML** for a CrewAI pipeline via OpenEvolve full-rewrite, using a **two-stage staged evolution** strategy—learn how to write prompts on a small crew first, then extend the pipeline for the final score push.

### Results at a glance

| Phase | Run | Crew scale | Gen-0 | Best | Gain |
|-------|-----|------------|-------|------|------|
| Phase 1 — Basic | `final_basicOnly` | 3 agents × 3 tasks | 0.9100 | **0.9412** | +0.031 |
| Phase 2 — Extended | `final_agentTask` | 5 agents × 5 tasks | 0.9579 | **0.9999** | +0.042 |

Scoring target: `combined_score = (rating prediction accuracy + review quality) / 2`; within review quality, **topic weight = 50%**.

---

### A. Novelty — What & How we leverage OpenEvolve

**What (optimization target)**  
We do not evolve Python code. We evolve the **prompt contract of the entire Sequential Crew**: each agent’s `role / goal / backstory` and each task’s `description / expected_output`. Tool names and pipeline topology are fixed in `simulation_crew.py`; under a structure guard, OpenEvolve focuses on *how to query data, pass intermediate fields, and emit final JSON*.

**How (creative OpenEvolve usage)**

1. **Two-stage handoff evolution**  
   - Phase 1: 3 agents only (user → item → predict), small search space, fast convergence.  
   - Phase 2: Phase 1 `best_program.yaml` as Gen-0; we **manually extend** with `review_analyst`, `internet_researcher`, and their tasks, then run a second evolution.  
   - Humans design topology; OpenEvolve optimizes wording—balancing control and exploration.

2. **Joint agents + tasks bundle**  
   A single `EVOLVE-BLOCK` mutates agents and tasks together so instructions and personas co-adapt to `combined_score`.

3. **Pipeline aligned with the metric**  
   - Early tasks: user/item features (star MAE).  
   - Mid task: `lookup_reviews_by_user_and_item` for direct match (stars + topic).  
   - Final task: tool-less `prediction_modeler` consuming structured context → `{"stars","review"}`.

**Crew collaboration pattern**

```
Phase 1 (Sequential):
  analyze_user_task → analyze_item_task → simulate_review_task → JSON

Phase 2 (Sequential, extended):
  internet_research_task → analyze_user_task → analyze_item_task
    → analyze_reviews_task → simulate_review_task → JSON
```

| Agent | Role (summary) | Tool use (task layer) |
|-------|----------------|----------------------|
| `user_analyst` | User behavior analysis | `search_user_profile_data`, `search_historical_reviews_data` |
| `item_analyst` | Business feature analysis | `search_restaurant_feature_data`, `search_historical_reviews_data` |
| `review_analyst` *(P2)* | Historical review matching | `lookup_reviews_by_user_and_item` |
| `internet_researcher` *(P2)* | General rating trends | `search_internet` (no fabricated user/item data) |
| `prediction_modeler` | Stars + review generation | **No tools** (synthesizes prior reports) |

Full Role / Goal / Backstory / `expected_output` details are in §2.

---

### B. Evolution Analysis — Paths and strategies OpenEvolve discovered

**Methods**  
- Parse `checkpoints/checkpoint_*/programs/*.json` and `parent_id` ancestry from `best_program_info.json`.  
- Use the **Visualizer** (`make visualize OUTPUT=...`) to compare **Gen-0 vs Best** prompt diffs and the evolution tree.  
- Tooling: `scripts/parse_evolution_run.py` → `docs/assets/evolution/evolution_summary.json`.

**Phase 1 path (`final_basicOnly`)**

| Checkpoint | Best score | Reading |
|------------|-----------|---------|
| iter 5 | 0.9335 | Early rapid gain |
| iter 15 | **0.9412** | Plateau reached |
| iter 20–50 | 0.9412 | No gain for 35 iters → triggers Phase 2 |

Ancestry: `gen0(0.91) → gen1(0.94) → gen2(0.92) → gen3(0.9412) Best`  
→ After a brief regression at gen=2, gen=3 integrates mutations—illustrating MAP-Elites diversity value.

**Strategies discovered in Phase 1**: keep tool names fixed; refine `prediction_modeler` data-scientist narrative, strengthen missing-data defaults (3.8 stars), and tighten JSON contract—**prompt semantics > tool swapping**.

**Phase 2 path (`final_agentTask`)**

| Checkpoint | Best score | Reading |
|------------|-----------|---------|
| Gen-0 | 0.9579 | Inherits Phase 1 Best + new agents/tasks |
| iter 5–40 | 0.9666 | Plateau: review chain not yet aligned |
| iter 45 | **0.9999** | Breakthrough |
| iter 50 | 0.9999 | Converged |

Ancestry: `gen0(0.96) → gen1~4(0.94~0.95 oscillation) → gen5(0.9999) Best`  
→ Mid-run score oscillation, then gen=5 **integrates** prior effective mutations.

**Strategies discovered in Phase 2** (verifiable via Visualizer / diff):

1. **Direct review shortcut**: strengthen `analyze_reviews_task` to extract matched stars / snippets for `prediction_modeler`.  
2. **Multi-source synthesis**: `simulate_review_task` explicitly consumes four prior reports; forbids mentioning missing data.  
3. **Context discipline**: keep `internet_research_task` but cap at ≤5 general bullets to avoid diluting key fields.  
4. **Zero structural failures**: 292 individuals per run, **0× combined_score=0**—structure guard keeps YAML valid.

**Gen-0 vs Best files** (for Visualizer / slides):

| Phase | Gen-0 | Best |
|-------|-------|------|
| Phase 1 | `docs/assets/evolution/final_basicOnly_gen0.yaml` | `config/openevolve_output/final_basicOnly/best/best_program.yaml` |
| Phase 2 | `docs/assets/evolution/final_agentTask_gen0.yaml` | `config/openevolve_output/final_agentTask/best/best_program.yaml` |

---

### One-line conclusion

We use a **human-designed pipeline + machine-optimized prompts** two-stage OpenEvolve strategy to push Yelp review simulation from 0.91 to **0.9999**; Phase 1 learns star heuristics, Phase 2 achieves the final leap at iter 45 via historical review matching. See §2 for design details, §3 for checkpoints and ancestry.

---

## 2. Novel Design

**Collaboration pattern**: CrewAI Sequential; `simulate_review_task` must be last and output `{"stars", "review"}` JSON.

### Phase 1: 3 Agents × 3 Tasks

```
user_analyst → analyze_user_task
item_analyst → analyze_item_task
prediction_modeler → simulate_review_task → JSON
```

| Agent | Tools (task layer) | Strategy focus |
|-------|-------------------|----------------|
| `user_analyst` | `search_user_profile_data`, `search_historical_reviews_data` | Default to 3.8 stars when data is missing |
| `item_analyst` | `search_restaurant_feature_data`, `search_historical_reviews_data` | Business features and public sentiment |
| `prediction_modeler` | No tools | `(user_avg + item_stars)/2 ± 0.5~1.0` |

Evolution gains came mainly from **prompt refinement** (not tool changes). Score plateaued at 0.9412 after iteration 15.

### Phase 2: 5 Agents × 5 Tasks (extended from Phase 1 Best)

```
internet_research_task → analyze_user_task → analyze_item_task
  → analyze_reviews_task → simulate_review_task → JSON
```

**Additions**:
- `internet_researcher` + `internet_research_task` (`search_internet`, general trends only)
- `review_analyst` + `analyze_reviews_task` (`lookup_reviews_by_user_and_item`, direct match)

---

## 3. Evolution Analysis

**Setup**: 50 iterations, `gpt-4.1-mini`, population 50 / 3 islands, full rewrite, seed 42.

### Score trajectory

| Phase | Key turning point | Interpretation |
|-------|-------------------|----------------|
| Phase 1 | iter 15 → 0.9412, then flat | 3-agent ceiling ≈ 0.94 |
| Phase 2 | iter 5~40 → 0.9666; **iter 45 → 0.9999** | Needs enough iterations to integrate the review chain |

### Ancestry chain

```
Phase 1: gen0(0.91) → gen1(0.94) → gen3(0.9412) Best
Phase 2: gen0(0.96) → gen1~4(0.94~0.95 oscillation) → gen5(0.9999) Best
```

Recommended screenshots: evolution tree, performance curve, Gen-0 vs Best diff.

---

## 4. Design ↔ Scoring Alignment

| Design choice | Impact |
|---------------|--------|
| Star-rating calculation heuristic | Rating prediction accuracy (main Phase 1 contribution) |
| `lookup_reviews_by_user_and_item` | Rating + topic (Phase 2 breakthrough at iter 45) |
| Review mentions strengths/weaknesses | Topic (highest weight) |

---
