import { FormEvent, useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'

type StudentTarget = {
  id: number
  name: string
  email?: string | null
  student_number?: string | null
}

type AdviseeTarget = {
  id: number
  name: string
  student_profile_id?: number | null
}

type DocumentRow = {
  id: number
  title: string
  owner_type: string
  owner_id: number
  owner_name?: string | null
  category?: string
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

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentRow[]>([])
  const [students, setStudents] = useState<StudentTarget[]>([])
  const [advisees, setAdvisees] = useState<AdviseeTarget[]>([])
  const [documentCategories, setDocumentCategories] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)

  const [title, setTitle] = useState('')
  const [ownerType, setOwnerType] = useState('student')
  const [ownerId, setOwnerId] = useState('')
  const [category, setCategory] = useState('Other')
  const [file, setFile] = useState<File | null>(null)
  const [selectedStudentIds, setSelectedStudentIds] = useState<string[]>([])

  const [search, setSearch] = useState('')
  const [filterStudentId, setFilterStudentId] = useState('')
  const [filterDocType, setFilterDocType] = useState('')
  const [filterCategory, setFilterCategory] = useState('')
  const [personNameFilter, setPersonNameFilter] = useState('')
  const [sortBy, setSortBy] = useState<'updated_at' | 'created_at' | 'title' | 'document_type' | 'current_version'>('updated_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  const [selectedDocument, setSelectedDocument] = useState<DocumentRow | null>(null)
  const [previewText, setPreviewText] = useState('')
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)

  const selectedStudentsLabel = useMemo(() => {
    if (selectedStudentIds.length === 0) return 'No linked students selected'
    return students
      .filter((student) => selectedStudentIds.includes(String(student.id)))
      .map((student) => student.name)
      .join(', ')
  }, [selectedStudentIds, students])

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl)
      }
    }
  }, [previewUrl])

  async function loadTargets() {
    const response = await api.get<{
      students: StudentTarget[]
      advisees: AdviseeTarget[]
      document_categories: string[]
    }>('/documents/targets')
    setStudents(response.students)
    setAdvisees(response.advisees || [])
    setDocumentCategories(response.document_categories || ['Record', 'Assignment', 'Note', 'Other'])
    if ((response.document_categories || []).length > 0) {
      setCategory(response.document_categories[0])
    }
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
    if (filterCategory) params.set('category', filterCategory)
    if (personNameFilter.trim()) params.set('person_name', personNameFilter.trim())
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
    form.append('category', category)
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

  async function openPreview(document: DocumentRow) {
    setPreviewLoading(true)
    setError(null)
    setSelectedDocument(document)
    setPreviewText('')

    if (previewUrl) {
      URL.revokeObjectURL(previewUrl)
      setPreviewUrl(null)
    }

    try {
      const [textPayload] = await Promise.all([
        api.get<{ text: string }>(`/documents/${document.id}/text`),
      ])
      setPreviewText(textPayload.text || '')

      if (document.document_type === 'pdf') {
        const response = await fetch(`${API_BASE}/documents/${document.id}/download`)
        if (!response.ok) {
          throw new Error(`Preview download failed (${response.status})`)
        }
        const blob = await response.blob()
        setPreviewUrl(URL.createObjectURL(blob))
      }
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setPreviewLoading(false)
    }
  }

  return (
    <section>
      <h2>Documents</h2>
      <p className="subtitle">Upload once, link to multiple students, and preview extracted text and PDFs before download.</p>

      <article className="card">
        <h3>Upload Document</h3>
        <form className="form" onSubmit={upload}>
          <input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Document title" required />
          <select
            value={ownerType}
            onChange={(event) => {
              const nextType = event.target.value
              setOwnerType(nextType)
              if (nextType === 'student' && students.length > 0) {
                setOwnerId(String(students[0].id))
              } else if (nextType === 'advisee' && advisees.length > 0) {
                setOwnerId(String(advisees[0].id))
              } else if (nextType === 'system') {
                setOwnerId('1')
              }
            }}
          >
            <option value="student">Student</option>
            <option value="advisee">Advisee</option>
            <option value="system">System</option>
          </select>
          <div className="table-subtle">
            Owner guidance: choose `Student` for student files, `Advisee` for advising-only records, or `System` for general documents.
          </div>
          {ownerType === 'student' ? (
            <select value={ownerId} onChange={(event) => setOwnerId(event.target.value)} required>
              {students.map((student) => (
                <option key={student.id} value={student.id}>
                  {student.name} [{student.student_number || 'No ID#'}]
                </option>
              ))}
            </select>
          ) : ownerType === 'advisee' ? (
            <select value={ownerId} onChange={(event) => setOwnerId(event.target.value)} required>
              {advisees.map((advisee) => (
                <option key={advisee.id} value={advisee.id}>
                  {advisee.name}
                </option>
              ))}
            </select>
          ) : (
            <input value={ownerId} onChange={(event) => setOwnerId(event.target.value)} placeholder="System owner ID" required />
          )}

          <select value={category} onChange={(event) => setCategory(event.target.value)}>
            {documentCategories.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>

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

      <article className="card action-bar" style={{ marginTop: '0.8rem' }}>
        <h3>Find Documents</h3>
        <div className="gradebook-toolbar compact-grid">
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search by title" />
          <input
            value={personNameFilter}
            onChange={(event) => setPersonNameFilter(event.target.value)}
            placeholder="Filter by student/advisee name"
          />
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
          <select value={filterCategory} onChange={(event) => setFilterCategory(event.target.value)}>
            <option value="">All categories</option>
            {documentCategories.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
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
        <table className="students-grid-table prioritize-mobile">
          <thead>
            <tr>
              <th>Title</th>
              <th>Type</th>
              <th>Category</th>
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
                <td>{document.category || 'Other'}</td>
                <td>
                  {document.owner_type}:{document.owner_id}
                  {document.owner_name ? ` (${document.owner_name})` : ''}
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
                    <button type="button" onClick={() => void openPreview(document)}>Preview</button>
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

      {selectedDocument ? (
        <article className="card" style={{ marginTop: '0.8rem' }}>
          <h3>Quick Preview: {selectedDocument.title}</h3>
          {previewLoading ? <p>Loading preview...</p> : null}
          <div className="gradebook-layout" style={{ gridTemplateColumns: '1.2fr 1fr' }}>
            <div className="card">
              <h3>Document View</h3>
              {selectedDocument.document_type === 'pdf' && previewUrl ? (
                <iframe src={previewUrl} title="PDF preview" style={{ width: '100%', minHeight: '420px', border: '1px solid #d5c8aa' }} />
              ) : (
                <p className="table-subtle">
                  Inline preview available for PDF. Use Download for {selectedDocument.document_type.toUpperCase()} files.
                </p>
              )}
            </div>
            <div className="card" style={{ maxHeight: '460px', overflow: 'auto' }}>
              <h3>Extracted Text</h3>
              <pre>{previewText || 'No extracted text available.'}</pre>
            </div>
          </div>
        </article>
      ) : null}
    </section>
  )
}
