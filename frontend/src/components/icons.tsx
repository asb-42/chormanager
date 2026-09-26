// Deskriptive SVG-Icons (keine Emojis): geometrische Linienstil-Icons.
function Base({
  children,
  className = '',
}: {
  children: React.ReactNode
  className?: string
}) {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      {children}
    </svg>
  )
}

export function TasksIcon({ className }: { className?: string }) {
  return (
    <Base className={className}>
      <rect x="4" y="4" width="16" height="16" rx="2" />
      <path d="M9 12l2 2 4-4" />
    </Base>
  )
}

export function ProjectsIcon({ className }: { className?: string }) {
  return (
    <Base className={className}>
      <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
    </Base>
  )
}

export function SingersIcon({ className }: { className?: string }) {
  return (
    <Base className={className}>
      <circle cx="9" cy="8" r="3" />
      <path d="M3 20c0-3.5 2.7-5.5 6-5.5s6 2 6 5.5" />
      <circle cx="17" cy="9" r="2.5" />
      <path d="M16.5 15c2.3.6 4.5 2.2 4.5 5" />
    </Base>
  )
}

export function BesetzungIcon({ className }: { className?: string }) {
  return (
    <Base className={className}>
      <path d="M9 6h12M9 12h12M9 18h12" />
      <path d="M3.5 6l1 1 2-2M3.5 12l1 1 2-2M3.5 18l1 1 2-2" />
    </Base>
  )
}

export function EventsIcon({ className }: { className?: string }) {
  return (
    <Base className={className}>
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M3 10h18M8 3v4M16 3v4" />
    </Base>
  )
}

export function FormationIcon({ className }: { className?: string }) {
  return (
    <Base className={className}>
      <rect x="4" y="4" width="7" height="7" rx="1" />
      <rect x="13" y="4" width="7" height="7" rx="1" />
      <rect x="4" y="13" width="7" height="7" rx="1" />
      <rect x="13" y="13" width="7" height="7" rx="1" />
    </Base>
  )
}

export function RepertoireIcon({ className }: { className?: string }) {
  return (
    <Base className={className}>
      <path d="M9 18V6l10-2v11" />
      <circle cx="6.5" cy="18" r="2.5" />
      <circle cx="16.5" cy="15" r="2.5" />
    </Base>
  )
}

export function MarketingIcon({ className }: { className?: string }) {
  return (
    <Base className={className}>
      <path d="M4 10v5h3l7 4V6l-7 4H4z" />
      <path d="M17.5 9a4.5 4.5 0 0 1 0 6" />
    </Base>
  )
}

export function SunIcon({ className }: { className?: string }) {
  return (
    <Base className={className}>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </Base>
  )
}

export function MoonIcon({ className }: { className?: string }) {
  return (
    <Base className={className}>
      <path d="M20 13A8 8 0 1 1 11 4a6.5 6.5 0 0 0 9 9z" />
    </Base>
  )
}

export function MonitorIcon({ className }: { className?: string }) {
  return (
    <Base className={className}>
      <rect x="3" y="4" width="18" height="12" rx="2" />
      <path d="M9 20h6M12 16v4" />
    </Base>
  )
}

export function EditIcon({ className }: { className?: string }) {
  return (
    <Base className={className}>
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z" />
    </Base>
  )
}

export function DuplicateIcon({ className }: { className?: string }) {
  return (
    <Base className={className}>
      <rect x="9" y="9" width="12" height="12" rx="2" />
      <path d="M5 15V5a2 2 0 0 1 2-2h10" />
    </Base>
  )
}

export function DeleteIcon({ className }: { className?: string }) {
  return (
    <Base className={className}>
      <path d="M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2m3 0-1 13a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L6 7" />
      <path d="M10 11v6M14 11v6" />
    </Base>
  )
}

export function MenuIcon({ className }: { className?: string }) {
  return (
    <Base className={className}>
      <path d="M4 7h16M4 12h16M4 17h16" />
    </Base>
  )
}
