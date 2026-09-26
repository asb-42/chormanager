import { Link, NavLink, Route, Routes } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import AvailabilityPage from './pages/AvailabilityPage'
import BackupPage from './pages/BackupPage'
import BesetzungPage from './pages/BesetzungPage'
import EventsPage from './pages/EventsPage'
import FormationEditorPage from './pages/FormationEditorPage'
import FormationsPage from './pages/FormationsPage'
import ProjectsPage from './pages/ProjectsPage'
import RepertoirePage from './pages/RepertoirePage'
import SettingsPage from './pages/SettingsPage'
import SingersPage from './pages/SingersPage'
import WizardPage from './pages/WizardPage'
import HelpPage from './pages/HelpPage'
import MarketingPage from './pages/MarketingPage'
import { fetchVersion } from './api/client'

type Theme = 'light' | 'dark' | 'system'

function applyTheme(mode: Theme) {
  const dark =
    mode === 'dark' ||
    (mode === 'system' &&
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-color-scheme: dark)').matches)
  document.documentElement.classList.toggle('dark', dark)
}

function loadTheme(): Theme {
  const stored = window.localStorage.getItem('chor-theme')
  return stored === 'light' || stored === 'dark' ? stored : 'system'
}

function HomePage() {
  const cards = [
    {
      to: '/wizard/formation',
      title: 'Aufstellung planen',
      text: 'Projekt → Termin → Zusagen → Aufstellung',
    },
    {
      to: '/wizard/event',
      title: 'Termin eintragen',
      text: 'Neuer Termin mit Datum und Typ',
    },
    {
      to: '/wizard/singer',
      title: 'Chormitglied aufnehmen',
      text: 'Neues Chormitglied mit Stimmgruppe',
    },
  ]
  return (
    <section>
      <h1 className="text-xl font-semibold">ChorManager</h1>
      <p className="mt-2">Womit soll es losgehen?</p>
      <div className="mt-4 grid max-w-2xl gap-2">
        {cards.map((card) => (
          <Link key={card.to} to={card.to} className="rounded border p-4 hover:bg-gray-100 dark:hover:bg-gray-800">
            <span className="font-semibold">{card.title}</span>
            <span className="block text-sm text-gray-600">{card.text}</span>
          </Link>
        ))}
      </div>
    </section>
  )
}

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded px-3 py-1 ${isActive ? 'bg-gray-200 dark:bg-gray-700' : ''}`

export default function App() {
  const { data: version } = useQuery({
    queryKey: ['version'],
    queryFn: fetchVersion,
    retry: false,
    staleTime: Infinity,
  })
  const [theme, setTheme] = useState<Theme>(loadTheme)

  useEffect(() => {
    applyTheme(theme)
    window.localStorage.setItem('chor-theme', theme)
  }, [theme])

  return (
    <div className="mx-auto max-w-5xl p-4">
      <nav className="mb-6 flex flex-wrap items-center gap-2">
        <NavLink to="/" className={linkClass}>
          Start
        </NavLink>
        <NavLink to="/singers" className={linkClass}>
          Sänger
        </NavLink>
        <NavLink to="/events" className={linkClass}>
          Termine
        </NavLink>
        <NavLink to="/projects" className={linkClass}>
          Projekte
        </NavLink>
        <NavLink to="/besetzung" className={linkClass}>
          Besetzung
        </NavLink>
        <NavLink to="/repertoire" className={linkClass}>
          Repertoire
        </NavLink>
        <NavLink to="/availability" className={linkClass}>
          Verfügbarkeit
        </NavLink>
        <NavLink to="/wizard" className={linkClass}>
          Assistent
        </NavLink>
        <NavLink to="/backup" className={linkClass}>
          Backup
        </NavLink>
        <span className="ml-2 flex gap-1 text-sm" role="group" aria-label="Ansicht">
          <button
            type="button"
            onClick={() => setTheme('light')}
            aria-pressed={theme === 'light'}
            className={`rounded px-2 py-1 ${theme === 'light' ? 'bg-gray-200 dark:bg-gray-700' : ''}`}
          >
            Hell
          </button>
          <button
            type="button"
            onClick={() => setTheme('dark')}
            aria-pressed={theme === 'dark'}
            className={`rounded px-2 py-1 ${theme === 'dark' ? 'bg-gray-200 dark:bg-gray-700' : ''}`}
          >
            Dunkel
          </button>
          <button
            type="button"
            onClick={() => setTheme('system')}
            aria-pressed={theme === 'system'}
            className={`rounded px-2 py-1 ${theme === 'system' ? 'bg-gray-200 dark:bg-gray-700' : ''}`}
          >
            Auto
          </button>
        </span>
        <NavLink to="/settings" className={linkClass}>
          Konfiguration
        </NavLink>
        <NavLink to="/marketing" className={linkClass}>
          Marketing
        </NavLink>
        <NavLink to="/help" className={linkClass}>
          Hilfe
        </NavLink>
        <NavLink to="/formations" className={linkClass}>
          Aufstellungen
        </NavLink>
      </nav>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/singers" element={<SingersPage />} />
        <Route path="/events" element={<EventsPage />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/projects/:id" element={<ProjectsPage />} />
        <Route path="/besetzung" element={<BesetzungPage />} />
        <Route path="/repertoire" element={<RepertoirePage />} />
        <Route path="/availability" element={<AvailabilityPage />} />
        <Route path="/wizard" element={<WizardPage />} />
        <Route path="/wizard/:flow" element={<WizardPage />} />
        <Route path="/backup" element={<BackupPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/marketing" element={<MarketingPage />} />
        <Route path="/help" element={<HelpPage />} />
        <Route path="/formations" element={<FormationsPage />} />
        <Route path="/formations/:id" element={<FormationEditorPage />} />
      </Routes>
      <footer className="mt-8 text-sm text-gray-500">
        ChorManager Web{version ? ` ${version.version}` : ''}
      </footer>
    </div>
  )
}
