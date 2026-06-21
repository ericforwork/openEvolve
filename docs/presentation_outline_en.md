# Presentation Outline — Two-Stage OpenEvolve Evolution

> Full report: `docs/TECHNICAL_REPORT.md`

---

## Slide 1 — Title

- **Title**: OpenEvolve × CrewAI: Two-Stage Yelp Review Simulation Evolution
- **Subtitle**: Basic (3-agent) → Extended (5-agent)
- **Result**: 0.9412 → **0.9999** `combined_score`

---

## Slide 2 — Scoring Objective

- `combined_score = (preference_estimation + review_generation) / 2`
- Star rating MAE + review topic (highest weight)
- Output contract: `{"stars": float, "review": str}`

---

## Slide 3 — Novelty: Two-Stage Strategy (Key Point)

```
Phase 1 (final_basicOnly)     Phase 2 (final_agentTask)
3 agents × 3 tasks      →     5 agents × 5 tasks
Gen-0: 0.910                    Gen-0: 0.958 (inherits P1 Best)
Best:  0.941                    Best:  0.9999
```

- **Simple first, complex later**: avoids evolving an oversized search space in one shot
- Phase 2 Gen-0: three core agents = Phase 1 Best (already validated)

---

## Slide 4 — Phase 1 Crew Diagram

```
user_analyst → analyze_user_task
item_analyst → analyze_item_task
prediction_modeler → simulate_review_task → JSON
```

- Sequential; lookup backstory + search task tools
- No review matching, no web search

---

## Slide 5 — Phase 2 Crew Diagram

```
internet_researcher → internet_research_task
user_analyst → analyze_user_task
item_analyst → analyze_item_task
review_analyst → analyze_reviews_task  ← new
prediction_modeler → simulate_review_task → JSON
```

- `lookup_reviews_by_user_and_item` was the breakthrough at iter 45

---

## Slide 6 — Agent & Tool Reference (One-Page Table)

| Agent | Phase 1 | Phase 2 Additions/Changes |
|-------|---------|---------------------------|
| user_analyst | search_user_profile_data | unchanged |
| item_analyst | search_restaurant_feature_data | unchanged |
| prediction_modeler | no tools | synthesizes 4 prior reports |
| review_analyst | — | lookup_reviews_by_user_and_item |
| internet_researcher | — | search_internet |

---

## Slide 7 — Evolution Analysis: Score Trajectory

**Phase 1**: plateaus at 0.9412 after iter 15  
**Phase 2**: holds at 0.9666 from iter 5–40 → **jumps to 0.9999 at iter 45**

(Include checkpoint line chart or Visualizer Performance tab screenshot)

---

## Slide 8 — Visualizer Findings

- Evolution tree: Phase 2 is deeper (gen=5)
- 3 islands, no zero-score mutations (structure guard is stable)
- Diff viewer: Gen-0 vs Best changes in `analyze_reviews_task` / `simulate_review_task`

```bash
make visualize OUTPUT=config/openevolve_output/final_basicOnly
make visualize OUTPUT=config/openevolve_output/final_agentTask
```

---

## Slide 9 — Ancestry Chain (Evolution Path)

**Phase 1 Best**: gen0(0.91) → gen1(0.94) → gen3(0.941)  
**Phase 2 Best**: gen0(0.96) → … → gen5(0.9999)

- Mid-run score oscillation = exploration phase
- Final offspring integrates effective mutations from earlier generations

---

## Slide 10 — Conclusion & Takeaways

1. **Staged evolution** beats one-shot optimization (3-agent ceiling ≈ 0.94)
2. **Historical review matching** delivers the largest marginal gain in Phase 2
3. **Structure lock + JSON contract** ensured zero failures across 292 individuals
4. Next steps: full 41-task validation, unified lookup-first tool chain

---

## Backup Q&A

- **Why does Phase 1 use search instead of lookup?** To widen the evolution space early on; backstory already guides lookup-style reasoning.
- **Why did the breakthrough happen only at iter 45?** The 5-task pipeline needs more iterations for the review chain and predictor to align.
- **Did internet_research help?** The best program still keeps it, but it converges to 5 bullet general insights.
