import { useState } from 'react'
import type { Singer, SingerInput, VoiceGroup } from '../api/client'
import { Button, Field, inputClassName } from './ui'
import { Modal } from './Modal'

interface SingerDialogProps {
  title: string
  initial: Partial<Singer>
  voiceGroups: VoiceGroup[]
  onSubmit: (input: SingerInput) => void
  onClose: () => void
}

const TEXT_FIELDS: { key: keyof SingerInput; label: string; type?: string }[] = [
  { key: 'short_name', label: 'Kurzname' },
  { key: 'birth_date', label: 'Geburtsdatum', type: 'date' },
  { key: 'gender', label: 'Geschlecht' },
]

function str(value: unknown): string {
  return value === null || value === undefined ? '' : String(value)
}

export default function SingerDialog({
  title,
  initial,
  voiceGroups,
  onSubmit,
  onClose,
}: SingerDialogProps) {
  const [form, setForm] = useState<Record<string, string>>(() => ({
    full_name: str(initial.full_name),
    short_name: str(initial.short_name),
    birth_date: str(initial.birth_date)?.slice(0, 10) ?? '',
    gender: str(initial.gender),
    email: str(initial.email),
    phone: str(initial.phone),
    social_contacts: str(initial.social_contacts),
    street: str(initial.street),
    postal_code: str(initial.postal_code),
    city: str(initial.city),
    voice_group: str(initial.voice_group),
    height: str(initial.height),
    joined_year: str(initial.joined_year),
    joined_month: str(initial.joined_month),
    left_year: str(initial.left_year),
    left_month: str(initial.left_month),
    affinity_uuid: str(initial.affinity_uuid),
    guardian1: str(initial.guardian1),
    guardian1_phone: str(initial.guardian1_phone),
    guardian2: str(initial.guardian2),
    guardian2_phone: str(initial.guardian2_phone),
  }))

  function set(key: string, value: string) {
    setForm((previous) => ({ ...previous, [key]: value }))
  }

  const valid = form.full_name.trim().length > 0

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (!valid) return
    const out: Record<string, unknown> = { full_name: form.full_name.trim() }
    const text = (key: string) => {
      const value = (form[key] ?? '').trim()
      if (value) out[key] = value
    }
    const num = (key: string) => {
      const raw = (form[key] ?? '').trim()
      if (!raw) return
      const parsed = parseInt(raw, 10)
      if (!Number.isNaN(parsed)) out[key] = parsed
    }
    text('short_name')
    text('birth_date')
    text('gender')
    text('email')
    text('phone')
    text('social_contacts')
    text('street')
    text('postal_code')
    text('city')
    text('voice_group')
    num('height')
    num('joined_year')
    num('joined_month')
    num('left_year')
    num('left_month')
    text('affinity_uuid')
    text('guardian1')
    text('guardian1_phone')
    text('guardian2')
    text('guardian2_phone')
    onSubmit(out as unknown as SingerInput)
  }

  function textField(key: string, label: string, type?: string) {
    return (
      <Field key={key} label={label}>
        <input
          type={type ?? 'text'}
          value={form[key] ?? ''}
          onChange={(event) => set(key, event.target.value)}
          className={inputClassName}
        />
      </Field>
    )
  }

  return (
    <Modal label={title} onClose={onClose} wide>
      <h2 className="text-lg font-semibold">{title}</h2>
      <form onSubmit={handleSubmit} className="mt-3 space-y-4">
        <fieldset>
          <legend className="text-sm font-semibold uppercase tracking-wider text-gray-500">
            Person
          </legend>
          <div className="mt-1 grid gap-2 sm:grid-cols-2">
            <Field label="Name">
              <input
                value={form.full_name}
                onChange={(event) => set('full_name', event.target.value)}
                className={inputClassName}
              />
            </Field>
            {TEXT_FIELDS.map((field) => (
              <div key={field.key}>{textField(field.key, field.label, field.type)}</div>
            ))}
          </div>
        </fieldset>
        <fieldset>
          <legend className="text-sm font-semibold uppercase tracking-wider text-gray-500">
            Kontakt
          </legend>
          <div className="mt-1 grid gap-2 sm:grid-cols-2">
            {textField('email', 'E-Mail')}
            {textField('phone', 'Telefon')}
            {textField('social_contacts', 'Kontakte')}
          </div>
        </fieldset>
        <fieldset>
          <legend className="text-sm font-semibold uppercase tracking-wider text-gray-500">
            Adresse
          </legend>
          <div className="mt-1 grid gap-2 sm:grid-cols-2">
            {textField('street', 'Straße')}
            {textField('postal_code', 'PLZ')}
            {textField('city', 'Ort')}
          </div>
        </fieldset>
        <fieldset>
          <legend className="text-sm font-semibold uppercase tracking-wider text-gray-500">
            Chor
          </legend>
          <div className="mt-1 grid gap-2 sm:grid-cols-2">
            <Field label="Stimmgruppe">
              <select
                value={form.voice_group}
                onChange={(event) => set('voice_group', event.target.value)}
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
            {textField('height', 'Größe (cm)')}
            {textField('joined_year', 'Eintritt Jahr')}
            {textField('joined_month', 'Eintritt Monat')}
            {textField('left_year', 'Austritt Jahr')}
            {textField('left_month', 'Austritt Monat')}
            {textField('affinity_uuid', 'Sitzpartner-ID')}
          </div>
        </fieldset>
        <fieldset>
          <legend className="text-sm font-semibold uppercase tracking-wider text-gray-500">
            Familie
          </legend>
          <div className="mt-1 grid gap-2 sm:grid-cols-2">
            {textField('guardian1', 'Sorgeberechtigt 1')}
            {textField('guardian1_phone', 'Telefon 1')}
            {textField('guardian2', 'Sorgeberechtigt 2')}
            {textField('guardian2_phone', 'Telefon 2')}
          </div>
        </fieldset>
        <div className="flex gap-2 pt-1">
          <Button type="submit" variant="primary" disabled={!valid}>
            Speichern
          </Button>
          <Button onClick={onClose}>Abbrechen</Button>
        </div>
      </form>
    </Modal>
  )
}
