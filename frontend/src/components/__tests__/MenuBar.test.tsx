// Menüleiste nach Qt-Vorbild (Dropdowns statt nur Nav-Links).
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { queryClient } from '../../api/client'
import MenuBar from '../MenuBar'

function renderBar(path = '/') {
  queryClient.clear()
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>{<MenuBar />}</MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('MenuBar', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('opens dropdowns on click with working entries', async () => {
    const user = userEvent.setup({ delay: 10 })
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: true, json: async () => ({}) })),
    )
    renderBar()
    await user.click(screen.getByRole('button', { name: 'Datei' }))
    expect(
      screen.getByRole('menuitem', { name: 'Backup anlegen' }),
    ).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Hilfe' }))
    expect(
      screen.getByRole('menuitem', { name: 'Version prüfen' }),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('menuitem', { name: 'Backup anlegen' }),
    ).not.toBeInTheDocument()
  })

  it('closes on Escape', async () => {
    const user = userEvent.setup({ delay: 10 })
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: true, json: async () => ({}) })),
    )
    renderBar()
    await user.click(screen.getByRole('button', { name: 'Ansicht' }))
    expect(screen.getByRole('menuitem', { name: 'Dunkel' })).toBeInTheDocument()
    await user.keyboard('{Escape}')
    expect(
      screen.queryByRole('menuitem', { name: 'Dunkel' }),
    ).not.toBeInTheDocument()
  })

  it('enables undo only in the formation editor', async () => {
    const user = userEvent.setup({ delay: 10 })
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: true, json: async () => ({}) })),
    )
    renderBar('/singers')
    await user.click(screen.getByRole('button', { name: 'Bearbeiten' }))
    expect(screen.getByRole('menuitem', { name: 'Rückgängig' })).toBeDisabled()
  })
})
