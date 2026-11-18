# Multi-street batch solver — first implementation increment

This module runs a **single Rust DCFR game spanning flop, turn and river** for
each sampled flop. The existing `pfdriver` and the pinned external
`b-inary/postflop-solver` are reused. It does **not** splice a coarse flop
strategy onto separately solved turns/rivers.

## GitHub Actions

Go to **Actions → Postflop multi-street batch → Run workflow** on this branch.
Choose a supported spot, a 0-based starting flop index, count and preset.

- `smoke`: 33% pot only. Small tree / CI and end-to-end integration.
- `medium`: 33%, 75%. Compare to historical abstraction.
- `full`: 33%, 50%, 75%, 100%, 150%, all-in, plus raises `3x,a`.
  This is a **requested experimental abstraction**, not a promise that a
  hosted runner with 5 GB can fit the resulting full tree.
- Set `memory_gb` below the GitHub-hosted runner's usable memory. The driver
  aborts with exit 42 **before strategy allocation** if its estimated
  requirement exceeds this budget.
- A job reaching the iteration limit with exploitability above its target is
  **NOT_CONVERGED**. The workflow fails and archives the diagnostic logs.

Run locally, from repo root:

```bash
git clone https://github.com/b-inary/postflop-solver.git postflop/postflop-solver
git -C postflop/postflop-solver checkout 9d1509fe5077d019825f833eed04b16d342dfda1
cargo build --release --manifest-path postflop/pfdriver/Cargo.toml
python3 -m pip install numpy
python3 -m unittest discover -s postflop/check -p 'test_multistreet*.py' -v
python3 postflop/py/multistreet_batch.py --spot BTN_BB --start 0 --count 1 \
    --preset smoke --max-memory-gb 5 --iters 300
```

Outputs: per-flop `.json`, `.job.json`, `.log`, and per-batch manifest.
`strategy_report.py` exports `.csv` plus reachability/solver `.audit.json`.
The categories are two-pair+, top pair good/weak, middle/low pair,
strong/weak draw and air. A made hand takes precedence over a draw.
For decision thresholds the CSV exports **empirical action frequencies by
reached class**, not a fictional sharp equity cutoff. Each physical flop can
have multiple overlapping board labels (high card, paired, monotone).

The existing output already supplies `node.w` (per-hand reach),
`node.strat` (action-major per-combo strategy), action labels, per-combo EV
and equity. We only aggregate weights **strictly above the reach threshold**.
The audit flags any hand that has zero parental reach but positive child
reach on the same board. Impossible hole-card/board combinations are omitted.

## Important remaining gaps (not solved by this PR)

1. Six-size fully branched games frequently exceed hosted-runner memory;
   rigorous decomposition / safe continuation-value boundary stitching is
   still required. This PR rejects OOM-size trees, **never silently narrows**.
2. The current export samples runouts for the **check-check flop line** and
   check-check turn line. The full underlying game includes other branches,
   but to export *every* node and turn/river branch requires a streaming
   extractor / exhaustive or weighted traversal.
3. The report has rough draw/pair buckets; it is not a complete hand
   abstraction for multiway pots and its aggregated action probabilities
   are not interchangeable with full combo strategies.
4. No production-sized full-preset convergence results have been obtained.
   `gto_expl_pct` is the backend's normalized best-response/exploitability
   diagnostic; do not assert a six-player NashConv for this HU subgame.
5. Raise labels in the existing driver all appear as `r`. Multiple distinct
   raise sizes would require a label/lock/export compatibility migration.
   The first increment therefore retains one non-all-in raise size (3x)
   plus all-in, not the complete multi-size raise menu.
6. No changes to existing web deployment, preflop outputs, or pool data.

## Acceptance criteria for the next increments

- Full node extraction, including all conditional chance-card runouts,
  with action-specific reaches propagated and audited.
- Separate raise sizes with stable unique labels.
- Bounded-memory multi-street subgames with explicitly validated boundary
  values, including turn/river strategy and EV continuity checks.
- Exhaustive toy-game equilibrium checks and representative flop validation.
- Spot extensions and reproducible comparison to the existing 90-flop suite.

AGPL-3.0 external solver is cloned at an exact commit; review licensing
obligations if distributing its linked or modified solver binaries.
