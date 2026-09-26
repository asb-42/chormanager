// Sweep 6/6 Repertoire: 8 Qt-Spalten, Suche, Sortierung,
// Bearbeiten (voll), Duplizieren.
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { queryClient } from '../../api/client'
import { ActiveProvider } from '../../active/active'
import RepertoirePage from '../RepertoirePage'

let repertoire = [
  { id: 'r-1', composer: 'Bach', title: 'Motette', dates: '1685-1750', country: 'DE', publisher: 'Bärenreiter', arrangement: 'SATB', location: 'Archiv', project_id: 'p-1' },
  { id: 'r-2', composer: 'Mozart', title: 'Messe', dates: null, country: null, publisher: null, arrangement: null, location: null, project_id: null },
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
    if (u.includes('/api/repertoire') && method === 'POST') {
      const created = { id: 'r-9', ...(body as object) }
      repertoire.push(created as (typeof repertoire)[number])
      return { ok: true, status: 201, json: async () => created }
    }
    if (u.match(/\/api\/repertoire\/[^/]+$/) && method === 'PUT') {
      const id = u.split('/').pop() as string
      repertoire = repertoire.map((r) => (r.id === id ? { ...r, ...(body as object) } : r))
      return { ok: true, json: async () => repertoire.find((r) => r.id === id) }
    }
    if (u.includes('/api/repertoire')) {
      const query = u.split('?')[1] ?? ''
      const search = new URLSearchParams(query).get('search')?.toLowerCase() ?? ''
      const filtered = search
        ? repertoire.filter((r) =>
            [r.composer, r.title].some(
              (field) => field && field.toLowerCase().includes(search),
            ),
          )
        : repertoire
      return { ok: true, json: async () => filtered }
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
          <RepertoirePage />
        </ActiveProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('RepertoirePage Qt-Tabelle', () => {
  beforeEach(() => {
    vi.unstubAllGlobals()
    window.localStorage.clear()
    repertoire = [
      { id: 'r-1', composer: 'Bach', title: 'Motette', dates: '1685-1750', country: 'DE', publisher: 'Bärenreiter', arrangement: 'SATB', location: 'Archiv', project_id: 'p-1' },
      { id: 'r-2', composer: 'Mozart', title: 'Messe', dates: null, country: null, publisher: null, arrangement: null, location: null, project_id: null },
    ]
  })

  afterEach(() => {
    cleanup()
  })

  it('renders Qt columns', async () => {
    stubFetch()
    renderPage()
    expect(await screen.findByText('Motette')).toBeInTheDocument()
    for (const header of ['Komponist', 'Titel', 'Lebensdaten', 'Land', 'Verlag', 'Besetzung', 'Standort', 'Programm']) {
      expect(screen.getByText(header, { selector: 'th' })).toBeInTheDocument()
    }
    expect(screen.getByText('1685-1750')).toBeInTheDocument()
    expect(screen.getByText('Bärenreiter')).toBeInTheDocument()
  })

  it('searches and sorts like Qt', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage()
    await screen.findByText('Motette')
    await user.type(screen.getByPlaceholderText('Suchen …'), 'mozart')
    await waitFor(() => {
      expect(
        calls.some((c) => c.url.includes('search=mozart')),
      ).toBe(true)
    })
    await waitFor(() => {
      expect(screen.queryByText('Motette')).not.toBeInTheDocument()
    })
    await user.clear(screen.getByPlaceholderText('Suchen …'))
    await user.selectOptions(screen.getByLabelText('Sortieren'), 'composer')
    await user.selectOptions(screen.getByLabelText('Reihenfolge'), 'desc')
    await waitFor(() => {
      expect(
        calls.some((c) => c.url.includes('sort=composer')),
      ).toBe(true)
    })
  })

  it('edits all fields via dialog', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage()
    await screen.findByText('Motette')
    const row = screen.getByText('Motette').closest('tr') as HTMLElement
    await user.click(within(row).getByRole('button', { name: 'Bearbeiten' }))
    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByLabelText('Titel')).toHaveValue('Motette')
    expect(within(dialog).getByLabelText('Lebensdaten')).toHaveValue('1685-1750')
    await user.clear(within(dialog).getByLabelText('Verlag'))
    await user.type(within(dialog).getByLabelText('Verlag'), 'Neu')
    await user.click(within(dialog).getByRole('button', { name: 'Speichern' }))
    await waitFor(() => {
      expect(
        calls.some(
          (c) =>
            c.method === 'PUT' &&
            c.url.endsWith('/api/repertoire/r-1') &&
            (c.body as { publisher: string }).publisher === 'Neu',
        ),
      ).toBe(true)
    })
  })

  it('duplicates with (Kopie)', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage()
    await screen.findByText('Motette')
    const row = screen.getByText('Motette').closest('tr') as HTMLElement
    await user.click(within(row).getByRole('button', { name: 'Duplizieren' }))
    await waitFor(() => {
      expect(
        calls.some(
          (c) =>
            c.method === 'POST' &&
            (c.body as { title: string }).title === 'Motette (Kopie)',
        ),
      ).toBe(true)
    })
  })
})
