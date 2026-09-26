import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { fetchMarketing, putMarketing } from '../api/client'
import { PageHeader } from '../components/ui'

export default function MarketingPage() {
  const [saved, setSaved] = useState(false)
  const { data, isLoading, isError } = useQuery({
    queryKey: ['marketing'],
    queryFn: fetchMarketing,
  })
  const [text, setText] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: (content: string) => putMarketing(content),
    onSuccess: () => setSaved(true),
  })

  return (
    <section>
      <PageHeader title="Marketing" />
      {isLoading && <p className="mt-4">Lädt …</p>}
      {isError && <p className="mt-4 text-red-600">Fehler beim Laden.</p>}
      {data && (
        <div className="mt-4 max-w-2xl">
          <label className="block text-sm font-medium">
            Selbstdarstellung
            <textarea
              value={text ?? data.content}
              onChange={(event) => {
                setText(event.target.value)
                setSaved(false)
              }}
              rows={10}
              className="mt-1 w-full rounded border border-gray-300 px-2 py-1 dark:border-gray-600 dark:bg-gray-800"
            />
          </label>
          <button
            type="button"
            onClick={() => mutation.mutate(text ?? data.content)}
            className="mt-2 rounded bg-blue-600 px-3 py-1 text-white"
          >
            Speichern
          </button>
          {saved && <p className="mt-2">Gespeichert.</p>}
        </div>
      )}
    </section>
  )
}
