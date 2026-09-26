// Sweep 1/6 Projekte: Tabelle (Spielzeit/Name/Beschreibung/Aktiv/
// Anz. Termine), Suche, Sortierung, Zeilenaktionen, Neu-Dialog.
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { queryClient } from '../../api/client'
import { ActiveProvider } from '../../active/active'
import ProjectsPage from '../ProjectsPage'

let projects = [
  { id: 'p-1', name: 'B-Projekt', description: 'Desc B', spielzeit: '2026/27', event_count: 2 },
  { id: 'p-2', name: 'A-Projekt', description: 'Desc A', spielzeit: '2025/26', event_count: 0 },
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
    if (u.includes('/api/projects') && method === 'POST') {
      const created = { id: 'p-9', event_count: 0, ...(body as object) }
      projects.push(created as (typeof projects)[number])
      return { ok: true, status: 201, json: async () => created }
    }
    if (u.match(/\/api\/projects\/[^/]+$/) && method === 'PUT') {      const id = u.split('/').pop() as string
      projects = projects.map((p) => (p.id === id ? { ...p, ...(body as object) } : p))
      return { ok: true, json: async () => projects.find((p) => p.id === id) }
    }
    if (u.match(/\/api\/projects\/[^/]+$/) && method === 'DELETE') {
      const id = u.split('/').pop() as string
      projects = projects.filter((p) => p.id !== id)
      return { ok: true, status: 204, json: async () => ({}) }
    }
    if (u.match(/\/api\/projects\/[^/]+$/) && method === 'GET') {
      const id = u.split('/').pop() as string
      return { ok: true, json: async () => projects.find((p) => p.id === id) }
    }
    if (u.includes('/api/projects')) {
      return { ok: true, json: async () => projects }
    }
  })
  vi.stubGlobal('fetch', mock)
  return { mock, calls }
}

function renderPage() {
  queryClient.clear()
  window.localStorage.clear()
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/projects']}>
        <ActiveProvider>
          <Routes>
            <Route path="/projects" element={<ProjectsPage />} />
          </Routes>
        </ActiveProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ProjectsPage Tabelle', () => {
  beforeEach(() => {
    vi.unstubAllGlobals()
    projects = [
      { id: 'p-1', name: 'B-Projekt', description: 'Desc B', spielzeit: '2026/27', event_count: 2 },
      { id: 'p-2', name: 'A-Projekt', description: 'Desc A', spielzeit: '2025/26', event_count: 0 },
    ]
  })

  afterEach(() => {
    cleanup()
  })

  it('renders all Qt columns', async () => {
    stubFetch()
    renderPage()
    expect(await screen.findByText('B-Projekt')).toBeInTheDocument()
    expect(screen.getByText('2026/27')).toBeInTheDocument()
    expect(screen.getByText('Desc B')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('searches and sorts like Qt', async () => {
    const user = userEvent.setup({ delay: 10 })
    stubFetch()
    renderPage()
    await screen.findByText('B-Projekt')
    await user.type(screen.getByPlaceholderText('Suchen …'), 'A-Projekt')
    await waitFor(() => {
      expect(screen.queryByText('B-Projekt')).not.toBeInTheDocument()
    })
    await user.clear(screen.getByPlaceholderText('Suchen …'))
    await user.selectOptions(screen.getByLabelText('Sortieren'), 'spielzeit')
    await user.selectOptions(screen.getByLabelText('Reihenfolge'), 'asc')
    const rows = await screen.findAllByRole('row')
    expect(rows[1]).toHaveTextContent('A-Projekt')
  })

  it('creates via Neu-Dialog', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage()
    await screen.findByText('B-Projekt')
    await user.click(screen.getByRole('button', { name: 'Hinzufügen' }))
    await user.type(screen.getByLabelText('Name'), 'Neu')
    await user.click(screen.getByRole('button', { name: 'Anlegen' }))
    await waitFor(() => {
      expect(
        calls.some(
          (c) =>
            c.method === 'POST' &&
            c.url.endsWith('/api/projects') &&
            (c.body as { name: string }).name === 'Neu',
        ),
      ).toBe(true)
    })
    expect(await screen.findByText('Neu')).toBeInTheDocument()
  })

  it('duplicates with (Kopie) and deletes after confirm', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage()
    await screen.findByText('B-Projekt')
    const row = screen.getByText('B-Projekt').closest('tr') as HTMLElement
    await user.click(within(row).getByRole('button', { name: 'Duplizieren' }))
    await waitFor(() => {
      expect(
        calls.some(
          (c) =>
            c.method === 'POST' &&
            (c.body as { name: string }).name === 'B-Projekt (Kopie)',
        ),
      ).toBe(true)
    })
    const row2 = screen.getByText('A-Projekt').closest('tr') as HTMLElement
    await user.click(within(row2).getByRole('button', { name: 'Löschen' }))
    await user.click(within(row2).getByRole('button', { name: 'Wirklich löschen' }))
    await waitFor(() => {
      expect(
        calls.some((c) => c.method === 'DELETE' && c.url.endsWith('/api/projects/p-2')),
      ).toBe(true)
    })
  })
})
