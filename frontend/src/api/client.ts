import { QueryClient } from '@tanstack/react-query'

export interface Singer {
  id: string
  full_name: string
  short_name?: string | null
  voice_group?: string | null
  height?: number | null
  email?: string | null
  affinity_uuid?: string | null
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init)
  if (!response.ok) {
    throw new Error(`API ${response.status}: ${path}`)
  }
  return response.json() as Promise<T>
}

export function fetchSingers(search: string): Promise<Singer[]> {
  const query = search ? `?search=${encodeURIComponent(search)}` : ''
  return api<Singer[]>(`/api/singers${query}`)
}

export const queryClient = new QueryClient()
