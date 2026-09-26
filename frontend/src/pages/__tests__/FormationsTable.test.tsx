// Sweep 5/6 Aufstellung: Qt-Spalten, Suche, 6 Sortierungen,
// Duplizieren, Löschen.
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { queryClient } from '../../api/client'
import { ActiveProvider } from '../../active/active'
import FormationsPage from '../FormationsPage'

let formations = [
  {
    id: 'f-1', name: 'choraufstellung-b.json', rows: 4, cols: 5, event_id: 'e-1',
    updated_at: '2026-09-02T10:00:00',
    metadata: { project: 'P', event: 'Konzert', event_date: '2026-10-01', event_type: 'Konzert' },
    size: 2048,
  },
  {
    id: 'f-2', name: 'choraufstellung-a.json', rows: 2, cols: 3, event_id: 'e-1',
    updated_at: '2026-09-01T10:00:00',
    metadata: { project: 'P', event: 'Probe', event_date: '2026-09-01', event_type: 'Probe' },
    size: 512,
  },
]

const DETAIL = {
  id: 'f-1', name: 'choraufstellung-b.json', rows: 4, cols: 5, staggered: false,
  voicing_config: [], singers: [], placed: [], metadata: {}, event_id: 'e-1',
}

function stubFetch() {
  const calls: Array<{ method: string; url: string; body?: unknown }> = []
  const mock = vi.fn(async (url: string, init?: RequestInit) => {
    const method = init?.method ?? 'GET'
    const u = String(url)
    let body: unknown
    try {
      body = init?.body ? JSON.parse(String(init.body)) : undefined
    } catch {
      body = undefined
    }
    calls.push({ method, url: u, body })
    if (u.endsWith('/api/formations') && method === 'POST') {
      const created = { id: 'f-9', updated_at: '2026-09-03', metadata: {}, size: 0, ...(body as object) }
      formations.push(created as (typeof formations)[number])
      return { ok: true, status: 201, json: async () => created }
    }
    if (u.match(/\/api\/formations\/[^/]+$/) && method === 'DELETE') {
      const id = u.split('/').pop() as string
      formations = formations.filter((f) => f.id !== id)
      return { ok: true, status: 204, json: async () => ({}) }
    }
    if (u.match(/\/api\/formations\/[^/]+$/) && method === 'GET') {
      return { ok: true, json: async () => DETAIL }
    }
    if (u.includes('/placements') && method === 'PUT') {
      return { ok: true, json: async () => DETAIL }
    }
    if (u.endsWith('/api/formations')) {
      return { ok: true, json: async () => formations }
    }
    return { ok: true, json: async () => [] }
  })
  vi.stubGlobal('fetch', mock)
  return { mock, calls }
}

function renderPage() {
  queryClient.clear()
  window.localStorage.clear()
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/formations']}>
        <ActiveProvider>
          <Routes>
            <Route path="/formations" element={<FormationsPage />} />
          </Routes>
        </ActiveProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('FormationsPage Qt-Tabelle', () => {
  beforeEach(() => {
    vi.unstubAllGlobals()
    window.localStorage.clear()
    formations = [
      {
        id: 'f-1', name: 'choraufstellung-b.json', rows: 4, cols: 5, event_id: 'e-1',
        updated_at: '2026-09-02T10:00:00',
        metadata: { project: 'P', event: 'Konzert', event_date: '2026-10-01', event_type: 'Konzert' },
        size: 2048,
      },
      {
        id: 'f-2', name: 'choraufstellung-a.json', rows: 2, cols: 3, event_id: 'e-1',
        updated_at: '2026-09-01T10:00:00',
        metadata: { project: 'P', event: 'Probe', event_date: '2026-09-01', event_type: 'Probe' },
        size: 512,
      },
    ]
  })

  afterEach(() => {
    cleanup()
  })

  it('renders Qt columns', async () => {
    stubFetch()
    renderPage()
    expect(await screen.findByText('choraufstellung-b.json')).toBeInTheDocument()
    for (const header of ['Dateiname', 'Dateigröße', 'Projekt', 'Termin', 'Typ', 'Gespeichert']) {
      expect(screen.getByText(header, { selector: 'th' })).toBeInTheDocument()
    }
    expect(screen.getByText('2 KB')).toBeInTheDocument()
    expect(screen.getByText('Konzert')).toBeInTheDocument()
  })

  it('searches and sorts like Qt', async () => {
    const user = userEvent.setup({ delay: 10 })
    stubFetch()
    renderPage()
    await screen.findByText('choraufstellung-b.json')
    await user.type(screen.getByPlaceholderText('Suchen …'), 'konzert')
    await waitFor(() => {
      expect(screen.queryByText('choraufstellung-a.json')).not.toBeInTheDocument()
    })
    await user.clear(screen.getByPlaceholderText('Suchen …'))
    await user.selectOptions(screen.getByLabelText('Sortieren'), 'filename-desc')
    const rows = await screen.findAllByRole('row')
    expect(rows[1]).toHaveTextContent('choraufstellung-b.json')
  })

  it('duplicates incl. placements and deletes after confirm', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage()
    await screen.findByText('choraufstellung-b.json')
    const row = screen.getByText('choraufstellung-b.json').closest('tr') as HTMLElement
    await user.click(within(row).getByRole('button', { name: 'Duplizieren' }))
    await waitFor(() => {
      expect(
        calls.some(
          (c) =>
            c.method === 'POST' &&
            c.url.endsWith('/api/formations') &&
            (c.body as { name: string }).name === 'choraufstellung-b.json (Kopie)',
        ),
      ).toBe(true)
    })
    expect(
      calls.some((c) => c.method === 'PUT' && c.url.includes('/placements')),
    ).toBe(true)
    const row2 = screen.getByText('choraufstellung-a.json').closest('tr') as HTMLElement
    await user.click(within(row2).getByRole('button', { name: 'Löschen' }))
    await user.click(within(row2).getByRole('button', { name: 'Wirklich löschen' }))
    await waitFor(() => {
      expect(
        calls.some((c) => c.method === 'DELETE' && c.url.endsWith('/api/formations/f-2')),
      ).toBe(true)
    })
  })
})
