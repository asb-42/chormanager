# AGENTS.md — frontend/

## Purpose
**Web frontend** (React + TypeScript, M2+): Browser-Client zur
M1-API. Desktop-first (Notebook mit Maus/Trackpad, Analyse §5.1);
kein Mobile-First.

## Ownership
Das Frontend gehört der Web-Migration (Branch ``web-migration``).
API-Verträge stehen in
``docs/plans/2026-09-26_m0_erd-openapi.md`` §3; Abweichungen dort
nachziehen.

## Local Contracts

* **Stack.** Vite + React 18 + TypeScript 5 + Tailwind +
  TanStack Query + React Router. dnd-kit erst mit dem Formation
  Editor (M3).
* **API-Zugriff nur via ``src/api/``.** Komponenten fetchen nie
  direkt; TanStack Query mit ``['<resource>', ...]``-Keys,
  Suche serverseitig (``?search=``).
* **Tests colocated.** ``src/**/__tests__/*.test.tsx`` (Vitest +
  Testing Library, jsdom). ``fetch`` per Test stubben
  (``vi.stubGlobal``), QueryClient pro Test clearen, Testing
  Library-``cleanup`` nach jedem Test (kein ``globals: true``).
  ``userEvent.type`` braucht ``{ delay: 10 }`` (jsdom
  kollabiert sonst Anschläge); kein 2. fetch-Argument
  erwarten (``expect.anything()`` matcht ``undefined`` nicht).
* **UI nur via Primitives.** Buttons/Inputs/Labels/Header/
  Empty-/Error-/Loading-States kommen aus
  ``src/components/ui.tsx`` (Varianten primary/secondary/danger/
  success/ghost, Größen md/sm). Keine Ad-hoc-Klassen in
  Pages/Dialogen; Tokens (Farben, Radius, Fokus) in
  ``src/index.css`` dokumentiert.
* **Keine Platzhalter-Routen.** Nur Routen anlegen, die eine
  echte Seite haben (M2 baut tabweise aus).

## Work Guidance

* Neue Seite = Route + Page-Komponente + Spec nach obigem Muster.
* Hell/Dunkel via ``prefers-color-scheme`` + Tailwind
  ``dark:``-Klassen (volles Theming in M2 ausbauen).

## Verification

```bash
npm test --prefix frontend      # Vitest
npm run build --prefix frontend # tsc + vite build
```

## Child DOX Index

* ``src/api/`` — API-Client + QueryClient (folgt diesem Doc).
* ``src/pages/`` — Routen-Seiten + colocated Specs.
