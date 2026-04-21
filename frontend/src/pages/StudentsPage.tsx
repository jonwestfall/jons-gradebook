import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'

type Student = {
  id: number
  first_name: string
  last_name: string
  email?: string | null
}

export function StudentsPage() {
  const [students, setStudents] = useState<Student[]>([])

  useEffect(() => {
    api.get<Student[]>('/students/').then(setStudents).catch(console.error)
  }, [])

  return (
    <section>
      <h2>Students</h2>
      <ul className="list">
        {students.map((student) => (
          <li key={student.id} className="card">
            <h3>
              {student.first_name} {student.last_name}
            </h3>
            <div>{student.email || 'No email'}</div>
            <Link to={`/students/${student.id}`}>Open Profile</Link>
          </li>
        ))}
      </ul>
    </section>
  )
}
