// Menüleiste nach Qt-Vorbild (Dropdowns: Datei, Bearbeiten,
// Ansicht, Konfiguration, Marketing, Hilfe). Ersetzt keine Nav,
// sondern ergänzt sie um die bekannten Menü-Einstiege.
import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate, type To } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createBackup } from '../api/client'

export type MenuTheme = 'light' | 'dark' | 'system'

interface MenuItem {
  label: string
  hint?: string
  disabled?: boolean
  action: () => void
}

function MenuDropdown({
  label,
  open,
  onToggle,
  onClose,
  items,
}: {
  label: string
  open: boolean
  onToggle: () => void
  onClose: () => void
  items: (MenuItem | 'separator')[]
}) {
  const boxRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    function onDown(event: MouseEvent) {
      if (boxRef.current && !boxRef.current.contains(event.target as Node)) {
        onClose()
      }
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('mousedown', onDown)
    window.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      window.removeEventListener('keydown', onKey)
    }
  }, [open, onClose])

  return (
    <div ref={boxRef} className="relative">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={onToggle}
        className="rounded px-3 py-1 hover:bg-gray-100 dark:hover:bg-gray-800"
      >
        {label}
      </button>
      {open && (
        <div
          role="menu"
          aria-label={label}
          className="absolute left-0 z-50 mt-1 min-w-48 rounded border border-gray-200 bg-white py-1 shadow-lg dark:border-gray-700 dark:bg-gray-900"
        >
          {items.map((item, index) =>
            item === 'separator' ? (
              <div key={`sep-${index}`} role="separator" className="my-1 border-t border-gray-200 dark:border-gray-700" />
            ) : (
              <button
                key={item.label}
                type="button"
                role="menuitem"
                disabled={item.disabled}
                title={item.hint}
                onClick={() => {
                  onClose()
                  item.action()
                }}
                className="block w-full px-3 py-1 text-left text-sm hover:bg-gray-100 disabled:opacity-40 dark:hover:bg-gray-800"
              >
                {item.label}
              </button>
            ),
          )}
        </div>
      )}
    </div>
  )
}

export default function MenuBar({
  theme = 'system',
  onTheme = () => {},
}: {
  theme?: MenuTheme
  onTheme?: (theme: MenuTheme) => void
}) {
  const [open, setOpen] = useState<string | null>(null)
  const location = useLocation()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  function go(to: To) {
    navigate(to)
  }

  const inEditor = location.pathname.startsWith('/formations/')

  function dispatchEditor(type: 'chor:undo' | 'chor:redo') {
    window.dispatchEvent(new CustomEvent(type))
  }

  const createBackupMutation = useMutation({
    mutationFn: () => createBackup(),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['backups'] })
      go('/backup')
    },
  })

  function toggle(name: string) {
    setOpen((previous) => (previous === name ? null : name))
  }

  function close() {
    setOpen(null)
  }

  return (
    <div className="mb-4 flex flex-wrap gap-1 border-b border-gray-200 pb-2 dark:border-gray-700">
      <MenuDropdown
        label="Datei"
        open={open === 'Datei'}
        onToggle={() => toggle('Datei')}
        onClose={close}
        items={[
          { label: 'Backup anlegen', action: () => createBackupMutation.mutate() },
          { label: 'Backup & Restore…', action: () => go('/backup') },
        ]}
      />
      <MenuDropdown
        label="Bearbeiten"
        open={open === 'Bearbeiten'}
        onToggle={() => toggle('Bearbeiten')}
        onClose={close}
        items={[
          {
            label: 'Rückgängig',
            hint: inEditor ? 'Strg+Z' : 'Nur im Aufstellungs-Editor',
            disabled: !inEditor,
            action: () => dispatchEditor('chor:undo'),
          },
          {
            label: 'Wiederholen',
            hint: inEditor ? 'Strg+Umschalt+Z' : 'Nur im Aufstellungs-Editor',
            disabled: !inEditor,
            action: () => dispatchEditor('chor:redo'),
          },
        ]}
      />
      <MenuDropdown
        label="Ansicht"
        open={open === 'Ansicht'}
        onToggle={() => toggle('Ansicht')}
        onClose={close}
        items={[
          { label: `Hell${theme === 'light' ? ' ✓' : ''}`, action: () => onTheme('light') },
          { label: `Dunkel${theme === 'dark' ? ' ✓' : ''}`, action: () => onTheme('dark') },
          { label: `Auto${theme === 'system' ? ' ✓' : ''}`, action: () => onTheme('system') },
        ]}
      />
      <MenuDropdown
        label="Konfiguration"
        open={open === 'Konfiguration'}
        onToggle={() => toggle('Konfiguration')}
        onClose={close}
        items={[{ label: 'Einstellungen…', action: () => go('/settings') }]}
      />
      <MenuDropdown
        label="Marketing"
        open={open === 'Marketing'}
        onToggle={() => toggle('Marketing')}
        onClose={close}
        items={[{ label: 'Selbstdarstellung…', action: () => go('/marketing') }]}
      />
      <MenuDropdown
        label="Hilfe"
        open={open === 'Hilfe'}
        onToggle={() => toggle('Hilfe')}
        onClose={close}
        items={[
          { label: 'Version prüfen', action: () => go('/help') },
          'separator',
          { label: 'Über…', action: () => go('/help') },
        ]}
      />
    </div>
  )
}
