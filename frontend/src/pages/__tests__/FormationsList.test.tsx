// M3 proper: formations list page spec.
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { queryClient } from '../../api/client'
import FormationsPage from '../FormationsPage'

describe('FormationsPage', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('renders formations with links to the editor', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        json: async () => [
          { id: 'f-1', name: 'Probe A', rows: 4, cols: 5, event_id: 'e-1', updated_at: '2026-01-01' },
        ],
      })),
    )
    queryClient.clear()
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <FormationsPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    const link = await screen.findByRole('link', { name: 'Probe A' })
    expect(link.getAttribute('href')).toBe('/formations/f-1')
  })
})
