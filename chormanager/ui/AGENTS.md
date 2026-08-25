# AGENTS.md — chormanager/ui/

## Purpose
The **Qt MainWindow and controllers** of ChorManager proper (NOT
ChorAufstellung — see ``chormanager/choraufstellung/AGENTS.md``
for that sub-app).

## Ownership
This folder owns the top-level Qt shell: the ``MainWindow``
class, the menu bar, the toolbar, the context toolbar, the
``TabSignals`` bus, the ``UpdateController``, the
``SubprocessRunner``, the ``ExportController`` (skeleton, A-1),
and the dialog / view sub-folders.

## Local Contracts

* **Composition pattern for new controllers.** New code is added
  as a ``QObject`` member on MainWindow, NOT as a mixin. The
  legacy mixins (TabRouterMixin, ExportCoreMixin, ...) remain
  in place; the A-1 sub-plan migrates them incrementally.
  Example: ``task_flow_controller.py:TaskFlowController`` owns the
  Aufgaben-view → TaskWizard → Choraufstellung-launch flow.
* **TabSignals is the signal bus.** Tab-level events flow through
  ``chormanager/ui/tab_signals.py``. Do not add per-tab
  ``pyqtSignal`` to the widgets; emit through TabSignals.
  (Exception: pre-existing per-view signals stay where they are;
  ``TAB_TASKS = 6`` is defined there.)
* **Theme-aware styling.** Never hardcode light-theme hex colors in
  widget stylesheets — they override the window-wide dark stylesheet.
  Use Qt palette roles (``palette(base)``, ``palette(mid)``, …) for
  surfaces/text and ``theme_manager.accent_color("success"/"error")``
  for semantic status colors. Widgets reacting to live theme switches
  re-render on ``changeEvent(StyleChange)``.
* **SubprocessRunner is the async primitive.** Any
  ``subprocess.run`` should go through
  ``chormanager/ui/subprocess_runner.py:SubprocessRunner`` (M-1)
  to keep the UI responsive.
* **ExportController is the future.** New export code should
  target ``ExportController(QObject)`` (skeleton; the migration
  of the 20+ mixin bodies is left for a future sprint).

## Work Guidance

* The ``MainWindow`` class is currently 900+ LOC and is the
  largest in the project. Resist adding more methods to it; use
  the controller composition pattern instead.
* ``update_controller.py`` is now QThread-based (C-3). Do not
  reintroduce ``QApplication.processEvents()``.
* The ChorAufstellung-spawning logic is in
  ``choraufstellung_launcher.py``. Future work (C-1) will move
  it to a direct import rather than a subprocess spawn.

## Verification

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest \
    tests/unit/test_main_window_actions_mixin.py \
    tests/unit/test_choraufstellung_launcher_mixin.py \
    tests/unit/test_choraufstellung_open_paths.py \
    tests/unit/test_update_controller_qthread.py \
    tests/unit/test_tab_signals_composition.py \
    tests/unit/test_export_controller_skeleton.py \
    -q
```

## Child DOX Index

| Child | Owns | Local AGENTS.md |
|---|---|---|
| ``dialogs/`` | Per-domain Qt dialogs (event, singer, repertoire, ...). | [chormanager/ui/dialogs/AGENTS.md](chormanager/ui/dialogs/AGENTS.md) |
| ``views/`` | Per-tab Qt views (events, singers, projects, ...). | [chormanager/ui/views/AGENTS.md](chormanager/ui/views/AGENTS.md) |
| ``forms/`` | Form widgets (singer dialog, ...). | [chormanager/ui/forms/AGENTS.md](chormanager/ui/forms/AGENTS.md) |
