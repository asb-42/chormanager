// M4: backup list/create/restore/delete UI.
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { queryClient } from '../../api/client'
import BackupPage from '../BackupPage'

let backups = [{ id: 'chor-backup_1.db', size: 1234, modified_at: '2026-01-01' }]

function stubFetch() {
  const calls: Array<{ method: string; url: string }> = []
  const mock = vi.fn(async (url: string, init?: RequestInit) => {
    const method = init?.method ?? 'GET'
    const u = String(url)
    calls.push({ method, url: u })
    if (u.endsWith('/api/backup') && method === 'GET') {
      return { ok: true, json: async () => backups }
    }
    if (u.endsWith('/api/backup') && method === 'POST') {
      backups.push({ id: 'chor-backup_2.db', size: 10, modified_at: '2026-01-02' })
      return { ok: true, status: 201, json: async () => backups[1] }
    }
    if (u.includes('/restore') && method === 'POST') {
      return { ok: true, json: async () => ({ restored: 'x' }) }
    }
    if (method === 'DELETE') {
      const id = u.split('/').pop() as string
      backups = backups.filter((b) => b.id !== id)
      return { ok: true, status: 204, json: async () => ({}) }
    }
    return { ok: false, status: 404, json: async () => ({}) }
  })
  vi.stubGlobal('fetch', mock)
  return { mock, calls }
}

function renderPage() {
  queryClient.clear()
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <BackupPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('BackupPage', () => {
  beforeEach(() => {
    vi.unstubAllGlobals()
    backups = [{ id: 'chor-backup_1.db', size: 1234, modified_at: '2026-01-01' }]
  })

  afterEach(() => {
    cleanup()
  })

  it('renders backups and creates one', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage()
    expect(await screen.findByText('chor-backup_1.db')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Backup anlegen' }))
    await waitFor(() => {
      expect(
        calls.some((c) => c.method === 'POST' && c.url.endsWith('/api/backup')),
      ).toBe(true)
    })
    expect(await screen.findByText('chor-backup_2.db')).toBeInTheDocument()
  })

  it('restores after confirm', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage()
    await screen.findByText('chor-backup_1.db')
    await user.click(screen.getByRole('button', { name: 'Wiederherstellen' }))
    await user.click(screen.getByRole('button', { name: 'Wirklich wiederherstellen' }))
    await waitFor(() => {
      expect(
        calls.some(
          (c) => c.method === 'POST' && c.url.includes('/restore'),
        ),
      ).toBe(true)
    })
    expect(await screen.findByText('Wiederhergestellt.')).toBeInTheDocument()
  })

  it('deletes after confirm', async () => {
    const user = userEvent.setup({ delay: 10 })
    const { calls } = stubFetch()
    renderPage()
    await screen.findByText('chor-backup_1.db')
    await user.click(screen.getByRole('button', { name: 'Löschen' }))
    await user.click(screen.getByRole('button', { name: 'Wirklich löschen' }))
    await waitFor(() => {
      expect(
        calls.some(
          (c) => c.method === 'DELETE' && c.url.includes('/api/backup/'),
        ),
      ).toBe(true)
    })
    await waitFor(() => {
      expect(screen.queryByText('chor-backup_1.db')).not.toBeInTheDocument()
    })
  })

  it('shows the backend detail on failure', async () => {
    const user = userEvent.setup({ delay: 10 })
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_url: string, init?: RequestInit) => {
        if ((init?.method ?? 'GET') === 'POST') {
          return {
            ok: false,
            status: 400,
            json: async () => ({ detail: 'Nur für SQLite-Dateien' }),
          }
        }
        return { ok: true, json: async () => backups }
      }),
    )
    renderPage()
    await screen.findByText('chor-backup_1.db')
    await user.click(screen.getByRole('button', { name: 'Backup anlegen' }))
    expect(await screen.findByText(/Nur für SQLite-Dateien/)).toBeInTheDocument()
  })
})
