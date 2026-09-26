// M3.2: editor search highlight spec (mocked API).
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { queryClient } from '../../api/client'
import FormationEditorPage from '../FormationEditorPage'

const DOC = {
  id: 'f-1',
  name: 'Probe',
  rows: 4,
  cols: 5,
  staggered: false,
  voicing_config: [],
  singers: [
    { singer_id: 's-2', name: 'Berta B', voice_group: 'Bass 2', height: 0, affinity: '' },
  ],
  placed: [
    {
      singer: { singer_id: 's-1', name: 'Anna Muster', voice_group: 'Sopran 1', height: 0, affinity: '' },
      row: 0,
      col: 0,
    },
  ],
  metadata: {},
  event_id: 'e-1',
}

describe('FormationEditorPage search', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('highlights matching tiles', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        if (String(url).includes('/api/formations/f-1')) {
          return { ok: true, json: async () => DOC }
        }
        return { ok: true, json: async () => [] }
      }),
    )
    queryClient.clear()
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/formations/f-1']}>
          <Routes>
            <Route path="/formations/:id" element={<FormationEditorPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    )
    await screen.findByText('Anna Muster')
    const user = userEvent.setup({ delay: 10 })
    await user.type(screen.getByPlaceholderText('Suchen …'), 'anna')
    const tile = await screen.findByText('Anna Muster')
    expect(
      tile.closest('[data-tile]')?.getAttribute('data-highlight'),
    ).toBe('true')
  })
})
