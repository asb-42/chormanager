// Aktiv-Kontext (Desktop-Parität: Aktives Projekt / Aktive Besetzung /
// Aktiver Termin aus state.json + Info-Bar). Web: localStorage, kein
// Backend (Client-Kontext, Single-User-Semantik wie Desktop).
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { queryClient } from '../../api/client'
import { ActiveProvider, useActive } from '../active'
import InfoBar from '../../components/InfoBar'

function Probe() {
  const active = useActive()
  return (
    <div>
      <span data-testid="project">{active.projectId ?? '–'}</span>
      <span data-testid="besetzung">{active.besetzungId ?? '–'}</span>
      <span data-testid="event">{active.eventId ?? '–'}</span>
      <button type="button" onClick={() => active.setProject('p-1')}>
        set-project
      </button>
      <button type="button" onClick={() => active.clearProject()}>
        clear-project
      </button>
    </div>
  )
}

function renderProbe() {
  render(
    <ActiveProvider>
      <Probe />
    </ActiveProvider>,
  )
}

describe('useActive', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  afterEach(() => {
    cleanup()
  })

  it('persists across mounts (localStorage)', async () => {
    const user = userEvent.setup({ delay: 10 })
    renderProbe()
    await user.click(screen.getByRole('button', { name: 'set-project' }))
    expect(screen.getByTestId('project')).toHaveTextContent('p-1')
    expect(window.localStorage.getItem('chor-active-project')).toBe('p-1')
    cleanup()
    renderProbe()
    expect(screen.getByTestId('project')).toHaveTextContent('p-1')
  })

  it('clears', async () => {
    const user = userEvent.setup({ delay: 10 })
    renderProbe()
    await user.click(screen.getByRole('button', { name: 'set-project' }))
    await user.click(screen.getByRole('button', { name: 'clear-project' }))
    expect(screen.getByTestId('project')).toHaveTextContent('–')
    expect(window.localStorage.getItem('chor-active-project')).toBeNull()
  })
})

describe('InfoBar', () => {
  beforeEach(() => {
    window.localStorage.clear()
    window.localStorage.setItem('chor-active-project', 'p-1')
    window.localStorage.setItem('chor-active-besetzung', 'b-1')
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        const u = String(url)
        if (u.includes('/api/projects')) {
          return { ok: true, json: async () => [{ id: 'p-1', name: 'Hoffmann' }] }
        }
        if (u.includes('/api/besetzungen')) {
          return {
            ok: true,
            json: async () => [{ id: 'b-1', name: 'Stamm', singer_ids: [] }],
          }
        }
        return { ok: true, json: async () => [] }
      }),
    )
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('shows active project/besetzung/event with clear buttons', async () => {
    const user = userEvent.setup({ delay: 10 })
    queryClient.clear()
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <ActiveProvider>
            <InfoBar />
          </ActiveProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    )
    expect(await screen.findByText('Hoffmann')).toBeInTheDocument()
    expect(screen.getByText('Stamm')).toBeInTheDocument()
    expect(screen.getByText('Keiner')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Aktives Projekt zurücksetzen' }))
    expect(window.localStorage.getItem('chor-active-project')).toBeNull()
  })
})
