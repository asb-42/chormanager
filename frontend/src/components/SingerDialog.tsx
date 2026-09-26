import { useState } from 'react'
import type { Singer, SingerInput, VoiceGroup } from '../api/client'
import { Button, Field, dialogClassName, inputClassName } from './ui'

interface SingerDialogProps {
  title: string
  initial: Partial<Singer>
  voiceGroups: VoiceGroup[]
  onSubmit: (input: SingerInput) => void
  onClose: () => void
}

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
    <div role="dialog" aria-label={title} className={dialogClassName}>
      <h2 className="text-lg font-semibold">{title}</h2>
      <form onSubmit={handleSubmit} className="mt-2 space-y-2">
        <Field label="Name">
          <input
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            className={inputClassName}
          />
        </Field>
        <Field label="Kurzname">
          <input
            value={shortName}
            onChange={(event) => setShortName(event.target.value)}
            className={inputClassName}
          />
        </Field>
        <Field label="Stimmgruppe">
          <select
            value={voiceGroup}
            onChange={(event) => setVoiceGroup(event.target.value)}
            className={inputClassName}
          >
            <option value="">–</option>
            {voiceGroups.map((group) => (
              <option key={group.id} value={group.id}>
                {group.id}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Größe (cm)">
          <input
            value={height}
            inputMode="numeric"
            onChange={(event) => setHeight(event.target.value)}
            className={inputClassName}
          />
        </Field>
        <Field label="E-Mail">
          <input
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className={inputClassName}
          />
        </Field>
        <div className="flex gap-2 pt-1">
          <Button type="submit" variant="primary" disabled={!valid}>
            Speichern
          </Button>
          <Button onClick={onClose}>Abbrechen</Button>
        </div>
      </form>
    </div>
  )
}
