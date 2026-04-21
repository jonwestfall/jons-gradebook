import { FormEvent, useEffect, useState } from 'react'
import { api } from '../api/client'

type Doc = {
  id: number
  title: string
  owner_type: string
  owner_id: number
  current_version: number
  document_type: string
}

export function DocumentsPage() {
  const [documents, setDocuments] = useState<Doc[]>([])
  const [title, setTitle] = useState('')
  const [ownerType, setOwnerType] = useState('student')
  const [ownerId, setOwnerId] = useState('1')
  const [file, setFile] = useState<File | null>(null)

  async function load() {
    setDocuments(await api.get<Doc[]>('/documents/'))
  }

  async function upload(event: FormEvent) {
    event.preventDefault()
    if (!file) return
    const form = new FormData()
    form.append('owner_type', ownerType)
    form.append('owner_id', ownerId)
    form.append('title', title)
    form.append('file', file)
    await api.post('/documents/upload', form)
    setTitle('')
    setFile(null)
    await load()
  }

  useEffect(() => {
    void load()
  }, [])

  return (
    <section>
      <h2>Documents</h2>
      <form className="form" onSubmit={upload}>
        <input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Title" required />
        <input value={ownerType} onChange={(event) => setOwnerType(event.target.value)} placeholder="Owner type" required />
        <input value={ownerId} onChange={(event) => setOwnerId(event.target.value)} placeholder="Owner ID" required />
        <input
          type="file"
          onChange={(event) => {
            const selected = event.target.files?.[0]
            if (selected) setFile(selected)
          }}
          required
        />
        <button type="submit">Upload + Extract</button>
      </form>
      <ul className="list">
        {documents.map((document) => (
          <li key={document.id} className="card">
            <h3>{document.title}</h3>
            <div>
              {document.owner_type}:{document.owner_id}
            </div>
            <div>Type: {document.document_type}</div>
            <div>Version: {document.current_version}</div>
          </li>
        ))}
      </ul>
    </section>
  )
}
