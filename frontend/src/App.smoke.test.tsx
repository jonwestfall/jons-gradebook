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
})
