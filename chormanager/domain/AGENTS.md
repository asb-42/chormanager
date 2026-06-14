# AGENTS.md — chormanager/domain/

## Purpose
**Domain models and repositories**: ``Singer``, ``Event``,
``Project``, ``Besetzung``, ``Repertoire``, ``Availability`` and
their repositories. The repositories sit on top of
``chormanager/data/Database`` and are the **only** place that
should issue domain SQL.

## Ownership
The repositories belong to the domain layer; the
``chormanager/data/`` layer provides the connection. The split is
enforced by the `S1-FIX-A` SQL whitelist (in repositories
themselves; see ``chormanager/domain/repository.py:_whitelist_kwargs``).

## Local Contracts

* **SQL safety.** All repository methods use
  ``_whitelist_kwargs`` to filter unknown column names. Any new
  repository **must** apply the whitelist helper before binding
  parameters.
* **No raw ``cursor.execute`` in callers.** Tab code calls
  repository methods (``self.singer_repo.get_all()``) and never
  builds SQL itself.
* **Transactional grouping.** Multi-table writes
  (``set_active``, ``update`` etc.) go through
  ``self.db.transaction()`` (m6). New multi-table methods
  must do the same.
* **m7 INSERT OR IGNORE pattern.** When the caller does not
  know whether the row exists, the repository uses
  ``INSERT OR IGNORE`` followed by an ``UPDATE`` keyed on the
  business key (``(singer_id, event_id)``). The id is preserved
  across calls.

## Work Guidance

* When extending a repository, mirror the pattern in the
  neighbouring repository (singler <-> event <-> project).
  Inconsistencies in the layer are a major source of bugs.
* New repositories should live in this folder; do not create
  repositories in tab / controller code.
* The ``Besetzung`` (lineup) and ``Repertoire`` repositories are
  the least-tested of the bunch; if you touch them, write
  tests first.

## Verification

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest \
    tests/unit/test_repository_cleanup.py \
    tests/unit/test_project.py \
    tests/unit/test_event.py \
    tests/unit/test_sprint1_fixes.py \
    -q
```

## Child DOX Index

*(This folder is a leaf in the DOX tree. No children.)*
