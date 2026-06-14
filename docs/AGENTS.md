# AGENTS.md — docs/

## Purpose
**User-facing documentation** (Benutzerhandbuch) plus
**code-review reports**. The Benutzerhandbuch is the primary
end-user document; the review reports are developer-facing
artefacts from the periodic code-review wave.

## Ownership
The Benutzerhandbuch is owned by the project lead. The
code-review reports are owned by the reviewer (currently the
same person as the lead).

## Local Contracts

* **Benutzerhandbuch format.** German, Markdown, with anchor
  IDs (``## Problemlösung``) so it can be exported to a static
  HTML site. The "Inhalt" at the top must list every section.
* **Sprint-2 / Sprint-3 / Sprint-5 / Sprint-6 security note.**
  The "Problemlösung" chapter has a section
  "Update-Check schlägt fehl / TLS / MITM-Proxy" (S-2 / S2-FIX-A)
  that documents the trust assumption of the GitHub version
  check.
* **Code-review reports are immutable.** Once a report is
  committed, the recommendations either land in the M-4 plan
  or are explicitly rejected. Do not retroactively edit a
  report to match what the code became.

## Work Guidance

* When adding a new user-facing feature, update the
  Benutzerhandbuch **in the same commit** as the feature
  implementation.
* The Benutzerhandbuch has a fixed structure: it is read by
  choir directors, not developers. Keep the tone friendly and
  free of jargon.
* Code-review reports (``docs/reports/``): a new report is
  started at the beginning of every M-1 / M-2 / M-3 / M-4
  refactor wave. The report's structure mirrors the
  M-4 plan's "Findings" section.

## Verification

There is no automated test for docs. Verification is
**review-based**:
* Every new feature has a corresponding Benutzerhandbuch
  update in the same commit.
* Every refactor wave produces a new
  ``docs/reports/YYYY-MM-DD_code-review.md``.

## Child DOX Index

*(The two sub-folders are simple grouping utilities; no
per-sub-folder AGENTS.md is needed.)*
