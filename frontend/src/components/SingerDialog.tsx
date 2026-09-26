import { useState } from 'react'
import type { Singer, SingerInput, VoiceGroup } from '../api/client'

interface SingerDialogProps {
  title: string
  initial: Partial<Singer>
  voiceGroups: VoiceGroup[]
  onSubmit: (input: SingerInput) => void
  onClose: () => void
}

const inputClass =
  'w-full rounded border border-gray-300 px-2 py-1 dark:border-gray-600 dark:bg-gray-800'

const labelClass = 'block text-sm font-medium'

export default function SingerDialog({
  title,
  initial,
  voiceGroups,
  onSubmit,
  onClose,
}: SingerDialogProps) {
  const [fullName, setFullName] = useState(initial.full_name ?? '')
  const [shortName, setShortName] = useState(initial.short_name ?? '')
  const [voiceGroup, setVoiceGroup] = useState(initial.voice_group ?? '')
  const [height, setHeight] = useState(
    initial.height != null ? String(initial.height) : '',
  )
  const [email, setEmail] = useState(initial.email ?? '')

  const valid = fullName.trim().length > 0

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (!valid) return
    const input: SingerInput = { full_name: fullName.trim() }
    if (shortName.trim()) input.short_name = shortName.trim()
    if (voiceGroup) input.voice_group = voiceGroup
    const parsedHeight = parseInt(height, 10)
    if (height.trim() && !Number.isNaN(parsedHeight)) {
      input.height = parsedHeight
    }
    if (email.trim()) input.email = email.trim()
    onSubmit(input)
  }

  return (
    <div role="dialog" aria-label={title} className="mt-4 rounded border p-4">
      <h2 className="text-lg font-semibold">{title}</h2>
      <form onSubmit={handleSubmit} className="mt-2 space-y-2">
        <label className={labelClass}>
          Name
          <input
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            className={inputClass}
          />
        </label>
        <label className={labelClass}>
          Kurzname
          <input
            value={shortName}
            onChange={(event) => setShortName(event.target.value)}
            className={inputClass}
          />
        </label>
        <label className={labelClass}>
          Stimmgruppe
          <select
            value={voiceGroup}
            onChange={(event) => setVoiceGroup(event.target.value)}
            className={inputClass}
          >
            <option value="">–</option>
            {voiceGroups.map((group) => (
              <option key={group.id} value={group.id}>
                {group.id}
              </option>
            ))}
          </select>
        </label>
        <label className={labelClass}>
          Größe (cm)
          <input
            value={height}
            inputMode="numeric"
            onChange={(event) => setHeight(event.target.value)}
            className={inputClass}
          />
        </label>
        <label className={labelClass}>
          E-Mail
          <input
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className={inputClass}
          />
        </label>
        <div className="flex gap-2 pt-1">
          <button
            type="submit"
            disabled={!valid}
            className="rounded bg-blue-600 px-3 py-1 text-white disabled:opacity-40"
          >
            Speichern
          </button>
          <button
            type="button"
            onClick={onClose}
            className="rounded border px-3 py-1"
          >
            Abbrechen
          </button>
        </div>
      </form>
    </div>
  )
}
