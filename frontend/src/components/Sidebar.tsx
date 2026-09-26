// Linke Sidebar (Qt-nah): Hauptpills mit Icons oben, Text-Links unten.
import { NavLink } from 'react-router-dom'
import {
  BesetzungIcon,
  EventsIcon,
  FormationIcon,
  MarketingIcon,
  ProjectsIcon,
  RepertoireIcon,
  SingersIcon,
  TasksIcon,
} from './icons'

const MAIN = [
  { to: '/', label: 'Aufgaben', Icon: TasksIcon },
  { to: '/projects', label: 'Projekte', Icon: ProjectsIcon },
  { to: '/singers', label: 'Sänger', Icon: SingersIcon },
  { to: '/besetzung', label: 'Besetzung', Icon: BesetzungIcon },
  { to: '/events', label: 'Termine', Icon: EventsIcon },
  { to: '/formations', label: 'Aufstellung', Icon: FormationIcon },
  { to: '/repertoire', label: 'Repertoire', Icon: RepertoireIcon },
  { to: '/marketing', label: 'Marketing', Icon: MarketingIcon },
]

const BOTTOM = [
  { to: '/backup', label: 'Backup' },
  { to: '/settings', label: 'Konfiguration' },
  { to: '/help', label: 'Hilfe' },
  { to: '/about', label: 'About' },
]

export default function Sidebar({
  open,
  onNavigate,
}: {
  open: boolean
  onNavigate: () => void
}) {
  if (!open) return null
  return (
    <nav
      aria-label="Hauptnavigation"
      className="flex w-56 shrink-0 flex-col border-r border-gray-200 bg-gray-50 px-2 py-4 dark:border-gray-700 dark:bg-gray-900"
    >
      <ul className="space-y-1">
        {MAIN.map(({ to, label, Icon }) => (
          <li key={to}>
            <NavLink
              to={to}
              onClick={onNavigate}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded px-3 py-2 text-sm font-medium ${
                  isActive
                    ? 'bg-blue-700 text-white'
                    : 'hover:bg-gray-200 dark:hover:bg-gray-800'
                }`
              }
            >
              <Icon />
              {label}
            </NavLink>
          </li>
        ))}
      </ul>
      <div className="mt-auto space-y-1 border-t border-gray-200 pt-3 dark:border-gray-700">
        {BOTTOM.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            onClick={onNavigate}
            className="block px-3 py-1 text-sm text-gray-500 hover:text-gray-900 hover:underline dark:text-gray-400 dark:hover:text-gray-100"
          >
            {label}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
