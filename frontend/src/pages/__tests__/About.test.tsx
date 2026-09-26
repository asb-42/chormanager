// About-Seite (Qt: Hilfe → Über).
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { queryClient } from '../../api/client'
import AboutPage from '../AboutPage'

describe('AboutPage', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('shows app meta and backend version', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: true, json: async () => ({ version: '9.9' }) })),
    )
    queryClient.clear()
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AboutPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    expect(await screen.findByRole('heading', { name: /Über ChorManager/ })).toBeInTheDocument()
    expect(await screen.findByText(/9\.9/)).toBeInTheDocument()
  })
})
