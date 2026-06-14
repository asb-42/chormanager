# AGENTS.md — plans/

## Purpose
**Plan documents** for the major M-1 / M-2 / M-3 / M-4 refactor
waves and the corresponding sub-plans. These are **historical
records** that explain *why* decisions were made and the
trade-offs that were considered.

## Ownership
The plans are owned by the project lead. They are not edited
lightly — only when a refactor scope changes materially.

## Local Contracts

* **One file per scope.** ``plans/2026-06-14_m4_findings.md``
  is the top-level M-4 plan; the ``_phase2_p1.md`` and
  ``_phase3_p2.md`` files detail the P1 and P2 sub-clusters.
  Sub-plans (``_subplan_*.md``) live next to the main plan.
* **Naming.** All plans start with the date they were created
  (``YYYY-MM-DD``) to make the sequence obvious from a directory
  listing.
* **Status index.** The top-level ``_anhang_b_subplans.md``
  contains an "Implementations-Status" table that maps each
  sub-plan to "Geplant | Quick-Win implementiert | Voll
  implementiert". This table is updated after every refactor
  sprint.

## Work Guidance

* When starting a new refactor, do **not** create a new plan
  from scratch; check whether the M-4 plan already covers the
  work and add a sub-task under an existing heading.
* If a new sub-plan is genuinely needed, follow the template
  used in the existing sub-plans: Status / Quelle / Bezug /
  Architektur / Tradeoffs / Subtasks.

## Verification

There is no test suite for plans. Verification is **manual**:
* The top-level M-4 plan covers all 35 findings.
* Each sub-plan has a clear "Akzeptanz" section.
* The status table in ``_anhang_b_subplans.md`` matches the
  reality of the code.

## Child DOX Index

*(All plan files are siblings; no nested folders needed.)*
