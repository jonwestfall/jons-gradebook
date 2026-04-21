import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api/client'

type Profile = {
  student: { id: number; name: string; email?: string | null; student_number?: string | null }
  courses: { course_id: number; name: string; section_name?: string | null }[]
  recent_interactions: { id: number; type: string; summary: string; occurred_at: string }[]
  advising_meetings: { id: number; meeting_at: string; mode: string; summary?: string | null }[]
}

export function StudentProfilePage() {
  const { studentId } = useParams<{ studentId: string }>()
  const [profile, setProfile] = useState<Profile | null>(null)

  useEffect(() => {
    if (!studentId) return
    api.get<Profile>(`/students/${studentId}/profile`).then(setProfile).catch(console.error)
  }, [studentId])

  if (!profile) {
    return <p>Loading profile...</p>
  }

  return (
    <section>
      <h2>{profile.student.name}</h2>
      <p>Email: {profile.student.email || 'N/A'}</p>
      <p>Student number: {profile.student.student_number || 'N/A'}</p>

      <h3>Courses</h3>
      <ul className="list">
        {profile.courses.map((course) => (
          <li key={course.course_id} className="card">
            {course.name} ({course.section_name || 'No section'})
          </li>
        ))}
      </ul>

      <h3>Recent Interactions</h3>
      <ul className="list">
        {profile.recent_interactions.map((interaction) => (
          <li key={interaction.id} className="card">
            {interaction.type} - {interaction.summary}
          </li>
        ))}
      </ul>
    </section>
  )
}
