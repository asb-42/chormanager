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
  const response = await fetch(path, {
    ...init,
    headers: { ...authHeaders(), ...init?.headers },
  })
  if (!response.ok) {
    throw new Error(`API ${response.status}: ${path}`)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return response.json() as Promise<T>
}

function authHeaders(): Record<string, string> {
  const token =
    localStorage.getItem('chor-api-token') ??
    import.meta.env.VITE_API_TOKEN ??
    ''
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export function fetchSingers(search: string): Promise<Singer[]> {
  const query = search ? `?search=${encodeURIComponent(search)}` : ''
  return api<Singer[]>(`/api/singers${query}`)
}

export interface VoiceGroup {
  id: string
  short?: string | null
  order?: number | null
  color_light: string
  color_dark: string
}

export function fetchVoiceGroups(): Promise<VoiceGroup[]> {
  return api<VoiceGroup[]>('/api/config/voice-groups')
}

export interface SingerInput {
  full_name: string
  short_name?: string
  voice_group?: string
  height?: number
  email?: string
}

export function createSinger(input: SingerInput): Promise<Singer> {
  return api<Singer>('/api/singers', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
}

export function updateSinger(
  id: string,
  input: Partial<SingerInput>,
): Promise<Singer> {
  return api<Singer>(`/api/singers/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
}

export function deleteSinger(id: string): Promise<void> {
  return api<void>(`/api/singers/${id}`, { method: 'DELETE' })
}

export interface Besetzung {
  id: string
  name: string
  project_id?: string | null
  singer_ids: string[]
}

export interface BesetzungInput {
  name: string
  project_id?: string
  singer_ids: string[]
}

export function fetchBesetzungen(projectId?: string): Promise<Besetzung[]> {
  const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''
  return api<Besetzung[]>(`/api/besetzungen${query}`)
}

export function createBesetzung(input: BesetzungInput): Promise<Besetzung> {
  return api<Besetzung>('/api/besetzungen', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
}

export function deleteBesetzung(id: string): Promise<void> {
  return api<void>(`/api/besetzungen/${id}`, { method: 'DELETE' })
}

export interface RepertoireEntry {
  id: string
  title: string
  composer?: string | null
  project_id?: string | null
}

export interface RepertoireInput {
  title: string
  composer?: string
  project_id?: string
}

export function fetchRepertoire(projectId?: string): Promise<RepertoireEntry[]> {
  const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''
  return api<RepertoireEntry[]>(`/api/repertoire${query}`)
}

export function createRepertoire(input: RepertoireInput): Promise<RepertoireEntry> {
  return api<RepertoireEntry>('/api/repertoire', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
}

export function deleteRepertoire(id: string): Promise<void> {
  return api<void>(`/api/repertoire/${id}`, { method: 'DELETE' })
}

export interface AvailabilityMatrixEntry {
  singer_id: string
  full_name: string
  short_name?: string | null
  voice_group?: string | null
  status: string
}

export interface AvailabilityMatrix {
  event_id: string
  entries: AvailabilityMatrixEntry[]
}

export function fetchAvailabilityMatrix(
  eventId: string,
): Promise<AvailabilityMatrix> {
  return api<AvailabilityMatrix>(`/api/events/${eventId}/availability`)
}

export interface AvailabilityUpdate {
  singer_id: string
  status: string
}

export function putAvailabilityBulk(
  eventId: string,
  entries: AvailabilityUpdate[],
): Promise<{ event_id: string; updated: number }> {
  return api(`/api/events/${eventId}/availability`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ entries }),
  })
}

export interface EventItem {
  id: string
  name: string
  date: string
  event_type: string
  location?: string | null
  description?: string | null
  project_id?: string | null
  yes_count: number
  conditional_count: number
}

export interface Project {
  id: string
  name: string
  description?: string | null
  is_active?: number | null
  spielzeit?: string | null
}

export interface ProjectSummaryEvent {
  event_id: string
  name: string
  date: string
  yes: number
  conditional: number
}

export interface ProjectSummary {
  project_id: string
  events: ProjectSummaryEvent[]
  by_voice_group: Record<string, Record<string, number>>
}

export interface EventFilter {
  project_id?: string
  search?: string
  event_type?: string
}

export function fetchEvents(filter: EventFilter): Promise<EventItem[]> {
  const params = new URLSearchParams()
  if (filter.project_id) params.set('project_id', filter.project_id)
  if (filter.search) params.set('search', filter.search)
  if (filter.event_type) params.set('event_type', filter.event_type)
  const query = params.toString() ? `?${params.toString()}` : ''
  return api<EventItem[]>(`/api/events${query}`)
}

export function fetchProjects(): Promise<Project[]> {
  return api<Project[]>('/api/projects')
}

export function fetchProjectSummary(id: string): Promise<ProjectSummary> {
  return api<ProjectSummary>(`/api/projects/${id}/summary`)
}

export function formatDate(iso: string): string {
  const part = (iso || '').slice(0, 10).split('-')
  if (part.length !== 3) return iso || ''
  return `${part[2]}.${part[1]}.${part[0]}`
}

export const queryClient = new QueryClient()
