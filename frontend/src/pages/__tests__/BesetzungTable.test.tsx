// Sweep 3/6 Besetzung: Qt-Spalten (inkl. Zuletzt gespeichert),
// Bearbeiten-Dialog, Duplizieren. Keine Suche/Sortierung (wie Qt).
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { queryClient } from '../../api/client'
import { ActiveProvider } from '../../active/active'
import BesetzungPage from '../BesetzungPage'

let besetzungen = [
  { id: 'b-1', name: 'Stamm', project_id: 'p-1', singer_ids: ['s-1', 's-2'], updated_at: '2026-09-01T10:20:00' },
]
const PROJECTS = [{ id: 'p-1', name: 'Hoffmann' }]
const SINGERS = [
  { id: 's-1', full_name: 'Anna Muster', short_name: 'Anna', voice_group: 'Sopran 1' },
]

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
    if (u.includes('/api/singers')) return { ok: true, json: async () => SINGERS }
    if (u.includes('/api/besetzungen')) {
      if (method === 'POST') {
        const created = { id: 'b-9', updated_at: '2026-09-26T00:00:00', ...(body as object) }
        besetzungen.push(created as (typeof besetzungen)[number])
        return { ok: true, status: 201, json: async () => created }
      }
      if (method === 'PUT') {
        const id = u.split('/').pop() as string
        besetzungen = besetzungen.map((b) => (b.id === id ? { ...b, ...(body as object) } : b))
        return { ok: true, json: async () => besetzungen.find((b) => b.id === id) }
      }
      return { ok: true, json: async () => besetzungen }
    }
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
          <BesetzungPage />
        </ActiveProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('BesetzungPage Qt-Tabelle', () => {
  beforeEach(() => {
    vi.unstubAllGlobals()
    window.localStorage.clear()
    besetzungen = [
      { id: 'b-1', name: 'Stamm', project_id: 'p-1', singer_ids: ['s-1', 's-2'], updated_at: '2026-09-01T10:20:00' },
    ]
  })

  afterEach(() => {
    cleanup()
  })

  it('renders Qt columns incl. formatted timestamp', async () => {
    stubFetch()
    renderPage()
    expect(await screen.findByText('Stamm')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText(/01\.09\.2026/)).toBeInTheDocument()
  })

  it('edits via dialog', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage()
    await screen.findByText('Stamm')
    const row = screen.getByText('Stamm').closest('tr') as HTMLElement
    await user.click(within(row).getByRole('button', { name: 'Bearbeiten' }))
    const dialog = await screen.findByRole('dialog')
    await user.clear(within(dialog).getByLabelText('Name'))
    await user.type(within(dialog).getByLabelText('Name'), 'Stamm Neu')
    await user.click(within(dialog).getByRole('button', { name: 'Speichern' }))
    await waitFor(() => {
      expect(
        calls.some(
          (c) =>
            c.method === 'PUT' &&
            c.url.endsWith('/api/besetzungen/b-1') &&
            (c.body as { name: string }).name === 'Stamm Neu',
        ),
      ).toBe(true)
    })
    expect(await screen.findByText('Stamm Neu')).toBeInTheDocument()
  })

  it('duplicates with (Kopie)', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage()
    await screen.findByText('Stamm')
    const row = screen.getByText('Stamm').closest('tr') as HTMLElement
    await user.click(within(row).getByRole('button', { name: 'Duplizieren' }))
    await waitFor(() => {
      expect(
        calls.some(
          (c) =>
            c.method === 'POST' &&
            (c.body as { name: string }).name === 'Stamm (Kopie)' &&
            JSON.stringify((c.body as { singer_ids: string[] }).singer_ids) ===
              JSON.stringify(['s-1', 's-2']),
        ),
      ).toBe(true)
    })
  })
})
