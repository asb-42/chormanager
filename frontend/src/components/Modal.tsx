// Modales Dialog-System (Overlay, Escape, Fokus, Scroll-Lock).
// Ersetzt Inline-Karten am Seitenende: Dialoge sind modal sofort sichtbar.
import { useEffect, useRef } from 'react'
import type { ReactNode } from 'react'
import { dialogClassName } from './ui'

export function Modal({
  label,
  onClose,
  wide = false,
  children,
}: {
  label: string
  onClose: () => void
  wide?: boolean
  children: ReactNode
}) {
  const boxRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const first = boxRef.current?.querySelector(
      'input, select, textarea, button',
    )
    ;(first as HTMLElement | null)?.focus?.()
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener('keydown', onKey)
    }
  }, [onClose])

  return (
    <div
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
    >
      <div
        ref={boxRef}
        role="dialog"
        aria-label={label}
        aria-modal="true"
        className={`${dialogClassName} max-h-[90vh] w-full overflow-y-auto ${
          wide ? 'max-w-2xl' : 'max-w-lg'
        }`}
      >
        {children}
      </div>
    </div>
  )
}
