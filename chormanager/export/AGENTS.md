# AGENTS.md — chormanager/export/

## Purpose
**Export modules**: CSV, JSON, sync (for ChorAufstellung). The
new ``ExportController(QObject)`` in ``chormanager/ui/`` is the
composition-pattern wrapper; the bulk of the export logic still
lives here (and in the legacy mixin bodies in
``chormanager/ui/export_controller.py``).

## Ownership
The folder is owned by the project. The CSV / PDF / JSON-Sync
export paths are routed through here.

## Local Contracts

* **Singer CSV / event CSV export.** The schema is fixed:
  ``name, voice_group, height`` for singers;
  ``name, date, event_type`` for events. Test in
  ``tests/unit/test_export_csv.py``.
* **Register-Sum aggregation.** The event-availability CSV
  includes the sum of singers per voice group
  (``Register-Summen: Sopran/Alti/Tenor/Bass``). This is the
  only export path that does aggregation; all others are
  row-level.
* **JSON-Sync for ChorAufstellung.** The export
  ``export_singers_json`` produces the file format the
  ``ChorAufstellung`` sub-app reads. The format is documented
  in ``chormanager/export/sync.py``.

## Work Guidance

* When adding a new export format, add a function here, a test
  in ``tests/unit/test_export_*.py``, and a menu entry in
  ``MainWindow._create_menu_bar`` (the
  ``choraufstellung_export_menu`` block).
* Do not duplicate export logic in the controllers; the
  controllers are thin wrappers.

## Verification

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest \
    tests/unit/test_export.py \
    tests/unit/test_export_core_mixin.py \
    tests/unit/test_export_json_sync_mixin.py \
    tests/unit/test_export_tab_specific_mixin.py \
    -q
```

## Child DOX Index

*(This folder is a leaf in the DOX tree. No children.)*
