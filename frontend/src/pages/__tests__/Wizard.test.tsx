// M2 increment 6: Aufgaben-Wizard (Multi-Step über M1-API).
// Workflows: Aufstellung planen, Termin eintragen, Mitglied aufnehmen.
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { queryClient } from '../../api/client'
import WizardPage from '../WizardPage'

const PROJECTS = [{ id: 'p-1', name: 'Hoffmann' }]
const EVENTS = [
  { id: 'e-1', name: 'Probe A', date: '2026-09-01', event_type: 'Probe', project_id: 'p-1', yes_count: 0, conditional_count: 0 },
]
const GROUPS = [
  { id: 'Sopran 1', short: 'S1', order: 1, color_light: '#fff', color_dark: '#000' },
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
    if (u.includes('/api/config/voice-groups')) return { ok: true, json: async () => GROUPS }
    if (u.includes('/api/formations') && method === 'POST') {
      return { ok: true, status: 201, json: async () => ({ id: 'f-1', ...(body as object) }) }
    }
    if (u.includes('/api/events') && method === 'POST') {
      return { ok: true, status: 201, json: async () => ({ id: 'e-9', ...(body as object) }) }
    }
    if (u.includes('/api/singers') && method === 'POST') {
      return { ok: true, status: 201, json: async () => ({ id: 's-9', ...(body as object) }) }
    }
    if (u.includes('/api/events')) return { ok: true, json: async () => EVENTS }
    return { ok: true, json: async () => [] }
  })
  vi.stubGlobal('fetch', mock)
  return { mock, calls }
}

function renderPage() {
  queryClient.clear()
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <WizardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('WizardPage', () => {
  beforeEach(() => {
    vi.unstubAllGlobals()
  })

  afterEach(() => {
    cleanup()
  })

  it('shows the three workflows', async () => {
    stubFetch()
    renderPage()
    expect(await screen.findByText('Aufstellung planen')).toBeInTheDocument()
    expect(screen.getByText('Termin eintragen')).toBeInTheDocument()
    expect(screen.getByText('Chormitglied aufnehmen')).toBeInTheDocument()
  })

  it('starts preselected from the route', async () => {
    stubFetch()
    queryClient.clear()
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/wizard/event']}>
          <Routes>
            <Route path="/wizard/:flow" element={<WizardPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    )
    expect(await screen.findByLabelText('Name')).toBeInTheDocument()
    expect(screen.queryByText('Aufstellung planen')).not.toBeInTheDocument()
  })

  it('termin flow creates an event', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage()
    await user.click(await screen.findByText('Termin eintragen'))
    await user.type(screen.getByLabelText('Name'), 'Neue Probe')
    await user.type(screen.getByLabelText('Datum'), '2026-12-01')
    await user.click(screen.getByRole('button', { name: 'Anlegen' }))
    await waitFor(() => {
      expect(
        calls.some(
          (c) =>
            c.method === 'POST' &&
            c.url.endsWith('/api/events') &&
            (c.body as { name: string }).name === 'Neue Probe',
        ),
      ).toBe(true)
    })
    expect(await screen.findByText(/angelegt/i)).toBeInTheDocument()
  })

  it('aufstellung flow seeds a formation for the event', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage()
    await user.click(await screen.findByText('Aufstellung planen'))
    await user.selectOptions(screen.getByLabelText('Projekt'), 'p-1')
    await user.click(screen.getByRole('button', { name: 'Weiter' }))
    await user.selectOptions(screen.getByLabelText('Termin'), 'e-1')
    await user.click(screen.getByRole('button', { name: 'Weiter' }))
    await user.click(screen.getByRole('button', { name: 'Weiter' }))
    await user.click(screen.getByRole('button', { name: 'Aufstellung anlegen' }))
    await waitFor(() => {
      expect(
        calls.some(
          (c) =>
            c.method === 'POST' &&
            c.url.endsWith('/api/formations') &&
            (c.body as { event_id: string }).event_id === 'e-1',
        ),
      ).toBe(true)
    })
    expect(await screen.findByText(/Aufstellung angelegt/i)).toBeInTheDocument()
  })

  it('mitglied flow creates a singer', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage()
    await user.click(await screen.findByText('Chormitglied aufnehmen'))
    await user.type(screen.getByLabelText('Name'), 'Neu Mitglied')
    await user.click(screen.getByRole('button', { name: 'Speichern' }))
    await waitFor(() => {
      expect(
        calls.some(
          (c) =>
            c.method === 'POST' &&
            c.url.endsWith('/api/singers') &&
            (c.body as { full_name: string }).full_name === 'Neu Mitglied',
        ),
      ).toBe(true)
    })
    expect(await screen.findByText(/aufgenommen/i)).toBeInTheDocument()
  })
})
