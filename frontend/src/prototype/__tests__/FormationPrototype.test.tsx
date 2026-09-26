// M3-Spike: smoke test for the throwaway prototype.
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it } from 'vitest'
import FormationPrototype from '../FormationPrototype'

describe('FormationPrototype', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders 20 pool singers and an empty grid', () => {
    render(<FormationPrototype />)
    expect(screen.getByText('Sänger 1 (Sopran 1)')).toBeInTheDocument()
    expect(screen.getByText('Sänger 20 (Alt 2)')).toBeInTheDocument()
    expect(screen.getByText(/0 platziert, 20 im Pool/)).toBeInTheDocument()
  })

  it('toggles stagger mode', async () => {
    const user = userEvent.setup({ delay: 10 })
    render(<FormationPrototype />)
    const toggle = screen.getByRole('checkbox')
    expect(toggle).not.toBeChecked()
    await user.click(toggle)
    expect(toggle).toBeChecked()
  })
})
