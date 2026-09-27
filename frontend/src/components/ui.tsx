// Design-Fundament: geteilte UI-Primitives (eine Sprache).
//
// Regeln: Buttons/Inputs/Labels kommen von hier, keine Ad-hoc-
// Klassen in Pages/Dialogen. Varianten: primary (Hauptaktion),
// secondary (Standard), danger (Löschen), success (Bestätigen),
// ghost (unauffällig). Größen: md (Standard), sm (Tabellenzeilen).
// Design-System: Warm, elegant, freundlich (siehe index.css).
import type { ButtonHTMLAttributes, ReactNode } from 'react'

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'success' | 'ghost'
export type ButtonSize = 'md' | 'sm'

const baseButton =
  'inline-flex items-center justify-center gap-1.5 rounded-lg font-medium ' +
  'shadow-soft hover:shadow-card active:shadow-none ' +
  'focus-visible:outline-2 focus-visible:outline-offset-2 ' +
  'focus-visible:outline-primary-500 disabled:opacity-40 disabled:cursor-not-allowed ' +
  'disabled:shadow-none'

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    'bg-primary-600 text-white hover:bg-primary-700 active:bg-primary-800 ' +
    'shadow-[0_2px_4px_-1px_rgb(79_70_229/0.3)]',
  secondary:
    'border border-warm-200 bg-white text-warm-700 hover:bg-warm-50 ' +
    'hover:border-warm-300 active:bg-warm-100 ' +
    'dark:border-warm-700 dark:bg-warm-800 dark:text-warm-200 ' +
    'dark:hover:bg-warm-700 dark:hover:border-warm-600 dark:active:bg-warm-600',
  danger:
    'bg-danger-600 text-white hover:bg-danger-700 active:bg-danger-800 ' +
    'shadow-[0_2px_4px_-1px_rgb(220_38_38/0.3)]',
  success:
    'bg-success-600 text-white hover:bg-success-700 active:bg-success-800 ' +
    'shadow-[0_2px_4px_-1px_rgb(22_163_74/0.3)]',
  ghost:
    'text-warm-600 hover:bg-warm-100 active:bg-warm-200 ' +
    'dark:text-warm-300 dark:hover:bg-warm-800 dark:active:bg-warm-700',
}

const sizeClasses: Record<ButtonSize, string> = {
  md: 'px-4 py-2 text-sm',
  sm: 'px-2.5 py-1 text-sm',
}

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
}

export function Button({
  variant = 'secondary',
  size = 'md',
  className = '',
  type = 'button',
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`${baseButton} ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
      {...rest}
    />
  )
}

export const inputClassName =
  'w-full rounded-lg border border-warm-200 bg-white px-3 py-2 text-sm ' +
  'text-warm-900 placeholder:text-warm-400 ' +
  'shadow-soft focus-visible:border-primary-400 ' +
  'focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-primary-500 ' +
  'dark:border-warm-700 dark:bg-warm-800 dark:text-warm-100 dark:placeholder:text-warm-500 ' +
  'dark:focus-visible:border-primary-500'

export const labelClassName = 'block text-sm font-medium text-warm-700 dark:text-warm-300'

export function Field({
  label,
  hint,
  children,
}: {
  label: string
  hint?: string
  children: ReactNode
}) {
  return (
    <label className={labelClassName}>
      {label}
      {children}
      {hint && (
        <span className="mt-1 block text-xs font-normal text-warm-500 dark:text-warm-400">
          {hint}
        </span>
      )}
    </label>
  )
}

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string
  subtitle?: string
  actions?: ReactNode
}) {
  return (
    <div className="mb-6 border-b border-warm-200 pb-4 dark:border-warm-700">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-warm-900 dark:text-warm-50">
            {title}
          </h1>
          {subtitle && (
            <p className="mt-1 text-sm text-warm-500 dark:text-warm-400">{subtitle}</p>
          )}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
    </div>
  )
}

export function EmptyState({
  text,
  action,
}: {
  text: string
  action?: ReactNode
}) {
  return (
    <div className="mt-6 rounded-xl border border-dashed border-warm-300 bg-warm-50/50 px-6 py-10 text-center dark:border-warm-600 dark:bg-warm-800/30">
      <p className="text-warm-500 dark:text-warm-400">{text}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export function ErrorMessage({ text }: { text: string }) {
  return (
    <div
      role="alert"
      className="mt-4 rounded-lg border border-danger-200 bg-danger-50 px-4 py-3 text-sm text-danger-700 dark:border-danger-800 dark:bg-danger-900/30 dark:text-danger-300"
    >
      {text}
    </div>
  )
}

export function Th({ children }: { children: ReactNode }) {
  return (
    <th className="sticky top-0 border-b border-warm-200 bg-warm-50/95 py-3 pr-4 text-left text-xs font-semibold uppercase tracking-wider text-warm-500 backdrop-blur-sm dark:border-warm-700 dark:bg-warm-800/95 dark:text-warm-400">
      {children}
    </th>
  )
}

export function Td({ children, title }: { children: ReactNode; title?: string }) {
  return (
    <td
      title={title}
      className="border-b border-warm-100 py-2.5 pr-4 tabular-nums text-sm text-warm-700 dark:border-warm-800 dark:text-warm-300"
    >
      {children}
    </td>
  )
}

export const dialogClassName =
  'mt-4 max-w-md rounded-xl border border-warm-200 bg-white p-5 shadow-lifted ' +
  'dark:border-warm-700 dark:bg-warm-900'

export function Loading({ text = 'Lädt …' }: { text?: string }) {
  return (
    <div className="mt-6 flex items-center gap-2 text-warm-500 dark:text-warm-400">
      <svg
        className="h-4 w-4 animate-spin text-primary-500"
        viewBox="0 0 24 24"
        fill="none"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
        />
      </svg>
      <span className="text-sm">{text}</span>
    </div>
  )
}

export function IconButton({
  label,
  title,
  onClick,
  disabled = false,
  children,
}: {
  label: string
  title?: string
  onClick: () => void
  disabled?: boolean
  children: ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title ?? label}
      aria-label={label}
      className="rounded-lg p-2 text-warm-500 hover:bg-warm-100 hover:text-warm-700 disabled:opacity-40 disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500 dark:text-warm-400 dark:hover:bg-warm-800 dark:hover:text-warm-200"
    >
      {children}
    </button>
  )
}
