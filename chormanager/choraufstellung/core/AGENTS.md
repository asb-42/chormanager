# AGENTS.md — chormanager/choraufstellung/core/

## Purpose
**Pure-Python arrangement algorithms**: the rules and the optimizer
that decide where each singer goes on the formation grid.

## Ownership
This is the **highest-purity** code in the project. It must remain
importable and testable without any Qt dependency so that the
test suite can run on bare CPython (no display server).

## Local Contracts

* **Zero Qt imports.** Adding `import PyQt6` or `from PyQt5 ...`
  here is forbidden. The only Python packages allowed are
  `enum`, `dataclasses`, `typing`, `itertools`, `functools`, and the
  standard library. If you need a Qt type, use a Python-level
  stand-in (e.g. ``Tuple[int, int]`` for a position).
* **Pure data classes.** `SingerRef`, `ArrangementResult`, `GridConfig`
  are frozen / read-only as much as possible.
* **Determinism.** Optimizer runs are deterministic for a given input.
  No hidden global state, no clock, no RNG.
* **Bounds-checks at the entry point.** Every public ``apply()``
  method must validate its inputs (rows > 0, cols > 0, no
  duplicate singer_ids, ...) and raise ``ValueError`` on bad
  input. The bounds-check uses the grid engine
  (``GridEngine.is_valid_position``) when available; otherwise it
  falls back to a static ``0 <= r < rows, 0 <= c < cols`` test
  (see R-1).

## Work Guidance

* The core has its own **adjacent test directory**
  (``tests/unit/test_grid_engine.py``,
  ``tests/unit/test_affinity.py``,
  ``tests/unit/test_affinity_properties.py``,
  ``tests/unit/test_sprint1_fixes.py``). All new code must have a
  matching test.
* When in doubt about a rule, look at
  ``plans/2026-06-14_subplan_optimizer_perf.md`` for the
  C-4 performance contract.

## Verification

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest \
    tests/unit/test_grid_engine.py \
    tests/unit/test_affinity.py \
    tests/unit/test_affinity_properties.py \
    tests/unit/test_sprint1_fixes.py \
    tests/unit/test_c4_build_pairs_dict_index.py \
    -q
```

These tests are **fast** (no Qt, no I/O) and must complete in < 2 s.

## Child DOX Index

*(This folder is a leaf in the DOX tree. No children.)*
