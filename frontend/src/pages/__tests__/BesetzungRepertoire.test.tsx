// M2 increment 4: Besetzung/Repertoire lists + mutations.
// Ruft M1-Endpoints (Listen, Filter, POST/DELETE).
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { queryClient } from '../../api/client'
import BesetzungPage from '../BesetzungPage'
import RepertoirePage from '../RepertoirePage'

let besetzungen = [{ id: 'b-1', name: 'Stamm', project_id: 'p-1', singer_ids: ['s-1'] }]
let repertoire = [{ id: 'r-1', title: 'Motette', composer: 'Bach', project_id: 'p-1' }]
const PROJECTS = [{ id: 'p-1', name: 'Hoffmann' }]
const SINGERS = [
  { id: 's-1', full_name: 'Anna Muster', short_name: 'Anna', voice_group: 'Sopran 1' },
  { id: 's-2', full_name: 'Berta B', short_name: 'Berta', voice_group: 'Bass 2' },
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
        const created = { id: 'b-9', ...(body as object) }
        besetzungen.push(created as (typeof besetzungen)[number])
        return { ok: true, status: 201, json: async () => created }
      }
      if (method === 'DELETE') {
        const id = u.split('/').pop() as string
        besetzungen = besetzungen.filter((b) => b.id !== id)
        return { ok: true, status: 204, json: async () => ({}) }
      }
      const filtered = u.includes('project_id=p-1')
        ? besetzungen.filter((b) => b.project_id === 'p-1')
        : besetzungen
      return { ok: true, json: async () => filtered }
    }
    if (u.includes('/api/repertoire')) {
      if (method === 'POST') {
        const created = { id: 'r-9', ...(body as object) }
        repertoire.push(created as (typeof repertoire)[number])
        return { ok: true, status: 201, json: async () => created }
      }
      if (method === 'DELETE') {
        const id = u.split('/').pop() as string
        repertoire = repertoire.filter((r) => r.id !== id)
        return { ok: true, status: 204, json: async () => ({}) }
      }
      return { ok: true, json: async () => repertoire }
    }
    return { ok: false, status: 404, json: async () => ({}) }
  })
  vi.stubGlobal('fetch', mock)
  return { mock, calls }
}

function renderPage(page: React.ReactNode) {
  queryClient.clear()
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{page}</MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('BesetzungPage', () => {
  beforeEach(() => {
    vi.unstubAllGlobals()
    besetzungen = [{ id: 'b-1', name: 'Stamm', project_id: 'p-1', singer_ids: ['s-1'] }]
  })

  afterEach(() => {
    cleanup()
  })

  it('renders lineups with singer counts', async () => {
    stubFetch()
    renderPage(<BesetzungPage />)
    expect(await screen.findByText('Stamm')).toBeInTheDocument()
    expect(screen.getByText('1')).toBeInTheDocument()
  })

  it('creates a lineup with checked singers', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage(<BesetzungPage />)
    await screen.findByText('Stamm')
    await user.click(screen.getByRole('button', { name: 'Neu' }))
    await user.type(screen.getByLabelText('Name'), 'Gäste')
    await user.click(screen.getByRole('checkbox', { name: /Berta/ }))
    await user.click(screen.getByRole('button', { name: 'Speichern' }))
    await waitFor(() => {
      expect(
        calls.some(
          (c) =>
            c.method === 'POST' &&
            c.url.endsWith('/api/besetzungen') &&
            JSON.stringify((c.body as { singer_ids: string[] }).singer_ids) ===
              JSON.stringify(['s-2']),
        ),
      ).toBe(true)
    })
    expect(await screen.findByText('Gäste')).toBeInTheDocument()
  })

  it('deletes a lineup after confirm', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage(<BesetzungPage />)
    await screen.findByText('Stamm')
    await user.click(screen.getByRole('button', { name: 'Löschen' }))
    await user.click(screen.getByRole('button', { name: 'Wirklich löschen' }))
    await waitFor(() => {
      expect(
        calls.some(
          (c) => c.method === 'DELETE' && c.url.endsWith('/api/besetzungen/b-1'),
        ),
      ).toBe(true)
    })
    await waitFor(() => {
      expect(screen.queryByText('Stamm')).not.toBeInTheDocument()
    })
  })
})

describe('RepertoirePage', () => {
  beforeEach(() => {
    vi.unstubAllGlobals()
    repertoire = [{ id: 'r-1', title: 'Motette', composer: 'Bach', project_id: 'p-1' }]
  })

  afterEach(() => {
    cleanup()
  })

  it('renders entries and creates one', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage(<RepertoirePage />)
    expect(await screen.findByText('Motette')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Neu' }))
    await user.type(screen.getByLabelText('Titel'), 'Messe')
    await user.click(screen.getByRole('button', { name: 'Speichern' }))
    await waitFor(() => {
      expect(
        calls.some(
          (c) =>
            c.method === 'POST' &&
            c.url.endsWith('/api/repertoire') &&
            (c.body as { title: string }).title === 'Messe',
        ),
      ).toBe(true)
    })
    expect(await screen.findByText('Messe')).toBeInTheDocument()
  })

  it('deletes an entry after confirm', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage(<RepertoirePage />)
    await screen.findByText('Motette')
    await user.click(screen.getByRole('button', { name: 'Löschen' }))
    await user.click(screen.getByRole('button', { name: 'Wirklich löschen' }))
    await waitFor(() => {
      expect(
        calls.some(
          (c) => c.method === 'DELETE' && c.url.endsWith('/api/repertoire/r-1'),
        ),
      ).toBe(true)
    })
  })
})
