// Vollständiges Sänger-Formular (Desktop-Parität, ~20 Felder).
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { queryClient } from '../../api/client'
import SingersPage from '../SingersPage'

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
    if (u.includes('/api/config/voice-groups')) {
      return { ok: true, json: async () => GROUPS }
    }
    if (method === 'POST' && u.endsWith('/api/singers')) {
      return { ok: true, status: 201, json: async () => ({ id: 's-9', ...(body as object) }) }
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
      <MemoryRouter>
        <SingersPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('SingerDialog full model', () => {
  beforeEach(() => {
    vi.unstubAllGlobals()
    window.localStorage.clear()
  })

  afterEach(() => {
    cleanup()
  })

  it('shows all sections and fields', async () => {
    const user = userEvent.setup({ delay: 10 })
    stubFetch()
    renderPage()
    await user.click(screen.getByRole('button', { name: 'Neu' }))
    for (const label of [
      'Name', 'Kurzname', 'Geburtsdatum', 'Geschlecht',
      'E-Mail', 'Telefon', 'Kontakte', 'Straße', 'PLZ', 'Ort',
      'Stimmgruppe', 'Größe (cm)', 'Eintritt Jahr', 'Eintritt Monat',
      'Austritt Jahr', 'Austritt Monat', 'Sitzpartner-ID',
      'Sorgeberechtigt 1', 'Telefon 1', 'Sorgeberechtigt 2', 'Telefon 2',
    ]) {
      expect(screen.getByLabelText(label)).toBeInTheDocument()
    }
  })

  it('submits all fields', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage()
    await user.click(screen.getByRole('button', { name: 'Neu' }))
    await user.type(screen.getByLabelText('Name'), 'Max Muster')
    await user.type(screen.getByLabelText('Telefon'), '0123')
    await user.type(screen.getByLabelText('Straße'), 'Weg 1')
    await user.type(screen.getByLabelText('Sorgeberechtigt 1'), 'Mutter')
    await user.click(screen.getByRole('button', { name: 'Speichern' }))
    await waitFor(() => {
      const post = calls.find((c) => c.method === 'POST')
      expect(post).toBeDefined()
      expect(post?.body).toMatchObject({
        full_name: 'Max Muster',
        phone: '0123',
        street: 'Weg 1',
        guardian1: 'Mutter',
      })
    })
  })

  it('sorts by column header click', async () => {
    const user = userEvent.setup({ delay: 10 })
    const calls: string[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        calls.push(String(url))
        if (String(url).includes('/api/config/voice-groups')) {
          return { ok: true, json: async () => [] }
        }
        return {
          ok: true,
          json: async () => [
            { id: 's-1', full_name: 'Anna Muster', short_name: 'Anni', voice_group: 'Sopran 1' },
          ],
        }
      }),
    )
    renderPage()
    await screen.findByText('Anna Muster')
    await user.click(screen.getByRole('button', { name: /Stimmgruppe/ }))
    await waitFor(() => {
      expect(
        calls.some(
          (u) => u.includes('sort=voice_group') && !u.includes('direction=desc'),
        ),
      ).toBe(true)
    })
    await user.click(screen.getByRole('button', { name: /Stimmgruppe/ }))
    await waitFor(() => {
      expect(
        calls.some(
          (u) => u.includes('sort=voice_group') && u.includes('direction=desc'),
        ),
      ).toBe(true)
    })
  })
})
