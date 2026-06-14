# AGENTS.md — chormanager/backup/

## Purpose
The **backup service**: creates ZIP backups of the ChorManager
data directory and validates them before a restore.

## Ownership
Owned by the project; no third-party ownership. The service is
used by the MainWindow's ``_reload_after_restore`` slot, which is
itself called from the ``_backup_restore`` dialog.

## Local Contracts

* **m9 transactional backups.** ``BackupService.create_backup``
  routes ``.db`` / ``.sqlite`` / ``.sqlite3`` sources through
  ``sqlite3.Connection.backup`` (transactionally consistent). For
  non-SQLite files, falls back to ``shutil.copy2``. Failures in
  the SQLite path fall back to ``shutil.copy2`` with a logged
  warning.
* **mtime sort.** ``BackupService.list_backups`` returns
  newest-first by mtime. Sort by filename string is forbidden.
* **No automatic restore.** A successful ``create_backup``
  returns the path; ``restore_backup`` is a separate explicit
  call. No implicit calls.

## Work Guidance

* The backup file list (``BACKUP_FILES``) is a class attribute
  of ``BackupService``. Adding a new persistent file means
  appending it there AND adding a round-trip test in
  ``tests/unit/test_backup.py``.
* ``chormanager/export/backup_service.py`` is the **legacy**
  pre-m9 implementation. New code goes here, in
  ``chormanager/backup/service.py``. The legacy file should
  re-export for backward compat.

## Verification

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest \
    tests/unit/test_backup.py \
    tests/unit/test_backup_service_consistent_snapshot.py \
    tests/unit/test_backup_list_mtime_sort.py \
    -q
```

## Child DOX Index

*(This folder is a leaf in the DOX tree. No children.)*
