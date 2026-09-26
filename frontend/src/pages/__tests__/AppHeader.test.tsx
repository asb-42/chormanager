// Header (statt Menüleiste): App-Name links, Theme rechts.
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { queryClient } from '../../api/client'
import App from '../../App'

describe('App header', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
    document.documentElement.classList.remove('dark')
  })

  it('shows the app name left and theme toggle right, no menu bar', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: true, json: async () => [] })),
    )
    queryClient.clear()
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/']}>
          <App />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    expect(screen.getByText('Chormanager')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Dunkel' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Datei' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Bearbeiten' })).not.toBeInTheDocument()
  })
})
