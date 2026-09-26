// Design-Fundament: geteilte UI-Primitives (eine Sprache).
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Button, EmptyState, Field, PageHeader, Th, Td } from '../ui'

describe('Button', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders variants with accessible names', () => {
    render(
      <>
        <Button variant="primary">Speichern</Button>
        <Button variant="danger">Löschen</Button>
      </>,
    )
    expect(screen.getByRole('button', { name: 'Speichern' })).toHaveClass('bg-blue-700')
    expect(screen.getByRole('button', { name: 'Löschen' })).toHaveClass('bg-red-700')
  })

  it('forwards disabled and click', async () => {
    const user = userEvent.setup({ delay: 10 })
    const onClick = vi.fn()
    render(
      <Button disabled onClick={onClick}>
        Blockiert
      </Button>,
    )
    const button = screen.getByRole('button', { name: 'Blockiert' })
    expect(button).toBeDisabled()
    await user.click(button)
    expect(onClick).not.toHaveBeenCalled()
  })
})

describe('Field', () => {
  afterEach(() => {
    cleanup()
  })

  it('associates label and control', () => {
    render(
      <Field label="Name">
        <input defaultValue="x" aria-label="Name" />
      </Field>,
    )
    expect(screen.getByLabelText('Name')).toBeInTheDocument()
  })
})

describe('PageHeader', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders title and actions with separator', () => {
    render(
      <PageHeader title="Sänger" actions={<button type="button">Neu</button>} />,
    )
    expect(screen.getByRole('heading', { name: 'Sänger' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Neu' })).toBeInTheDocument()
  })
})

describe('Th/Td', () => {
  afterEach(() => {
    cleanup()
  })

  it('styles header cells uppercase gray, body cells plain', () => {
    render(
      <table>
        <thead>
          <tr>
            <Th>Name</Th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <Td>Anna</Td>
          </tr>
        </tbody>
      </table>,
    )
    const th = screen.getByText('Name')
    expect(th.tagName).toBe('TH')
    expect(th).toHaveClass('uppercase')
    expect(th).toHaveClass('text-gray-500')
    expect(screen.getByText('Anna').tagName).toBe('TD')
  })
})

describe('EmptyState', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders text and action', () => {
    render(
      <EmptyState
        text="Keine Sänger gefunden."
        action={<a href="/wizard/singer">Anlegen</a>}
      />,
    )
    expect(screen.getByText('Keine Sänger gefunden.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Anlegen' })).toBeInTheDocument()
  })
})
