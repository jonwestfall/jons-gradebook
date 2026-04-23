import { FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'

type Course = {
  id: number
  name: string
  section_name?: string | null
  term_name?: string | null
  canvas_course_id?: string | null
}

export function CoursesPage() {
  const [courses, setCourses] = useState<Course[]>([])
  const [name, setName] = useState('')
  const [sectionName, setSectionName] = useState('')
  const [termName, setTermName] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function loadCourses() {
    try {
      setCourses(await api.get<Course[]>('/courses/'))
    } catch (err) {
      setError((err as Error).message)
    }
  }

  async function createCourse(event: FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      await api.post('/courses/', { name, section_name: sectionName || null, term_name: termName || null })
      setName('')
      setSectionName('')
      setTermName('')
      await loadCourses()
    } catch (err) {
      setError((err as Error).message)
    }
  }

  useEffect(() => {
    void loadCourses()
  }, [])

  return (
    <section>
      <h2>Courses</h2>
      <form className="form" onSubmit={createCourse}>
        <input placeholder="Course name" value={name} onChange={(event) => setName(event.target.value)} required />
        <input
          placeholder="Section name"
          value={sectionName}
          onChange={(event) => setSectionName(event.target.value)}
        />
        <input placeholder="Term" value={termName} onChange={(event) => setTermName(event.target.value)} />
        <button type="submit">Create Local Course</button>
      </form>
      {error ? <p className="error">{error}</p> : null}
      <ul className="list">
        {courses.map((course) => (
          <li key={course.id} className="card">
            <h3>{course.name}</h3>
            <div>Section: {course.section_name || 'N/A'}</div>
            <div>Term: {course.term_name || 'N/A'}</div>
            <div>Canvas ID: {course.canvas_course_id || 'Local-only'}</div>
            <div style={{ display: 'flex', gap: '0.6rem', marginTop: '0.5rem', flexWrap: 'wrap' }}>
              <Link to={`/courses/${course.id}/gradebook`}>Open Gradebook</Link>
              <Link to={`/courses/${course.id}/matches`}>Open Match Queue</Link>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
