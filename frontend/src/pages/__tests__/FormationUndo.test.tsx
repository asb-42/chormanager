// M3: editor undo via icon toolbar (mocked API).
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
      singer: { singer_id: 's-1', name: 'Anna', voice_group: 'Sopran 1', height: 0, affinity: '' },
      row: 0,
      col: 0,
    },
  ],
  metadata: {},
  event_id: 'e-1',
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
    if (u.includes('/api/formations/f-1') && method === 'GET') {
      return { ok: true, json: async () => DOC }
    }
    if (u.includes('/placements') && method === 'PUT') {
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

describe('FormationEditorPage undo', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('undo is disabled until a change, then reverts it', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage()
    await screen.findByText('Anna')
    const undo = screen.getByRole('button', { name: 'Rückgängig' })
    expect(undo).toBeDisabled()
    // Änderung via Resize (5 Spalten statt 4 Zeilen lassen alles liegen).
    await user.clear(screen.getByLabelText('Reihen'))
    await user.type(screen.getByLabelText('Reihen'), '3')
    await user.click(screen.getByRole('button', { name: 'Anwenden' }))
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Rückgängig' })).toBeEnabled()
    })
    await user.click(screen.getByRole('button', { name: 'Rückgängig' }))
    await waitFor(() => {
      const puts = calls.filter(
        (c) => c.method === 'PUT' && c.url.includes('/placements'),
      )
      expect(puts.length).toBeGreaterThanOrEqual(2)
      const last = puts[puts.length - 1]
      expect((last.body as { rows?: number }).rows).toBe(4)
    })
  })

  it('responds to the Bearbeiten menu events', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage()
    await screen.findByText('Anna')
    await user.clear(screen.getByLabelText('Reihen'))
    await user.type(screen.getByLabelText('Reihen'), '3')
    await user.click(screen.getByRole('button', { name: 'Anwenden' }))
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Rückgängig' })).toBeEnabled()
    })
    window.dispatchEvent(new CustomEvent('chor:undo'))
    await waitFor(() => {
      const puts = calls.filter(
        (c) => c.method === 'PUT' && c.url.includes('/placements'),
      )
      expect(puts.length).toBeGreaterThanOrEqual(2)
      const last = puts[puts.length - 1]
      expect((last.body as { rows?: number }).rows).toBe(4)
    })
  })
})
