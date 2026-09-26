// FormationsPage: Neu-Dialog + Wegweiser statt Sackgasse.
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useParams } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { queryClient } from '../../api/client'
import FormationsPage from '../FormationsPage'

function EditorStub() {
  const params = useParams<{ id?: string }>()
  return <p>Editor {params.id}</p>
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
    if (u.endsWith('/api/formations') && method === 'POST') {
      return { ok: true, status: 201, json: async () => ({ id: 'f-9', ...(body as object) }) }
    }
    if (u.endsWith('/api/formations')) {
      return { ok: true, json: async () => [] }
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
      <MemoryRouter initialEntries={['/formations']}>
        <Routes>
          <Route path="/formations" element={<FormationsPage />} />
          <Route path="/formations/:id" element={<EditorStub />} />
          <Route path="/wizard/formation" element={<p>Assistent</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('FormationsPage empty state', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('guides to Neu and Assistent', async () => {
    stubFetch()
    renderPage()
    expect(await screen.findByText(/Keine Aufstellungen vorhanden/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Neu' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Assistent/ })).toHaveAttribute(
      'href',
      '/wizard/formation',
    )
  })

  it('creates and navigates to the editor', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage()
    await screen.findByText(/Keine Aufstellungen vorhanden/)
    await user.click(screen.getByRole('button', { name: 'Neu' }))
    await user.type(screen.getByLabelText('Name'), 'Sommer')
    await user.click(screen.getByRole('button', { name: 'Anlegen' }))
    await waitFor(() => {
      expect(
        calls.some(
          (c) =>
            c.method === 'POST' &&
            c.url.endsWith('/api/formations') &&
            (c.body as { name: string }).name === 'Sommer',
        ),
      ).toBe(true)
    })
    expect(await screen.findByText('Editor f-9')).toBeInTheDocument()
  })
})
