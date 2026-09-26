// Sweep 4/6 Termine: Sortierung (Qt-Optionen), CRUD-Dialoge,
// Duplizieren (Kopie), Icon-Aktionen, Hinzufügen.
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { queryClient } from '../../api/client'
import { ActiveProvider } from '../../active/active'
import EventsPage from '../EventsPage'

let events = [
  { id: 'e-1', name: 'Probe A', date: '2026-09-01', event_type: 'Probe', project_id: 'p-1', yes_count: 1, conditional_count: 0 },
  { id: 'e-2', name: 'Konzert', date: '2026-10-01', event_type: 'Konzert', project_id: 'p-1', yes_count: 0, conditional_count: 0 },
]
const PROJECTS = [{ id: 'p-1', name: 'Hoffmann' }]

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
    if (u.includes('/api/projects')) return { ok: true, json: async () => PROJECTS }
    if (u.includes('/api/events') && method === 'POST') {
      const created = { id: 'e-9', yes_count: 0, conditional_count: 0, ...(body as object) }
      events.push(created as (typeof events)[number])
      return { ok: true, status: 201, json: async () => created }
    }
    if (u.match(/\/api\/events\/[^/]+$/) && method === 'PUT') {
      const id = u.split('/').pop() as string
      events = events.map((e) => (e.id === id ? { ...e, ...(body as object) } : e))
      return { ok: true, json: async () => events.find((e) => e.id === id) }
    }
    if (u.match(/\/api\/events\/[^/]+$/) && method === 'DELETE') {
      const id = u.split('/').pop() as string
      events = events.filter((e) => e.id !== id)
      return { ok: true, status: 204, json: async () => ({}) }
    }
    if (u.includes('/api/events')) return { ok: true, json: async () => events }
    return { ok: false, status: 404, json: async () => ({}) }
  })
  vi.stubGlobal('fetch', mock)
  return { mock, calls }
}

function renderPage() {
  queryClient.clear()
  window.localStorage.clear()
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ActiveProvider>
          <EventsPage />
        </ActiveProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('EventsPage Qt-Tabelle', () => {
  beforeEach(() => {
    vi.unstubAllGlobals()
    window.localStorage.clear()
    events = [
      { id: 'e-1', name: 'Probe A', date: '2026-09-01', event_type: 'Probe', project_id: 'p-1', yes_count: 1, conditional_count: 0 },
      { id: 'e-2', name: 'Konzert', date: '2026-10-01', event_type: 'Konzert', project_id: 'p-1', yes_count: 0, conditional_count: 0 },
    ]
  })

  afterEach(() => {
    cleanup()
  })

  it('sorts like Qt (Datum/Name asc/desc)', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage()
    await screen.findByText('Probe A')
    await user.selectOptions(screen.getByLabelText('Sortieren'), 'date-asc')
    await waitFor(() => {
      expect(
        calls.some((c) => c.url.includes('sort=date')),
      ).toBe(true)
    })
  })

  it('creates via Hinzufügen', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage()
    await screen.findByText('Probe A')
    await user.click(screen.getByRole('button', { name: 'Hinzufügen' }))
    await user.type(screen.getByLabelText('Name'), 'Neu')
    await user.type(screen.getByLabelText('Datum'), '2026-12-01')
    await user.click(screen.getByRole('button', { name: 'Anlegen' }))
    await waitFor(() => {
      expect(
        calls.some(
          (c) =>
            c.method === 'POST' &&
            c.url.endsWith('/api/events') &&
            (c.body as { name: string }).name === 'Neu',
        ),
      ).toBe(true)
    })
  })

  it('edits, duplicates and deletes from the row', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage()
    await screen.findByText('Probe A')
    const row = screen.getByText('Probe A').closest('tr') as HTMLElement
    await user.click(within(row).getByRole('button', { name: 'Bearbeiten' }))
    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByLabelText('Name')).toHaveValue('Probe A')
    await user.click(within(dialog).getByRole('button', { name: 'Abbrechen' }))
    await user.click(within(row).getByRole('button', { name: 'Duplizieren' }))
    await waitFor(() => {
      expect(
        calls.some(
          (c) =>
            c.method === 'POST' &&
            (c.body as { name: string }).name === 'Probe A (Kopie)',
        ),
      ).toBe(true)
    })
    const row2 = screen
      .getAllByText('Konzert')
      .find((el) => el.tagName === 'TD')
      ?.closest('tr') as HTMLElement
    await user.click(within(row2).getByRole('button', { name: 'Löschen' }))
    await user.click(within(row2).getByRole('button', { name: 'Wirklich löschen' }))
    await waitFor(() => {
      expect(
        calls.some((c) => c.method === 'DELETE' && c.url.endsWith('/api/events/e-2')),
      ).toBe(true)
    })
  })
})
