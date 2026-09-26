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

describe('computeAge/joinedDisplay', () => {
  it('computes full years and handles missing dates', async () => {
    const { computeAge, joinedDisplay } = await import('../../api/client')
    expect(computeAge(null)).toBeNull()
    expect(computeAge('')).toBeNull()
    const age = computeAge('2012-01-01') as number
    expect(age).toBeGreaterThanOrEqual(13)
    expect(age).toBeLessThanOrEqual(15)
    expect(computeAge('not-a-date')).toBeNull()
    expect(joinedDisplay(2024, 9)).toBe('09/2024')
    expect(joinedDisplay(2024, null)).toBe('2024')
    expect(joinedDisplay(null, null)).toBe('')
  })
})
