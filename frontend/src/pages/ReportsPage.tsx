import { FormEvent, useState } from 'react'
import { api } from '../api/client'

export function ReportsPage() {
  const [studentId, setStudentId] = useState('')
  const [reportPaths, setReportPaths] = useState<{ pdf_path: string; png_path: string } | null>(null)

  async function generate(event: FormEvent) {
    event.preventDefault()
    const response = await api.post<{ pdf_path: string; png_path: string }>(`/reports/students/${studentId}`)
    setReportPaths(response)
  }

  return (
    <section>
      <h2>Student Reports</h2>
      <p>Generates branded PDF + PNG reports from current student profile data.</p>
      <form className="form" onSubmit={generate}>
        <input value={studentId} onChange={(event) => setStudentId(event.target.value)} placeholder="Student ID" required />
        <button type="submit">Generate Report</button>
      </form>
      {reportPaths ? (
        <article className="card">
          <div>PDF: {reportPaths.pdf_path}</div>
          <div>PNG: {reportPaths.png_path}</div>
        </article>
      ) : null}
    </section>
  )
}
