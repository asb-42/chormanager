// M2 increment 2: events table (filters + counts) and projects
// with summary. Ruft GET /api/events|/projects (M1).
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { queryClient } from '../../api/client'
import EventsPage from '../EventsPage'
import ProjectsPage from '../ProjectsPage'

const EVENTS = [
  { id: 'e-1', name: 'Probe A', date: '2026-09-01', event_type: 'Probe', project_id: 'p-1', yes_count: 3, conditional_count: 1 },
]

const PROJECTS = [{ id: 'p-1', name: 'Hoffmann', description: null, is_active: 0, spielzeit: null }]

const SUMMARY = {
  project_id: 'p-1',
  events: [{ event_id: 'e-1', name: 'Probe A', date: '2026-09-01', yes: 3, conditional: 1 }],
  by_voice_group: { 'Sopran 1': { yes: 2, conditional: 1 } },
}

function stubFetch() {
  const calls: string[] = []
  const mock = vi.fn(async (url: string) => {
    calls.push(String(url))
    const u = String(url)
    if (u.includes('/api/projects/p-1/summary')) return { ok: true, json: async () => SUMMARY }
    if (u.includes('/api/projects')) return { ok: true, json: async () => PROJECTS }
    return { ok: true, json: async () => EVENTS }
  })
  vi.stubGlobal('fetch', mock)
  return { mock, calls }
}

function renderWith(path: string, page: React.ReactNode) {
  queryClient.clear()
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>{page}</MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('EventsPage', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('renders event rows with counts', async () => {
    stubFetch()
    renderWith('/events', <EventsPage />)
    expect(await screen.findByText('Probe A')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('project filter narrows the query', async () => {
    const { calls } = stubFetch()
    renderWith('/events', <EventsPage />)
    await screen.findByText('Probe A')
    await userEvent.selectOptions(screen.getByLabelText('Projekt'), 'p-1')
    await waitFor(() => {
      expect(calls.some((u) => u.includes('project_id=p-1'))).toBe(true)
    })
  })
})

describe('ProjectsPage', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('renders projects and shows summary on click', async () => {
    stubFetch()
    renderWith('/projects', <ProjectsPage />)
    await userEvent.click(await screen.findByText('Hoffmann'))
    expect(await screen.findByText('Sopran 1')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
  })
})
