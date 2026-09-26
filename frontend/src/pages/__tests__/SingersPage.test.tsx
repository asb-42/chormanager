// M2 increment 1: singers list (search + table).
//
// Plan ref: M2 Frontend-CRUD, erste Seite. Ruft ``GET /api/singers``
// (M1) via TanStack Query; Suche filtert server-seitig.
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { queryClient } from '../../api/client'
import SingersPage from '../SingersPage'

const SINGERS = [
  { id: 's-1', full_name: 'Anna Muster', short_name: 'Anna', voice_group: 'Sopran 1' },
  { id: 's-2', full_name: 'Berta Beispiel', short_name: 'Berta', voice_group: 'Bass 2' },
]

function stubFetch() {
  const fetchMock = vi.fn(async (url: string) => ({
    ok: true,
    json: async () =>
      String(url).includes('search=Bert') ? [SINGERS[1]] : SINGERS,
  }))
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
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

describe('SingersPage', () => {
  beforeEach(() => {
    vi.unstubAllGlobals()
  })

  afterEach(() => {
    cleanup()
  })

  it('renders singer rows from the API', async () => {
    stubFetch()
    renderPage()
    expect(await screen.findByText('Anna Muster')).toBeInTheDocument()
    expect(screen.getByText('Berta Beispiel')).toBeInTheDocument()
  })

  it('filters server-side on search input', async () => {
    const fetchMock = stubFetch()
    renderPage()
    await screen.findByText('Anna Muster')
    await userEvent.type(screen.getByPlaceholderText('Suchen …'), 'Bert', {
      delay: 10,
    })
    await waitFor(
      () => {
        const urls = fetchMock.mock.calls.map(([url]) => String(url))
        expect(urls).toContain('/api/singers?search=Bert')
      },
      { timeout: 5000 },
    )
    expect(await screen.findByText('Berta Beispiel')).toBeInTheDocument()
  })

  it('shows an empty state without singers', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: true, json: async () => [] })),
    )
    renderPage()
    expect(await screen.findByText(/keine Sänger/i)).toBeInTheDocument()
  })
})
