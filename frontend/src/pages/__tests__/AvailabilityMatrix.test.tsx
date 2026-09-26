// M2 increment 5: availability matrix (select per singer + bulk save).
// Ruft GET/PUT /api/events/{id}/availability (M1).
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { queryClient } from '../../api/client'


import { ActiveProvider } from '../../active/active'
import AvailabilityPage from '../AvailabilityPage'

beforeEach(() => {
  window.localStorage.clear()
})

const EVENTS = [
  { id: 'e-1', name: 'Probe A', date: '2026-09-01', event_type: 'Probe', yes_count: 1, conditional_count: 0 },
  { id: 'e-2', name: 'Konzert', date: '2026-10-01', event_type: 'Konzert', yes_count: 0, conditional_count: 0 },
]

let matrixEntries = [
  { singer_id: 's-1', full_name: 'Anna Muster', short_name: 'Anna', voice_group: 'Sopran 1', status: 'yes' },
  { singer_id: 's-2', full_name: 'Berta B', short_name: 'Berta', voice_group: 'Bass 2', status: 'none' },
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
    if (u.includes('/api/events') && !u.includes('/availability')) {
      return { ok: true, json: async () => EVENTS }
    }
    if (u.includes('/availability')) {
      if (method === 'PUT') {
        for (const entry of (body as { entries: Array<{ singer_id: string; status: string }> }).entries) {
          matrixEntries = matrixEntries.map((row) =>
            row.singer_id === entry.singer_id ? { ...row, status: entry.status } : row,
          )
        }
        return { ok: true, json: async () => ({ updated: 2 }) }
      }
      return {
        ok: true,
        json: async () => ({ event_id: 'e-1', entries: matrixEntries }),
      }
    }
    return { ok: false, status: 404, json: async () => ({}) }
  })
  vi.stubGlobal('fetch', mock)
  return { mock, calls }
}

function renderPage() {
  queryClient.clear()
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ActiveProvider>
          <AvailabilityPage />
        </ActiveProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('AvailabilityPage', () => {
  beforeEach(() => {
    vi.unstubAllGlobals()
    matrixEntries = [
      { singer_id: 's-1', full_name: 'Anna Muster', short_name: 'Anna', voice_group: 'Sopran 1', status: 'yes' },
      { singer_id: 's-2', full_name: 'Berta B', short_name: 'Berta', voice_group: 'Bass 2', status: 'none' },
    ]
  })

  afterEach(() => {
    cleanup()
  })

  it('renders the matrix with current statuses', async () => {
    stubFetch()
    renderPage()
    await screen.findByText('Anna Muster')
    expect(
      (screen.getByLabelText('Anna Muster') as HTMLSelectElement).value,
    ).toBe('yes')
    expect(
      (screen.getByLabelText('Berta B') as HTMLSelectElement).value,
    ).toBe('none')
  })

  it('saves changed statuses as bulk', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage()
    await screen.findByText('Anna Muster')
    await user.selectOptions(screen.getByLabelText('Berta B'), 'conditional')
    await user.click(screen.getByRole('button', { name: 'Speichern' }))
    await waitFor(() => {
      const put = calls.find((c) => c.method === 'PUT')
      expect(put?.url).toContain('/api/events/e-1/availability')
      expect(put?.body).toEqual({
        entries: [
          { singer_id: 's-1', status: 'yes' },
          { singer_id: 's-2', status: 'conditional' },
        ],
      })
    })
    expect(await screen.findByText('Gespeichert.')).toBeInTheDocument()
  })

  it('switching events refetches the matrix', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage()
    await screen.findByText('Anna Muster')
    await user.selectOptions(screen.getByLabelText('Termin'), 'e-2')
    await waitFor(() => {
      expect(
        calls.some((c) => c.url.includes('/api/events/e-2/availability')),
      ).toBe(true)
    })
  })
})

describe('Aktiv-Kontext: Verfügbarkeit', () => {
  beforeEach(() => {
    matrixEntries = [
      { singer_id: 's-1', full_name: 'Anna Muster', short_name: 'Anna', voice_group: 'Sopran 1', status: 'yes' },
      { singer_id: 's-2', full_name: 'Berta B', short_name: 'Berta', voice_group: 'Bass 2', status: 'none' },
    ]
  })

  afterEach(() => {
    cleanup()
  })

  it('filtert auf die aktive Besetzung, opt-out möglich', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    window.localStorage.setItem('chor-active-besetzung', 'x-9')
    // Besetzungsliste kennt x-9 mit nur s-1.
    const origFetch = window.fetch
    window.fetch = (async (url: string, init?: RequestInit) => {
      if (String(url).includes('/api/besetzungen')) {
        return {
          ok: true,
          json: async () => [{ id: 'x-9', name: 'Kern', singer_ids: ['s-1'] }],
        }
      }
      return (origFetch as typeof fetch)(url, init)
    }) as typeof fetch
    renderPage()
    expect(await screen.findByText(/Gefiltert auf Besetzung/)).toBeInTheDocument()
    expect(await screen.findByText('Anna Muster')).toBeInTheDocument()
    expect(screen.queryByText('Berta B')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Alle Sänger zeigen' }))
    expect(await screen.findByText('Berta B')).toBeInTheDocument()
    expect(calls.length).toBeGreaterThan(0)
  })

  it('wählt den aktiven Termin vor und setzt ihn bei Wechsel', async () => {
    const user = userEvent.setup({ delay: 10 })
    stubFetch()
    window.localStorage.setItem('chor-active-event', 'e-2')
    renderPage()
    await screen.findByText('Anna Muster')
    expect(
      (screen.getByLabelText('Termin') as HTMLSelectElement).value,
    ).toBe('e-2')
    await user.selectOptions(screen.getByLabelText('Termin'), 'e-1')
    expect(window.localStorage.getItem('chor-active-event')).toBe('e-1')
  })
})
