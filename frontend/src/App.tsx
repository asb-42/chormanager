import { Link, Route, Routes } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import AboutPage from './pages/AboutPage'
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
import Sidebar from './components/Sidebar'
import InfoBar from './components/InfoBar'
import { ActiveProvider } from './active/active'
import { MenuIcon, MonitorIcon, MoonIcon, SunIcon } from './components/icons'
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
      title: 'Eine Aufstellung für einen Auftritt planen',
      text: 'Führt Sie Schritt für Schritt zum Sitzplan: Projekt, Termin, Besetzung, Zusagen – und öffnet dann die Aufstellung.',
    },
    {
      to: '/wizard/event',
      title: 'Einen neuen Termin eintragen',
      text: 'Probe, Konzert oder Auftritt in den Kalender aufnehmen.',
    },
    {
      to: '/wizard/availability',
      title: 'Zusagen und Absagen für einen Termin erfassen',
      text: 'Pro Sänger markieren, ob er zu einem Termin kommen kann.',
    },
    {
      to: '/wizard/singer',
      title: 'Ein Chormitglied aufnehmen',
      text: 'Name und Stimmgruppe eines neuen Sängers/einer neuen Sängerin eintragen.',
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

export default function App() {
  const { data: version } = useQuery({
    queryKey: ['version'],
    queryFn: fetchVersion,
    retry: false,
    staleTime: Infinity,
  })
  const [theme, setTheme] = useState<Theme>(loadTheme)
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(
    () =>
      typeof window.matchMedia !== 'function' ||
      window.matchMedia('(min-width: 768px)').matches,
  )

  useEffect(() => {
    applyTheme(theme)
    window.localStorage.setItem('chor-theme', theme)
  }, [theme])

  function closeSidebarOnMobile() {
    if (
      typeof window.matchMedia === 'function' &&
      !window.matchMedia('(min-width: 768px)').matches
    ) {
      setSidebarOpen(false)
    }
  }

  const themeButton =
    'rounded p-2 hover:bg-gray-100 dark:hover:bg-gray-800'

  return (
    <ActiveProvider>
      <div className="flex min-h-screen flex-col">
        <header className="flex items-center gap-2 border-b border-gray-200 px-4 py-2 dark:border-gray-700">
          <button
            type="button"
            onClick={() => setSidebarOpen((open) => !open)}
            aria-label="Navigation"
            aria-expanded={sidebarOpen}
            className={`${themeButton} md:hidden`}
          >
            <MenuIcon />
          </button>
          <div className="font-bold tracking-tight md:w-52">Chormanager</div>
          <div className="flex-1" />
          <span className="flex gap-1" role="group" aria-label="Ansicht">
            <button
              type="button"
              onClick={() => setTheme('light')}
              aria-pressed={theme === 'light'}
              aria-label="Hell"
              title="Hell"
              className={themeButton}
            >
              <SunIcon />
            </button>
            <button
              type="button"
              onClick={() => setTheme('dark')}
              aria-pressed={theme === 'dark'}
              aria-label="Dunkel"
              title="Dunkel"
              className={themeButton}
            >
              <MoonIcon />
            </button>
            <button
              type="button"
              onClick={() => setTheme('system')}
              aria-pressed={theme === 'system'}
              aria-label="Auto"
              title="Auto"
              className={themeButton}
            >
              <MonitorIcon />
            </button>
          </span>
        </header>
        <div className="flex min-h-0 flex-1">
          <div
            className={`${
              sidebarOpen ? '' : 'hidden'
            } fixed inset-y-0 left-0 z-40 flex md:static md:flex`}
          >
            <Sidebar open={sidebarOpen} onNavigate={closeSidebarOnMobile} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="mx-auto max-w-5xl p-4">
              <InfoBar />
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
        <Route path="/about" element={<AboutPage />} />
        <Route path="/formations" element={<FormationsPage />} />
        <Route path="/formations/:id" element={<FormationEditorPage />} />
      </Routes>
      <footer className="mt-8 text-sm text-gray-500">
        ChorManager Web{version ? ` ${version.version}` : ''}
      </footer>
            </div>
          </div>
        </div>
      </div>
    </ActiveProvider>
  )
}
