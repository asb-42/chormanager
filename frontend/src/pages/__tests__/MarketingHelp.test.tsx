// Marketing (Selbstdarstellung) + Hilfe Specs.
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { queryClient } from '../../api/client'
import HelpPage from '../HelpPage'
import MarketingPage from '../MarketingPage'

function renderPage(page: React.ReactNode) {
  queryClient.clear()
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{page}</MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('MarketingPage', () => {
  beforeEach(() => {
    vi.unstubAllGlobals()
  })

  afterEach(() => {
    cleanup()
  })

  it('loads, edits and saves the text', async () => {
    const user = userEvent.setup({ delay: 10 })
    const calls: Array<{ method: string; body?: unknown }> = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_url: string, init?: RequestInit) => {
        const method = init?.method ?? 'GET'
        let body: unknown
        try {
          body = init?.body ? JSON.parse(String(init.body)) : undefined
        } catch {
          body = undefined
        }
        calls.push({ method, body })
        if (method === 'PUT') {
          return { ok: true, json: async () => ({ id: 'd-1', content: (body as { content: string }).content }) }
        }
        return { ok: true, json: async () => ({ id: 'd-1', content: 'Alt' }) }
      }),
    )
    renderPage(<MarketingPage />)
    const box = await screen.findByLabelText('Selbstdarstellung')
    expect((box as HTMLTextAreaElement).value).toBe('Alt')
    await user.clear(box)
    await user.type(box, 'Neu')
    await user.click(screen.getByRole('button', { name: 'Speichern' }))
    await waitFor(() => {
      expect(
        calls.some(
          (c) => c.method === 'PUT' && (c.body as { content: string }).content === 'Neu',
        ),
      ).toBe(true)
    })
    expect(await screen.findByText('Gespeichert.')).toBeInTheDocument()
  })
})

describe('HelpPage', () => {
  beforeEach(() => {
    vi.unstubAllGlobals()
  })

  afterEach(() => {
    cleanup()
  })

  it('shows versions and a check timestamp', async () => {
    const user = userEvent.setup({ delay: 10 })
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: true, json: async () => ({ version: '1.2.3' }) })),
    )
    renderPage(<HelpPage />)
    expect(await screen.findByText(/1\.2\.3/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Version prüfen' }))
    expect(await screen.findByText(/Geprüft um/)).toBeInTheDocument()
  })
})
