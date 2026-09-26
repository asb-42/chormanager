import { NavLink, Route, Routes } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import AvailabilityPage from './pages/AvailabilityPage'
import BackupPage from './pages/BackupPage'
import BesetzungPage from './pages/BesetzungPage'
import EventsPage from './pages/EventsPage'
import FormationEditorPage from './pages/FormationEditorPage'
import FormationsPage from './pages/FormationsPage'
import ProjectsPage from './pages/ProjectsPage'
import RepertoirePage from './pages/RepertoirePage'
import SingersPage from './pages/SingersPage'
import WizardPage from './pages/WizardPage'
import { fetchVersion } from './api/client'

function HomePage() {
  return (
    <section>
      <h1 className="text-xl font-semibold">ChorManager</h1>
      <p className="mt-2">Chorverwaltung im Browser (M2-Aufbau).</p>
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
  return (
    <div className="mx-auto max-w-5xl p-4">
      <nav className="mb-6 flex gap-2">
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
        <NavLink to="/formations" className={linkClass}>
          Aufstellungen
        </NavLink>
      </nav>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/singers" element={<SingersPage />} />
        <Route path="/events" element={<EventsPage />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/besetzung" element={<BesetzungPage />} />
        <Route path="/repertoire" element={<RepertoirePage />} />
        <Route path="/availability" element={<AvailabilityPage />} />
        <Route path="/wizard" element={<WizardPage />} />
        <Route path="/backup" element={<BackupPage />} />
        <Route path="/formations" element={<FormationsPage />} />
        <Route path="/formations/:id" element={<FormationEditorPage />} />
      </Routes>
      <footer className="mt-8 text-sm text-gray-500">
        ChorManager Web{version ? ` ${version.version}` : ''}
      </footer>
    </div>
  )
}
