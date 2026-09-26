// Fehler-Details vom Backend (detail-Feld) statt nur Status.
import { afterEach, describe, expect, it, vi } from 'vitest'

describe('api error details', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('meldet das Backend-detail', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Nur für SQLite-Dateien' }),
      })),
    )
    const { fetchBackups } = await import('../../api/client')
    await expect(fetchBackups()).rejects.toThrow('Nur für SQLite-Dateien')
  })

  it('fällt ohne Body auf Status+Pfad zurück', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('no json')
        },
      })),
    )
    const { fetchBackups } = await import('../../api/client')
    await expect(fetchBackups()).rejects.toThrow('API 500')
  })
})
