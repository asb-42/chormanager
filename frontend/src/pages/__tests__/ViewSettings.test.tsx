// Ansicht (Hell/Dunkel) + Konfiguration (Settings) Specs.
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { queryClient } from '../../api/client'
import App from '../../App'
import SettingsPage from '../SettingsPage'

function renderApp(path: string, page: React.ReactNode) {
  queryClient.clear()
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>{page}</MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Ansicht Hell/Dunkel', () => {
  beforeEach(() => {
    vi.unstubAllGlobals()
    window.localStorage.clear()
    document.documentElement.classList.remove('dark')
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: true, json: async () => [] })),
    )
  })

  afterEach(() => {
    cleanup()
    document.documentElement.classList.remove('dark')
  })

  it('toggles dark class and persists', async () => {
    const user = userEvent.setup({ delay: 10 })
    renderApp('/', <App />)
    await user.click(screen.getByRole('button', { name: 'Dunkel' }))
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(window.localStorage.getItem('chor-theme')).toBe('dark')
    await user.click(screen.getByRole('button', { name: 'Hell' }))
    expect(document.documentElement.classList.contains('dark')).toBe(false)
    expect(window.localStorage.getItem('chor-theme')).toBe('light')
  })
})

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.unstubAllGlobals()
    window.localStorage.clear()
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: true, json: async () => ({ version: '9.9' }) })),
    )
  })

  afterEach(() => {
    cleanup()
  })

  it('saves and clears the API token', async () => {
    const user = userEvent.setup({ delay: 10 })
    renderApp('/settings', <SettingsPage />)
    await user.type(screen.getByLabelText('API-Token'), 't-1')
    await user.click(screen.getByRole('button', { name: 'Token speichern' }))
    expect(window.localStorage.getItem('chor-api-token')).toBe('t-1')
    expect(await screen.findByText(/gespeichert/i)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Token löschen' }))
    expect(window.localStorage.getItem('chor-api-token')).toBeNull()
  })

  it('shows the backend version', async () => {
    renderApp('/settings', <SettingsPage />)
    expect(await screen.findByText(/9\.9/)).toBeInTheDocument()
  })
})
