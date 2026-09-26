// Aktiv-Kontext (Desktop-Parität: state.json mit
// last_active_project/event/besetzung + Info-Bar).
// Web: localStorage (Client-Kontext, Single-User wie Desktop).
import { createContext, useCallback, useContext, useState } from 'react'
import type { ReactNode } from 'react'

const KEYS = {
  project: 'chor-active-project',
  besetzung: 'chor-active-besetzung',
  event: 'chor-active-event',
} as const

export interface ActiveState {
  projectId: string | null
  besetzungId: string | null
  eventId: string | null
  setProject: (id: string | null) => void
  setBesetzung: (id: string | null) => void
  setEvent: (id: string | null) => void
  clearProject: () => void
  clearBesetzung: () => void
  clearEvent: () => void
}

const ActiveContext = createContext<ActiveState | null>(null)

function read(key: string): string | null {
  return window.localStorage.getItem(key)
}

export function ActiveProvider({ children }: { children: ReactNode }) {
  const [projectId, setProjectId] = useState<string | null>(() => read(KEYS.project))
  const [besetzungId, setBesetzungId] = useState<string | null>(() => read(KEYS.besetzung))
  const [eventId, setEventId] = useState<string | null>(() => read(KEYS.event))

  const store = useCallback((key: string, id: string | null) => {
    if (id === null) {
      window.localStorage.removeItem(key)
    } else {
      window.localStorage.setItem(key, id)
    }
  }, [])

  const setProject = useCallback(
    (id: string | null) => {
      store(KEYS.project, id)
      setProjectId(id)
    },
    [store],
  )
  const setBesetzung = useCallback(
    (id: string | null) => {
      store(KEYS.besetzung, id)
      setBesetzungId(id)
    },
    [store],
  )
  const setEvent = useCallback(
    (id: string | null) => {
      store(KEYS.event, id)
      setEventId(id)
    },
    [store],
  )

  return (
    <ActiveContext.Provider
      value={{
        projectId,
        besetzungId,
        eventId,
        setProject,
        setBesetzung,
        setEvent,
        clearProject: () => setProject(null),
        clearBesetzung: () => setBesetzung(null),
        clearEvent: () => setEvent(null),
      }}
    >
      {children}
    </ActiveContext.Provider>
  )
}

export function useActive(): ActiveState {
  const state = useContext(ActiveContext)
  if (!state) throw new Error('useActive braucht ActiveProvider')
  return state
}
