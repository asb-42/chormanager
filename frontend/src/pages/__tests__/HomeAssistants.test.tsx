// Startseite: Assistenten-Karten wie im Qt (Aufgaben-Ansicht).
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { queryClient } from '../../api/client'
import App from '../../App'

describe('HomePage assistants', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('links the three assistant workflows (no placeholder)', async () => {
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
    expect(screen.queryByText(/M2-Aufbau/)).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Eine Aufstellung für einen Auftritt planen/ })).toHaveAttribute(
      'href',
      '/wizard/formation',
    )
    expect(screen.getByRole('link', { name: /Einen neuen Termin eintragen/ })).toHaveAttribute(
      'href',
      '/wizard/event',
    )
    expect(screen.getByRole('link', { name: /Zusagen und Absagen für einen Termin erfassen/ })).toHaveAttribute(
      'href',
      '/wizard/availability',
    )
    expect(screen.getByRole('link', { name: /Ein Chormitglied aufnehmen/ })).toHaveAttribute(
      'href',
      '/wizard/singer',
    )
  })
})
