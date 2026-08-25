# AGENTS.md — chormanager/domain/taskflow/

## Purpose
**Task flow domain core**: models end-user tasks ("plan a
formation", "record availability") as ordered step chains and
evaluates their prerequisites against the repositories. This powers
the Aufgaben view + TaskWizard in ``chormanager/ui/``.

## Ownership
Owned by the domain layer. Depends only on
``chormanager/domain/repository.py`` and the stdlib — **Qt imports
are forbidden here** (enforced by review; the whole point of the
split is headless testability and future front-end reuse).

## Local Contracts

* **Checks are pure predicates.** A ``TaskStep.check`` receives the
  :class:`~.models.TaskContext` and must not mutate anything.
  Repositories are instantiated inside the predicate from
  ``context.db``.
* **Resolvers mirror checks.** Every auto-detectable prerequisite has
  a public ``resolve_*`` helper (``resolve_project``,
  ``resolve_event``, ``resolve_besetzung``,
  ``resolve_besetzung_for_event``) returning the detected entity. The
  wizard shows these on confirm pages and pins them into the context
  when the user accepts.
* **Selection steps are pinned-only.** Steps whose entire purpose is
  a user decision (``termin_waehlen`` in the availability task) use
  ``check_event_pinned`` and are NEVER auto-detected — auto-detect is
  only for convenience prerequisites the user can confirm/replace on
  the wizard page.
* **Besetzung links singers to projects.** The data model has no
  direct singer↔project relation; ``besetzung.singer_ids`` (JSON,
  no FK) is the only link, and availability ignores besetzung. The
  ``besetzung_pruefen`` step exists to make that implicit chain
  explicit in the wizard (it sets the active-besetzung config key
  that the availability dialog filters by).
* **Context pinning beats auto-detection.** When
  ``context.project/event/besetzung`` is set, checks must evaluate
  against the pinned entity, never re-detect one.
* **"Aktives Projekt" = config key, not the DB flag.**
  ``resolve_project`` reads ``last_active_project_id`` (the same
  source the info bar shows); the legacy ``projects.is_active``
  column is ignored by the checker and must be kept in sync by
  writers (see ``_task_wizard._sync_active_project``). The
  TaskFlowController pre-pins the wizard context from the current
  UI state so wizard and info bar can never diverge.
* **Action steps have no check.** ``check=None`` means the step is
  completed by executing it in the wizard, never by DB state.
* **Stable ids.** Step ids (``projekt_waehlen``, …) are part of the
  UI contract: the wizard's executor map and pin targets key on them.

## Work Guidance

* New tasks go into ``catalog.py`` as a builder function plus an id
  in ``TASK_IDS``; reuse the shared predicates from ``checker.py``
  instead of writing new ones where possible.
* New predicates belong in ``checker.py`` so both catalog and UI can
  reuse them.
* Friendly German titles/subtitles are a hard requirement — this
  package exists because choir directors are non-technical users.

## Verification

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest \
    tests/unit/test_taskflow_models_checker.py \
    tests/unit/test_taskflow_catalog.py -q
```

## Child DOX Index

*(This folder is a leaf in the DOX tree. No children.)*
