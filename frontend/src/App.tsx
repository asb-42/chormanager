import { NavLink, Route, Routes } from 'react-router-dom'
import EventsPage from './pages/EventsPage'
import ProjectsPage from './pages/ProjectsPage'
import SingersPage from './pages/SingersPage'

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
      </nav>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/singers" element={<SingersPage />} />
        <Route path="/events" element={<EventsPage />} />
        <Route path="/projects" element={<ProjectsPage />} />
      </Routes>
    </div>
  )
}
