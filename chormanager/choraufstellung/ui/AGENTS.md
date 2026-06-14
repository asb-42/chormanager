# AGENTS.md — chormanager/choraufstellung/ui/

## Purpose
Qt widgets for the **embedded** ChorAufstellung mode (planned
embedding inside ChorManager).

## Ownership
Currently this folder is **mostly empty** (a few stub files
re-exporting from `chormanager/choraufstellung/widgets/` for
backward compat). The intent (see C-1 sub-plan) is to move the
real Qt widgets here from `widgets/`.

## Local Contracts

* **Backward-compat re-exports.** Anything imported via
  ``from chormanager.choraufstellung.ui import X`` must still
  work; the old ``widgets/`` path is a fallback.
* **No logic duplication.** Widgets in ``ui/`` re-export
  ``widgets/`` classes; do not fork the implementation.

## Work Guidance

* When migrating a widget from ``widgets/`` to ``ui/``,
  re-export from the old location for one release and update
  the new test file alongside.
* The end goal (C-1) is that ``ChorAufstellung`` runs as a tab
  inside ``ChorManager``. Until then, the widgets live in
  ``widgets/`` and ``ui/`` is a thin re-export shim.

## Verification

The widgets are exercised by the main test suite. There are no
unit tests specific to this folder yet.

## Child DOX Index

*(This folder is a leaf in the DOX tree. No children.)*
