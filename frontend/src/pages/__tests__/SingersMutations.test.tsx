// M2 increment 3: singer create/edit/delete (erste Mutations).
//
// POST/PUT/DELETE /api/singers (M1) via TanStack-Mutations;
// Token aus localStorage (VITE_API_TOKEN-Fallback im Client).
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { queryClient } from '../../api/client'
import SingersPage from '../SingersPage'

let singers = [
  { id: 's-1', full_name: 'Anna Muster', short_name: 'Anna', voice_group: 'Sopran 1' },
]

const GROUPS = [
  { id: 'Sopran 1', short: 'S1', order: 1, color_light: '#fff', color_dark: '#000' },
  { id: 'Bass 2', short: 'B2', order: 8, color_light: '#fff', color_dark: '#000' },
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
    if (u.includes('/api/config/voice-groups')) {
      return { ok: true, json: async () => GROUPS }
    }
    if (method === 'POST' && u.endsWith('/api/singers')) {
      const created = { id: 's-9', ...(body as object) }
      singers.push(created as (typeof singers)[number])
      return { ok: true, status: 201, json: async () => created }
    }
    if (method === 'PUT') {
      const id = u.split('/').pop() as string
      singers = singers.map((s) =>
        s.id === id ? { ...s, ...(body as object) } : s,
      )
      return { ok: true, json: async () => singers.find((s) => s.id === id) }
    }
    if (method === 'DELETE') {
      const id = u.split('/').pop() as string
      singers = singers.filter((s) => s.id !== id)
      return { ok: true, status: 204, json: async () => ({}) }
    }
    return { ok: true, json: async () => singers }
  })
  vi.stubGlobal('fetch', mock)
  return { mock, calls }
}

function renderPage() {
  queryClient.clear()
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <SingersPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('SingersPage mutations', () => {
  beforeEach(() => {
    vi.unstubAllGlobals()
    window.localStorage.clear()
    singers = [
      { id: 's-1', full_name: 'Anna Muster', short_name: 'Anna', voice_group: 'Sopran 1' },
    ]
  })

  afterEach(() => {
    cleanup()
  })

  it('creates a singer via dialog', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage()
    await screen.findByText('Anna Muster')
    await user.click(screen.getByRole('button', { name: 'Hinzufügen' }))
    await user.type(screen.getByLabelText('Name'), 'Clara Neu')
    await user.click(screen.getByRole('button', { name: 'Speichern' }))
    await waitFor(() => {
      expect(
        calls.some(
          (c) =>
            c.method === 'POST' &&
            c.url.endsWith('/api/singers') &&
            (c.body as { full_name: string }).full_name === 'Clara Neu',
        ),
      ).toBe(true)
    })
    expect(await screen.findByText('Clara Neu')).toBeInTheDocument()
  })

  it('blocks saving without a name', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage()
    await screen.findByText('Anna Muster')
    await user.click(screen.getByRole('button', { name: 'Hinzufügen' }))
    expect(screen.getByRole('button', { name: 'Speichern' })).toBeDisabled()
    expect(calls.some((c) => c.method === 'POST')).toBe(false)
  })

  it('edits a singer via dialog', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage()
    await screen.findByText('Anna Muster')
    await user.click(screen.getByRole('button', { name: 'Bearbeiten' }))
    expect(screen.getByLabelText('Name')).toHaveValue('Anna Muster')
    await user.clear(screen.getByLabelText('Kurzname'))
    await user.type(screen.getByLabelText('Kurzname'), 'Anni')
    await user.click(screen.getByRole('button', { name: 'Speichern' }))
    await waitFor(() => {
      expect(
        calls.some(
          (c) =>
            c.method === 'PUT' &&
            c.url.endsWith('/api/singers/s-1') &&
            (c.body as { short_name: string }).short_name === 'Anni',
        ),
      ).toBe(true)
    })
    expect(await screen.findByText('Anni')).toBeInTheDocument()
  })

  it('deletes a singer after confirm', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage()
    await screen.findByText('Anna Muster')
    await user.click(screen.getByRole('button', { name: 'Löschen' }))
    await user.click(
      screen.getByRole('button', { name: 'Wirklich löschen' }),
    )
    await waitFor(() => {
      expect(
        calls.some(
          (c) => c.method === 'DELETE' && c.url.endsWith('/api/singers/s-1'),
        ),
      ).toBe(true)
    })
    await waitFor(() => {
      expect(screen.queryByText('Anna Muster')).not.toBeInTheDocument()
    })
  })

  it('sends the token from localStorage', async () => {
    window.localStorage.setItem('chor-api-token', 't-1')
    const { mock } = stubFetch()
    renderPage()
    await screen.findByText('Anna Muster')
    const headers = mock.mock.calls[0][1]?.headers as Record<string, string>
    expect(headers['Authorization']).toBe('Bearer t-1')
  })
})
