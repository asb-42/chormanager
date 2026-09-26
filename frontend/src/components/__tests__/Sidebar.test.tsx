// Sidebar-Navigation (Qt-nah): Hauptpills mit Icons in fester
// Reihenfolge, unten Text-Links, mobil einklappbar.
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import Sidebar from '../Sidebar'

const MAIN_ORDER = [
  'Aufgaben',
  'Projekte',
  'Sänger',
  'Besetzung',
  'Termine',
  'Aufstellung',
  'Repertoire',
  'Marketing',
]

const BOTTOM_LINKS = ['Backup', 'Konfiguration', 'Hilfe', 'About']

function renderSidebar(open = true) {
  render(
    <MemoryRouter initialEntries={['/']}>
      <Sidebar open={open} onNavigate={() => {}} />
    </MemoryRouter>,
  )
}

describe('Sidebar', () => {
  afterEach(() => {
    cleanup()
  })

  it('lists main items with icons in Qt order', () => {
    renderSidebar()
    const links = screen
      .getAllByRole('link')
      .map((link) => link.textContent ?? '')
    const main = links.filter((text) =>
      MAIN_ORDER.some((label) => text.includes(label)),
    )
    expect(main).toHaveLength(MAIN_ORDER.length)
    let lastIndex = -1
    for (const label of MAIN_ORDER) {
      const index = main.findIndex((text) => text.includes(label))
      expect(index).toBeGreaterThan(lastIndex)
      lastIndex = index
    }
    // Icons statt Emoji/Text-Only.
    expect(document.querySelectorAll('nav svg').length).toBeGreaterThanOrEqual(
      MAIN_ORDER.length,
    )
  })

  it('routes to the right targets', () => {
    renderSidebar()
    expect(screen.getByRole('link', { name: /Aufgaben/ })).toHaveAttribute('href', '/')
    expect(screen.getByRole('link', { name: /Termine/ })).toHaveAttribute('href', '/events')
    expect(screen.getByRole('link', { name: /Aufstellung/ })).toHaveAttribute('href', '/formations')
    for (const label of BOTTOM_LINKS) {
      expect(
        screen.getByRole('link', { name: new RegExp(label) }),
      ).toBeInTheDocument()
    }
    expect(screen.getByRole('link', { name: /About/ })).toHaveAttribute('href', '/about')
  })

  it('hides content when closed (mobile drawer)', () => {
    const onNavigate = vi.fn()
    render(
      <MemoryRouter initialEntries={['/']}>
        <Sidebar open={false} onNavigate={onNavigate} />
      </MemoryRouter>,
    )
    expect(screen.queryByRole('link', { name: /Sänger/ })).not.toBeInTheDocument()
  })

  it('notifies on navigation (drawer closes on mobile)', async () => {
    const user = userEvent.setup({ delay: 10 })
    const onNavigate = vi.fn()
    render(
      <MemoryRouter initialEntries={['/']}>
        <Sidebar open={true} onNavigate={onNavigate} />
      </MemoryRouter>,
    )
    await user.click(screen.getByRole('link', { name: /Sänger/ }))
    expect(onNavigate).toHaveBeenCalledTimes(1)
  })
})
