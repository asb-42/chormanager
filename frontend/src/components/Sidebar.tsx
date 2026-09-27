// Linke Sidebar: Hauptpills mit Icons oben, Text-Links unten.
// Design: Warm, elegant, freundlich (siehe index.css).
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
      className="flex w-60 shrink-0 flex-col border-r border-warm-200 bg-gradient-to-b from-warm-50 to-warm-100/50 px-3 py-5 shadow-sidebar dark:border-warm-700 dark:from-warm-900 dark:to-warm-800/50"
    >
      <div className="mb-6 px-3">
        <span className="text-lg font-bold tracking-tight text-warm-900 dark:text-warm-50">
          ChorManager
        </span>
      </div>
      <ul className="space-y-1">
        {MAIN.map(({ to, label, Icon }) => (
          <li key={to}>
            <NavLink
              to={to}
              onClick={onNavigate}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-primary-600 text-white shadow-[0_2px_4px_-1px_rgb(79_70_229/0.3)]'
                    : 'text-warm-600 hover:bg-warm-200/60 hover:text-warm-900 dark:text-warm-300 dark:hover:bg-warm-800 dark:hover:text-warm-100'
                }`
              }
            >
              <Icon />
              {label}
            </NavLink>
          </li>
        ))}
      </ul>
      <div className="mt-auto space-y-1 border-t border-warm-200 pt-4 dark:border-warm-700">
        {BOTTOM.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            onClick={onNavigate}
            className="block rounded-lg px-3 py-2 text-sm text-warm-500 transition-colors hover:bg-warm-200/60 hover:text-warm-900 dark:text-warm-400 dark:hover:bg-warm-800 dark:hover:text-warm-100"
          >
            {label}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
