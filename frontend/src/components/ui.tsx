// Design-Fundament: geteilte UI-Primitives (eine Sprache).
//
// Regeln: Buttons/Inputs/Labels kommen von hier, keine Ad-hoc-
// Klassen in Pages/Dialogen. Varianten: primary (Hauptaktion),
// secondary (Standard), danger (Löschen), success (Bestätigen),
// ghost (unauffällig). Größen: md (Standard), sm (Tabellenzeilen).
import type { ButtonHTMLAttributes, ReactNode } from 'react'

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'success' | 'ghost'
export type ButtonSize = 'md' | 'sm'

const baseButton =
  'rounded font-medium focus-visible:outline-2 focus-visible:outline-offset-2 ' +
  'focus-visible:outline-blue-600 disabled:opacity-40'

const variantClasses: Record<ButtonVariant, string> = {
  primary: 'bg-blue-700 text-white hover:bg-blue-800',
  secondary:
    'border border-gray-300 hover:bg-gray-100 dark:border-gray-600 dark:hover:bg-gray-800',
  danger: 'bg-red-700 text-white hover:bg-red-800',
  success: 'bg-green-700 text-white hover:bg-green-800',
  ghost: 'hover:bg-gray-100 dark:hover:bg-gray-800',
}

const sizeClasses: Record<ButtonSize, string> = {
  md: 'px-3 py-1 text-sm',
  sm: 'px-2 py-0.5 text-sm',
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
  'w-full rounded border border-gray-300 px-2 py-1 ' +
  'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 ' +
  'dark:border-gray-600 dark:bg-gray-800'

export const labelClassName = 'block text-sm font-medium'

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
      {hint && <span className="block text-xs font-normal text-gray-500">{hint}</span>}
    </label>
  )
}

export function PageHeader({
  title,
  actions,
}: {
  title: string
  actions?: ReactNode
}) {
  return (
    <div className="flex flex-wrap items-center gap-3 border-b border-gray-200 pb-2 dark:border-gray-700">
      <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
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
    <div className="mt-4 rounded border border-dashed border-gray-300 p-6 text-center dark:border-gray-600">
      <p className="text-gray-600 dark:text-gray-300">{text}</p>
      {action && <div className="mt-3">{action}</div>}
    </div>
  )
}

export function ErrorMessage({ text }: { text: string }) {
  return (
    <p role="alert" className="mt-4 text-red-600 dark:text-red-400">
      {text}
    </p>
  )
}

export function Th({ children }: { children: ReactNode }) {
  return (
    <th className="sticky top-0 bg-white py-2 pr-4 text-left text-xs font-semibold uppercase tracking-wider text-gray-500 dark:bg-[#16171d] dark:text-gray-400">
      {children}
    </th>
  )
}

export function Td({ children, title }: { children: ReactNode; title?: string }) {
  return (
    <td title={title} className="py-2 pr-4 tabular-nums">
      {children}
    </td>
  )
}

export const dialogClassName =
  'mt-4 max-w-md rounded-lg border border-gray-200 bg-white p-4 shadow-lg ' +
  'dark:border-gray-700 dark:bg-gray-900'

export function Loading({ text = 'Lädt …' }: { text?: string }) {
  return <p className="mt-4 text-gray-500">{text}</p>
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
      className="rounded p-1.5 hover:bg-gray-100 disabled:opacity-40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 dark:hover:bg-gray-800"
    >
      {children}
    </button>
  )
}
