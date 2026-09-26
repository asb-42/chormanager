// Sweep 2/6 Sänger: Qt-Spalten, Stimmgruppen-/Status-Filter,
// Sortierung, Duplizieren.
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { queryClient } from '../../api/client'
import SingersPage from '../SingersPage'

let singers = [
  { id: 's-1', full_name: 'Anna Muster', short_name: 'Anna', birth_date: '2012-03-01', voice_group: 'Sopran 1', height: 150, email: 'a@x.org', phone: null, street: 'Weg 1', postal_code: '1', city: 'Ort', gender: null, guardian1: null, guardian1_phone: null, guardian2: null, guardian2_phone: null, social_contacts: null, joined_year: 2024, joined_month: 9, left_year: null, left_month: null, affinity_uuid: '' },
  { id: 's-2', full_name: 'Berta Alt', short_name: 'Berta', birth_date: '1990-01-01', voice_group: 'Bass 2', height: 185, email: null, phone: null, street: null, postal_code: null, city: null, gender: null, guardian1: null, guardian1_phone: null, guardian2: null, guardian2_phone: null, social_contacts: null, joined_year: 2020, joined_month: null, left_year: 2025, left_month: null, affinity_uuid: '' },
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
  window.localStorage.clear()
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <SingersPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('SingersPage Tabelle', () => {
  beforeEach(() => {
    vi.unstubAllGlobals()
    window.localStorage.clear()
    singers = [
      { id: 's-1', full_name: 'Anna Muster', short_name: 'Anna', birth_date: '2012-03-01', voice_group: 'Sopran 1', height: 150, email: 'a@x.org', phone: null, street: 'Weg 1', postal_code: '1', city: 'Ort', gender: null, guardian1: null, guardian1_phone: null, guardian2: null, guardian2_phone: null, social_contacts: null, joined_year: 2024, joined_month: 9, left_year: null, left_month: null, affinity_uuid: '' },
      { id: 's-2', full_name: 'Berta Alt', short_name: 'Berta', birth_date: '1990-01-01', voice_group: 'Bass 2', height: 185, email: null, phone: null, street: null, postal_code: null, city: null, gender: null, guardian1: null, guardian1_phone: null, guardian2: null, guardian2_phone: null, social_contacts: null, joined_year: 2020, joined_month: null, left_year: 2025, left_month: null, affinity_uuid: '' },
    ]
  })

  afterEach(() => {
    cleanup()
  })

  it('renders Qt columns', async () => {
    stubFetch()
    renderPage()
    expect(await screen.findByText('Anna Muster')).toBeInTheDocument()
    for (const header of [/Geburtsdatum/, /Ort/, /Beitritt/, /UUID/]) {
      expect(screen.getByText(header, { selector: 'th' })).toBeInTheDocument()
    }
    for (const header of [/Alter/, /Größe/]) {
      expect(screen.getByRole('button', { name: header })).toBeInTheDocument()
    }
    expect(screen.getByText('09/2024')).toBeInTheDocument()
  })

  it('filters by voice group and status', async () => {
    const user = userEvent.setup({ delay: 10 })
    stubFetch()
    renderPage()
    await screen.findByText('Anna Muster')
    await user.selectOptions(screen.getByLabelText('Stimmgruppe'), 'Bass 2')
    await waitFor(() => {
      expect(screen.queryByText('Anna Muster')).not.toBeInTheDocument()
    })
    await user.selectOptions(screen.getByLabelText('Stimmgruppe'), '')
    await user.selectOptions(screen.getByLabelText('Mitglieder'), 'minor')
    await waitFor(() => {
      expect(screen.getByText('Anna Muster')).toBeInTheDocument()
      expect(screen.queryByText('Berta Alt')).not.toBeInTheDocument()
    })
  })

  it('sorts by age and height client-side', async () => {
    const user = userEvent.setup({ delay: 10 })
    stubFetch()
    renderPage()
    await screen.findByText('Anna Muster')
    await user.selectOptions(screen.getByLabelText('Sortieren'), 'height-desc')
    const rows = await screen.findAllByRole('row')
    expect(rows[1]).toHaveTextContent('Berta Alt')
  })

  it('duplicates with (Kopie)', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage()
    await screen.findByText('Anna Muster')
    const row = screen.getByText('Anna Muster').closest('tr') as HTMLElement
    await user.click(within(row).getByRole('button', { name: 'Duplizieren' }))
    await waitFor(() => {
      expect(
        calls.some(
          (c) =>
            c.method === 'POST' &&
            (c.body as { full_name: string }).full_name === 'Anna Muster (Kopie)',
        ),
      ).toBe(true)
    })
  })
  it('sorts client-side by select and header', async () => {
    const user = userEvent.setup({ delay: 10 })
    stubFetch()
    renderPage()
    await screen.findByText('Anna Muster')
    let rows = await screen.findAllByRole('row')
    expect(rows[1]).toHaveTextContent('Anna Muster')
    await user.selectOptions(screen.getByLabelText('Sortieren'), 'height-desc')
    rows = await screen.findAllByRole('row')
    expect(rows[1]).toHaveTextContent('Berta Alt')
    await user.click(screen.getByRole('button', { name: /Größe/ }))
    rows = await screen.findAllByRole('row')
    expect(rows[1]).toHaveTextContent('Anna Muster')
  })
})
