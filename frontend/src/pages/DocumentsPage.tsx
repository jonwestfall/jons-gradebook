import { FormEvent, useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'

type StudentTarget = {
  id: number
  name: string
  email?: string | null
}

type DocumentRow = {
  id: number
  title: string
  owner_type: string
  owner_id: number
  current_version: number
  document_type: string
  updated_at?: string | null
  created_at?: string | null
  linked_students: StudentTarget[]
  latest_version?: {
    version_number: number
    original_filename: string
    mime_type: string
    size_bytes: number
    checksum_sha256: string
    updated_at?: string | null
  } | null
}

export function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentRow[]>([])
  const [students, setStudents] = useState<StudentTarget[]>([])
  const [error, setError] = useState<string | null>(null)

  const [title, setTitle] = useState('')
  const [ownerType, setOwnerType] = useState('student')
  const [ownerId, setOwnerId] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [selectedStudentIds, setSelectedStudentIds] = useState<string[]>([])

  const [search, setSearch] = useState('')
  const [filterStudentId, setFilterStudentId] = useState('')
  const [filterDocType, setFilterDocType] = useState('')
  const [sortBy, setSortBy] = useState<'updated_at' | 'created_at' | 'title' | 'document_type' | 'current_version'>('updated_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  const selectedStudentsLabel = useMemo(() => {
    if (selectedStudentIds.length === 0) return 'No linked students selected'
    return students
      .filter((student) => selectedStudentIds.includes(String(student.id)))
      .map((student) => student.name)
      .join(', ')
  }, [selectedStudentIds, students])

  async function loadTargets() {
    const response = await api.get<{ students: StudentTarget[] }>('/documents/targets')
    setStudents(response.students)
    if (!ownerId && response.students.length > 0) {
      setOwnerId(String(response.students[0].id))
      setSelectedStudentIds([String(response.students[0].id)])
    }
  }

  async function loadDocuments() {
    const params = new URLSearchParams()
    if (search.trim()) params.set('search', search.trim())
    if (filterStudentId) params.set('student_id', filterStudentId)
    if (filterDocType) params.set('document_type', filterDocType)
    params.set('sort_by', sortBy)
    params.set('sort_order', sortOrder)
    params.set('limit', '1000')

    const rows = await api.get<DocumentRow[]>(`/documents/?${params.toString()}`)
    setDocuments(rows)
  }

  useEffect(() => {
    void Promise.all([loadTargets(), loadDocuments()]).catch((err) => setError((err as Error).message))
  }, [])

  async function upload(event: FormEvent) {
    event.preventDefault()
    if (!file) return

    const form = new FormData()
    form.append('owner_type', ownerType)
    form.append('owner_id', ownerId)
    form.append('title', title)
    form.append('linked_student_ids', selectedStudentIds.join(','))
    form.append('file', file)

    setError(null)
    try {
      await api.post('/documents/upload', form)
      setTitle('')
      setFile(null)
      await loadDocuments()
    } catch (err) {
      setError((err as Error).message)
    }
  }

  return (
    <section>
      <h2>Documents</h2>
      <p className="subtitle">Upload once, link to multiple students, and search/sort all stored documents from one view.</p>

      <article className="card">
        <h3>Upload Document</h3>
        <form className="form" onSubmit={upload}>
          <input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Document title" required />
          <select value={ownerType} onChange={(event) => setOwnerType(event.target.value)}>
            <option value="student">Student</option>
            <option value="advisee">Advisee</option>
            <option value="system">System</option>
          </select>
          <input value={ownerId} onChange={(event) => setOwnerId(event.target.value)} placeholder="Owner ID" required />

          <label>
            Linked Students (multi-select)
            <select
              multiple
              size={8}
              value={selectedStudentIds}
              onChange={(event) => {
                const values = Array.from(event.target.selectedOptions).map((option) => option.value)
                setSelectedStudentIds(values)
              }}
            >
              {students.map((student) => (
                <option key={student.id} value={student.id}>
                  {student.name}
                  {student.email ? ` (${student.email})` : ''}
                </option>
              ))}
            </select>
          </label>
          <div className="table-subtle">Selected: {selectedStudentsLabel}</div>

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
      </article>

      <article className="card" style={{ marginTop: '0.8rem' }}>
        <h3>Find Documents</h3>
        <div className="gradebook-toolbar compact-grid">
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search by title" />
          <select value={filterStudentId} onChange={(event) => setFilterStudentId(event.target.value)}>
            <option value="">All students</option>
            {students.map((student) => (
              <option key={student.id} value={student.id}>
                {student.name}
              </option>
            ))}
          </select>
          <select value={filterDocType} onChange={(event) => setFilterDocType(event.target.value)}>
            <option value="">All types</option>
            <option value="pdf">PDF</option>
            <option value="docx">DOCX</option>
            <option value="txt">TXT</option>
            <option value="other">Other</option>
          </select>
          <select value={sortBy} onChange={(event) => setSortBy(event.target.value as 'updated_at' | 'created_at' | 'title' | 'document_type' | 'current_version')}>
            <option value="updated_at">Sort by Updated</option>
            <option value="created_at">Sort by Created</option>
            <option value="title">Sort by Title</option>
            <option value="document_type">Sort by Type</option>
            <option value="current_version">Sort by Version</option>
          </select>
          <select value={sortOrder} onChange={(event) => setSortOrder(event.target.value as 'asc' | 'desc')}>
            <option value="desc">Descending</option>
            <option value="asc">Ascending</option>
          </select>
          <button type="button" onClick={() => void loadDocuments()}>
            Apply
          </button>
        </div>
      </article>

      {error ? <p className="error">{error}</p> : null}

      <article className="card students-grid-wrap" style={{ marginTop: '0.8rem' }}>
        <table className="students-grid-table">
          <thead>
            <tr>
              <th>Title</th>
              <th>Type</th>
              <th>Owner</th>
              <th>Students Linked</th>
              <th>Version</th>
              <th>Filename</th>
              <th>Size</th>
              <th>Updated</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((document) => (
              <tr key={document.id}>
                <td>{document.title}</td>
                <td>{document.document_type}</td>
                <td>
                  {document.owner_type}:{document.owner_id}
                </td>
                <td>
                  {document.linked_students.length > 0
                    ? document.linked_students.map((student) => student.name).join(', ')
                    : 'None'}
                </td>
                <td>{document.current_version}</td>
                <td>{document.latest_version?.original_filename || 'N/A'}</td>
                <td>{document.latest_version?.size_bytes ? `${document.latest_version.size_bytes.toLocaleString()} B` : 'N/A'}</td>
                <td>{document.updated_at ? new Date(document.updated_at).toLocaleString() : 'N/A'}</td>
                <td>
                  <div style={{ display: 'flex', gap: '0.45rem', flexWrap: 'wrap' }}>
                    <a href={`/api/v1/documents/${document.id}/download`} target="_blank" rel="noreferrer">
                      Download
                    </a>
                    <a href={`/api/v1/documents/${document.id}/text`} target="_blank" rel="noreferrer">
                      Text
                    </a>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {documents.length === 0 ? <p>No documents found.</p> : null}
      </article>
    </section>
  )
}
