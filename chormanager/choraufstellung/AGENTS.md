# AGENTS.md — chormanager/choraufstellung/

## Purpose
The **ChorAufstellung** sub-application: a stand-alone Qt tool for
arranging singers into formation grids. It runs in two modes:
1. **Stand-alone**: invoked via `python -m choraufstellung`.
2. **Embedded** (planned, see C-1 sub-plan): imported by ChorManager
   so the user can edit formations without leaving the main app.

## Ownership
- The sub-application is owned by the ChorManager project; the
  `choraufstellung` package is **not** a separate project.
- Cross-cutting rules (TDD, type hints, error handling) live in
  the root `AGENTS.md` and apply here too.

## Local Contracts

* **Library + Standalone duality.** `chormanager/choraufstellung/main.py`
  exposes a `LibraryMainWindow` for embedding AND a `run_standalone()`
  entry point. `chormanager/choraufstellung/__main__.py` only calls
  `run_standalone()`.
* **Pure-Python core.** All arrangement algorithms live under
  `core/` and must not import `PyQt6` (the `choraufstellung/core/AGENTS.md`
  enforces this).
* **JSON file format.** The on-disk file format is documented in
  `core/file_io.py:save_formation` and is the only way state leaves
  the sub-app.
* **Subshell launch path.** `validate_choraufstellung_path()`
  (M-7) must be called before any subprocess spawn. See
  `chormanager/ui/choraufstellung_launcher.py:validate_choraufstellung_path`.

## Work Guidance

* Before touching `core/`, read the test pyramid target from the
  root `AGENTS.md` (~70 % unit, ~25 % integration, ~5 % UI). The
  sub-app is UI-heavy so the actual ratio is closer to 60/25/15.
* `qt_compat.py` is now PyQt6-only (A-2). Do not reintroduce
  PyQt5 fallbacks.
* `_rehydrate_singers` in `file_io.py` uses duck-typing
  (``name/voice_group/singer_id/row/col``) instead of
  `isinstance(Singer)` because the Singer class can be imported under
  different module paths in the embedded mode. Keep this contract.
* `formation_grid.apply_affinity_proximity` (R-4) must bounds-check
  every swap target before mutating; see R-1/R-2 in the M-4 plan.

## Verification

Run the **full** test suite from the repo root:

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/unit/ -q \
    --ignore=tests/unit/test_choraufstellung_window_resize_bug.py \
    --ignore=tests/unit/test_metadata_saving.py
```

Two tests are known to **deadlock on `main`** and are excluded:
the splitter-resize test and the metadata-save-event-file test.
These are tracked as pre-existing issues and must be fixed in a
future sprint, not as part of regular work.

## Child DOX Index

| Child | Owns | Local AGENTS.md |
|---|---|---|
| ``core/`` | Pure-Python arrangement rules + optimizer (no Qt). | [chormanager/choraufstellung/core/AGENTS.md](chormanager/choraufstellung/core/AGENTS.md) |
| ``ui/`` | Qt widgets (FormationGrid, SingerPool, dialogs). | [chormanager/choraufstellung/ui/AGENTS.md](chormanager/choraufstellung/ui/AGENTS.md) |
| ``widgets/`` | Legacy widgets (drag/drop, context-menu). | [chormanager/choraufstellung/widgets/AGENTS.md](chormanager/choraufstellung/widgets/AGENTS.md) |
