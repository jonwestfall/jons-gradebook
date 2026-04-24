import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { App } from './App'

function jsonResponse(payload: unknown): Response {
  return {
    ok: true,
    status: 200,
    json: async () => payload,
    text: async () => JSON.stringify(payload),
  } as Response
}

function mockApiFetch() {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)

    if (url.includes('/api/v1/dashboard/summary')) {
      return jsonResponse({
        cards: {
          needs_grading: 2,
          missing_late_followup: 4,
          out_of_sync_overrides: 1,
          unread_alerts: 0,
          upcoming_advising_followups: 3,
        },
        top_risk_students: [],
        latest_sync: null,
      })
    }

    if (url.includes('/api/v1/tasks/targets')) {
      return jsonResponse({ students: [], courses: [] })
    }

    if (url.includes('/api/v1/tasks/?')) {
      return jsonResponse([])
    }

    if (url.includes('/api/v1/documents/targets')) {
      return jsonResponse({ students: [{ id: 42, name: 'Ada Lovelace', email: 'ada@example.edu' }] })
    }

    if (url.includes('/api/v1/rubrics/evaluations?student_profile_id=42')) {
      return jsonResponse([
        {
          id: 7,
          rubric_id: 3,
          rubric_name: 'Research Rubric',
          rubric_max_points: 10,
          student_profile_id: 42,
          course_id: 1,
          course_name: 'Biology 101',
          assignment_id: 9,
          assignment_title: 'Lab Report',
          evaluator_notes: 'Strong evidence.',
          total_points: 8,
          created_at: '2026-04-24T12:00:00',
          items: [
            {
              id: 11,
              criterion_id: 5,
              criterion_title: 'Evidence',
              criterion_type: 'points',
              criterion_max_points: 5,
              rating_id: 6,
              rating_title: 'Proficient',
              rating_description: 'Uses relevant observations.',
              points_awarded: 4,
              is_checked: null,
              narrative_comment: null,
            },
          ],
        },
      ])
    }

    if (url.includes('/api/v1/students/42/profile')) {
      return jsonResponse({
        student: {
          id: 42,
          name: 'Ada Lovelace',
          first_name: 'Ada',
          last_name: 'Lovelace',
          email: 'ada@example.edu',
          phone_number: null,
          student_number: 'S-42',
          notes: 'Enjoys proofs.',
          is_advisee: false,
          advisee_id: null,
        },
        priority_sections: ['alerts', 'attendance_summary', 'recent_interactions', 'grade_overview'],
        alerts: [],
        flags_tags: [],
        attendance_summary: { present: 1, absent: 0, tardy: 0, excused: 0, total_records: 1 },
        courses: [
          {
            course_id: 1,
            name: 'Biology 101',
            section_name: 'A',
            totals: { earned: 8, possible: 10, percent: 80 },
            assignments: [
              {
                assignment_id: 9,
                title: 'Lab Report',
                source: 'local',
                due_at: null,
                points_possible: 10,
                score: 8,
                status: 'graded',
                percent: 80,
              },
            ],
          },
        ],
        grade_overview: [{ course_id: 1, course_name: 'Biology 101', earned: 8, possible: 10, percent: 80 }],
        student_documents: [],
        recent_interactions: [],
        advising_meetings: [],
      })
    }

    if (url.includes('/api/v1/courses/1/matches/history')) {
      return jsonResponse([])
    }

    if (url.includes('/api/v1/courses/1/matches')) {
      return jsonResponse([])
    }

    if (url.endsWith('/api/v1/courses/')) {
      return jsonResponse([{ id: 1, name: 'Biology 101', section_name: 'A' }])
    }

    return jsonResponse({})
  })
}

describe('App smoke routes', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', mockApiFetch())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders action dashboard on root route', async () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Action Dashboard')).toBeInTheDocument()
    expect(await screen.findByText('Needs Grading / Match Review')).toBeInTheDocument()
  })

  it('renders task queue route', async () => {
    render(
      <MemoryRouter initialEntries={['/tasks']}>
        <App />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Task Queue')).toBeInTheDocument()
    expect(await screen.findByText('Run Intervention Rules')).toBeInTheDocument()
  })

  it('renders course match workbench route', async () => {
    render(
      <MemoryRouter initialEntries={['/courses/1/matches']}>
        <App />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Match Queue Workbench')).toBeInTheDocument()
    expect(await screen.findByText('Refresh Suggestions')).toBeInTheDocument()
  })

  it('renders collapsible student profile areas with scored assignment rubrics', async () => {
    render(
      <MemoryRouter initialEntries={['/students/42']}>
        <App />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Ada Lovelace')).toBeInTheDocument()
    expect(await screen.findByText('Scored Assignment Rubrics')).toBeInTheDocument()
    expect((await screen.findAllByText('Lab Report')).length).toBeGreaterThan(0)
    expect(await screen.findByText('Research Rubric - 8 / 10')).toBeInTheDocument()
  })
})
