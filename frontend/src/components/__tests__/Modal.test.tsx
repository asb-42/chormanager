// Modales Dialog-System (statt Inline-Karten am Seitenende).
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Modal } from '../Modal'

describe('Modal', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders centered with overlay and label', () => {
    render(
      <Modal label="Sänger anlegen" onClose={() => {}}>
        <p>Inhalt</p>
      </Modal>,
    )
    expect(screen.getByRole('dialog', { name: 'Sänger anlegen' })).toBeInTheDocument()
    expect(screen.getByText('Inhalt')).toBeInTheDocument()
  })

  it('closes on Escape and overlay click, not on content click', async () => {
    const user = userEvent.setup({ delay: 10 })
    const onClose = vi.fn()
    render(
      <Modal label="T" onClose={onClose}>
        <p>Inhalt</p>
      </Modal>,
    )
    await user.click(screen.getByText('Inhalt'))
    expect(onClose).not.toHaveBeenCalled()
    await user.keyboard('{Escape}')
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('focuses the first field on open', async () => {
    render(
      <Modal label="T" onClose={() => {}}>
        <label>
          Name
          <input />
        </label>
      </Modal>,
    )
    expect(await screen.findByLabelText('Name')).toHaveFocus()
  })
})
