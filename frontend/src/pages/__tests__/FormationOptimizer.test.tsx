// M3.3: optimizer dialog + grid resize specs (mocked API).
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { queryClient } from '../../api/client'
import FormationEditorPage from '../FormationEditorPage'

const DOC = {
  id: 'f-1',
  name: 'Probe',
  rows: 4,
  cols: 5,
  staggered: false,
  voicing_config: [],
  singers: [],
  placed: [
    {
      singer: { singer_id: 's-1', name: 'Anna Muster', voice_group: 'Sopran 1', height: 170, affinity: '' },
      row: 0,
      col: 0,
    },
    {
      singer: { singer_id: 's-2', name: 'Berta B', voice_group: 'Bass 2', height: 185, affinity: '' },
      row: 0,
      col: 1,
    },
  ],
  metadata: {},
  event_id: 'e-1',
}

const RULES = [
  { id: 'height', name: 'Größe', primary: true },
  { id: 'affinity', name: 'Nähe', primary: false },
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
    if (u.includes('/api/formations/rules')) {
      return { ok: true, json: async () => RULES }
    }
    if (u.includes('/optimize') && method === 'POST') {
      return {
        ok: true,
        json: async () => ({
          placements: [{ singer_id: 's-1', row: 1, col: 1 }],
          swap_count: 2,
          cost: 10,
          applied_rules: ['height'],
          messages: [],
        }),
      }
    }
    if (u.includes('/placements') && method === 'PUT') {
      return { ok: true, json: async () => DOC }
    }
    if (u.includes('/api/formations/f-1')) {
      return { ok: true, json: async () => DOC }
    }
    return { ok: true, json: async () => [] }
  })
  vi.stubGlobal('fetch', mock)
  return { mock, calls }
}

function renderPage() {
  queryClient.clear()
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/formations/f-1']}>
        <Routes>
          <Route path="/formations/:id" element={<FormationEditorPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('FormationEditorPage optimizer', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('previews rules and applies on confirm', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage()
    await screen.findByText('Anna Muster')
    await user.click(screen.getByRole('button', { name: 'Optimieren' }))
    await user.click(screen.getByRole('checkbox', { name: 'Größe' }))
    await user.click(screen.getByRole('button', { name: 'Vorschau' }))
    expect(await screen.findByText(/2 Vertauschungen/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Übernehmen' }))
    await waitFor(() => {
      const put = calls.find(
        (c) => c.method === 'PUT' && c.url.includes('/placements'),
      )
      expect(put?.body).toEqual({
        staggered: false,
        rows: 4,
        cols: 5,
        placements: [{ singer_id: 's-1', row: 1, col: 1 }],
      })
    })
  })
})

describe('FormationEditorPage resize', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('applies new dimensions', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage()
    await screen.findByText('Anna Muster')
    await user.clear(screen.getByLabelText('Reihen'))
    await user.type(screen.getByLabelText('Reihen'), '2')
    await user.click(screen.getByRole('button', { name: 'Anwenden' }))
    await waitFor(() => {
      const put = calls.find(
        (c) =>
          c.method === 'PUT' &&
          c.url.includes('/placements') &&
          (c.body as { rows?: number }).rows === 2,
      )
      expect(put).toBeDefined()
    })
  })

  it('asks before dropping singers outside the grid', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage()
    await screen.findByText('Anna Muster')
    await user.clear(screen.getByLabelText('Spalten'))
    await user.type(screen.getByLabelText('Spalten'), '1')
    await user.click(screen.getByLabelText('Reihen'))
    await user.clear(screen.getByLabelText('Reihen'))
    await user.type(screen.getByLabelText('Reihen'), '1')
    await user.click(screen.getByRole('button', { name: 'Anwenden' }))
    expect(await screen.findByText(/fällt raus|fallen raus/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Trotzdem anwenden' }))
    await waitFor(() => {
      const puts = calls.filter(
        (c) => c.method === 'PUT' && c.url.includes('/placements'),
      )
      const last = puts[puts.length - 1]
      expect((last.body as { placements: unknown[] }).placements).toEqual([
        { singer_id: 's-1', row: 0, col: 0 },
      ])
    })
  })
})
