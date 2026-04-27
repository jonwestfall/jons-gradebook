type HttpMethod = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'

type DemoTask = {
  id: number
  title: string
  status: string
  priority: string
  due_at: string | null
  note: string | null
  linked_student_id: number | null
  linked_course_id: number | null
  linked_interaction_id: number | null
  linked_advising_meeting_id: number | null
  source: string
  outcome_tag: string | null
  outcome_note: string | null
  created_at: string
  updated_at: string
}

const now = new Date('2026-04-27T14:30:00-05:00')

const students = [
  {
    id: 101,
    first_name: 'Maya',
    last_name: 'Chen',
    email: 'maya.chen@example.edu',
    phone_number: '(555) 014-2011',
    student_number: 'S-2026-014',
    has_class_enrollment: true,
    is_advisee: true,
    latest_interaction_at: '2026-04-25T16:30:00-05:00',
  },
  {
    id: 102,
    first_name: 'Jordan',
    last_name: 'Rivera',
    email: 'jordan.rivera@example.edu',
    phone_number: '(555) 014-2048',
    student_number: 'S-2026-029',
    has_class_enrollment: true,
    is_advisee: false,
    latest_interaction_at: '2026-04-20T09:15:00-05:00',
  },
  {
    id: 103,
    first_name: 'Priya',
    last_name: 'Nair',
    email: 'priya.nair@example.edu',
    phone_number: null,
    student_number: 'S-2026-031',
    has_class_enrollment: true,
    is_advisee: true,
    latest_interaction_at: '2026-04-26T11:05:00-05:00',
  },
  {
    id: 104,
    first_name: 'Elliot',
    last_name: 'Brooks',
    email: 'elliot.brooks@example.edu',
    phone_number: '(555) 014-2099',
    student_number: 'S-2026-044',
    has_class_enrollment: true,
    is_advisee: false,
    latest_interaction_at: null,
  },
]

const courses = [
  { id: 201, name: 'BIO 210: Research Methods', section_name: 'A', term_name: 'Spring 2026', canvas_course_id: 'canvas-bio-210-a' },
  { id: 202, name: 'PSY 330: Learning Analytics', section_name: 'B', term_name: 'Spring 2026', canvas_course_id: 'canvas-psy-330-b' },
  { id: 203, name: 'HON 101: Academic Success Studio', section_name: 'Seminar', term_name: 'Spring 2026', canvas_course_id: null },
]

const assignments = [
  { id: 301, title: 'Literature Matrix', source: 'canvas', due_at: '2026-04-18T23:59:00-05:00', points_possible: 20, grading_type: 'points', display_order: 1 },
  { id: 302, title: 'Methods Draft', source: 'local', due_at: '2026-04-25T23:59:00-05:00', points_possible: 30, grading_type: 'points', display_order: 2 },
  { id: 303, title: 'Lab Reflection', source: 'canvas', due_at: '2026-04-29T23:59:00-05:00', points_possible: 10, grading_type: 'completion', display_order: 3 },
]

const demoRubrics = [
  {
    id: 701,
    name: 'Research Methods Rubric',
    description: 'Scores evidence quality, analysis, and revision planning for research drafts.',
    max_points: 10,
    archived_at: null,
    is_archived: false,
    evaluation_count: 3,
    can_delete: false,
    criteria: [
      {
        id: 7101,
        title: 'Evidence Quality',
        criterion_type: 'points',
        max_points: 4,
        is_required: true,
        prompt: 'Evaluate source credibility, relevance, and integration.',
        display_order: 10,
        ratings: [
          { id: 7201, title: 'Exemplary', description: 'Evidence is credible, varied, and directly tied to claims.', points: 4, display_order: 10 },
          { id: 7202, title: 'Proficient', description: 'Evidence is relevant with minor gaps in integration.', points: 3, display_order: 20 },
          { id: 7203, title: 'Developing', description: 'Evidence is present but uneven or loosely connected.', points: 2, display_order: 30 },
        ],
      },
      {
        id: 7102,
        title: 'Analysis and Interpretation',
        criterion_type: 'points',
        max_points: 4,
        is_required: true,
        prompt: 'Look for clear interpretation, not just summary.',
        display_order: 20,
        ratings: [
          { id: 7204, title: 'Exemplary', description: 'Analysis explains why evidence matters and anticipates counterpoints.', points: 4, display_order: 10 },
          { id: 7205, title: 'Proficient', description: 'Analysis connects evidence to the central research question.', points: 3, display_order: 20 },
          { id: 7206, title: 'Needs Revision', description: 'Analysis is mostly descriptive or missing clear links.', points: 2, display_order: 30 },
        ],
      },
      {
        id: 7103,
        title: 'Revision Plan',
        criterion_type: 'narrative',
        max_points: null,
        is_required: false,
        prompt: 'Describe the next concrete revision step.',
        display_order: 30,
        ratings: [],
      },
    ],
  },
  {
    id: 702,
    name: 'Participation and Preparedness',
    description: 'Lightweight seminar rubric for attendance, preparation, and contribution quality.',
    max_points: 6,
    archived_at: null,
    is_archived: false,
    evaluation_count: 2,
    can_delete: true,
    criteria: [
      {
        id: 7301,
        title: 'Prepared for Discussion',
        criterion_type: 'checkbox',
        max_points: null,
        is_required: true,
        prompt: 'Student brought notes, questions, or relevant examples.',
        display_order: 10,
        ratings: [],
      },
      {
        id: 7302,
        title: 'Contribution Quality',
        criterion_type: 'points',
        max_points: 6,
        is_required: true,
        prompt: 'Evaluate whether contributions advanced the conversation.',
        display_order: 20,
        ratings: [
          { id: 7401, title: 'Strong', description: 'Specific, generous, and advances peer learning.', points: 6, display_order: 10 },
          { id: 7402, title: 'Adequate', description: 'Relevant but could be more specific.', points: 4, display_order: 20 },
          { id: 7403, title: 'Limited', description: 'Minimal contribution or mostly off-topic.', points: 2, display_order: 30 },
        ],
      },
    ],
  },
]

const archivedDemoRubrics = [
  {
    id: 703,
    name: 'Legacy Reflection Rubric',
    description: 'Older reflection rubric kept for report history examples.',
    max_points: 5,
    archived_at: '2026-03-15T10:00:00-05:00',
    is_archived: true,
    evaluation_count: 4,
    can_delete: false,
    criteria: [],
  },
]

const demoReportConfig = {
  metadata: {
    report_title: 'Student Progress Snapshot',
    footer_text: 'Demo University advising report - generated by Jon\'s Gradebook',
  },
  theme: {
    primary_color: '#175e73',
    accent_color: '#b66a2c',
    neutral_color: '#f8faf7',
    font_scale: 1,
    header_style: 'band',
    logo_asset_id: null,
  },
  sections: [
    { key: 'student_profile', label: 'Student Snapshot', enabled: true, order: 10, options: { show_email: true, show_courses: true } },
    { key: 'grade_overview', label: 'Grade Overview', enabled: true, order: 20, options: { limit: 8, show_scores: true } },
    { key: 'attendance', label: 'Attendance Pattern', enabled: true, order: 30, options: { show_empty: true } },
    { key: 'rubric_evaluations', label: 'Rubric Feedback', enabled: true, order: 40, options: { limit: 4, item_limit: 4, show_notes: true, show_scores: true } },
    { key: 'recent_interactions', label: 'Recent Interactions', enabled: true, order: 50, options: { limit: 5 } },
    { key: 'advising_meetings', label: 'Advising Meetings', enabled: true, order: 60, options: { limit: 5, show_action_items: true } },
    { key: 'tasks', label: 'Open Follow-Ups', enabled: true, order: 70, options: { limit: 5, show_done: false } },
    { key: 'linked_documents', label: 'Linked Documents', enabled: true, order: 80, options: { limit: 5 } },
  ],
}

const demoReportTemplates = [
  {
    id: 801,
    name: 'Progress Snapshot',
    description: 'Screenshot-ready student progress report with grades, attendance, rubric feedback, and follow-ups.',
    report_type: 'student',
    is_active: true,
    is_default: true,
    archived_at: null,
    config_json: demoReportConfig,
    logo_asset: null,
  },
  {
    id: 802,
    name: 'Advising Check-In',
    description: 'More advising-heavy variant with tasks and meeting notes emphasized.',
    report_type: 'student',
    is_active: true,
    is_default: false,
    archived_at: null,
    config_json: {
      ...demoReportConfig,
      metadata: { ...demoReportConfig.metadata, report_title: 'Advising Check-In Summary' },
      theme: { ...demoReportConfig.theme, primary_color: '#1f3d45', accent_color: '#6f7e2f', header_style: 'plain' },
    },
    logo_asset: null,
  },
]

const demoReportRuns = [
  {
    id: 901,
    student_id: 101,
    student_name: 'Maya Chen',
    template_id: 801,
    template_name: 'Progress Snapshot',
    pdf_url: '/demo/reports/maya-chen-progress.pdf',
    png_url: '/demo/reports/maya-chen-progress.png',
    pdf_document_id: 611,
    png_document_id: 612,
    created_at: '2026-04-26T15:30:00-05:00',
  },
  {
    id: 902,
    student_id: 103,
    student_name: 'Priya Nair',
    template_id: 802,
    template_name: 'Advising Check-In',
    pdf_url: '/demo/reports/priya-nair-check-in.pdf',
    png_url: '/demo/reports/priya-nair-check-in.png',
    pdf_document_id: 613,
    png_document_id: 614,
    created_at: '2026-04-25T11:40:00-05:00',
  },
]

let demoTasks: DemoTask[] = [
  {
    id: 701,
    title: 'Follow up on Methods Draft',
    status: 'open',
    priority: 'high',
    due_at: '2026-04-28T10:00:00-05:00',
    note: 'Maya has a strong outline but missing the analysis paragraph.',
    linked_student_id: 101,
    linked_course_id: 201,
    linked_interaction_id: null,
    linked_advising_meeting_id: null,
    source: 'rule_engine',
    outcome_tag: null,
    outcome_note: null,
    created_at: '2026-04-25T16:40:00-05:00',
    updated_at: '2026-04-25T16:40:00-05:00',
  },
  {
    id: 702,
    title: 'Check attendance pattern',
    status: 'in_progress',
    priority: 'medium',
    due_at: '2026-04-30T13:00:00-05:00',
    note: 'Two recent tardies; confirm transportation constraint.',
    linked_student_id: 103,
    linked_course_id: 203,
    linked_interaction_id: null,
    linked_advising_meeting_id: null,
    source: 'manual',
    outcome_tag: 'student_replied',
    outcome_note: null,
    created_at: '2026-04-26T11:12:00-05:00',
    updated_at: '2026-04-26T11:12:00-05:00',
  },
]

function dateDaysFromNow(days: number): string {
  const next = new Date(now)
  next.setDate(next.getDate() + days)
  return next.toISOString()
}

function studentName(student: (typeof students)[number]): string {
  return `${student.first_name} ${student.last_name}`
}

function studentTargets() {
  return students.map((student) => ({
    id: student.id,
    name: `${studentName(student)} (${student.student_number})`,
    email: student.email,
    student_number: student.student_number,
  }))
}

function courseTargets() {
  return courses.map((course) => ({ id: course.id, name: course.name, section_name: course.section_name }))
}

function dashboardSummary() {
  return {
    cards: {
      needs_grading: 5,
      missing_late_followup: 3,
      out_of_sync_overrides: 1,
      unread_alerts: 2,
      upcoming_advising_followups: 4,
    },
    top_risk_students: [
      {
        student_id: 101,
        student_name: 'Maya Chen',
        risk_score: 82,
        level: 'high',
        missing_assignments: 1,
        current_percent: 72.4,
        days_since_interaction: 2,
        reasons: ['missing Methods Draft section', 'grade below course target'],
      },
      {
        student_id: 103,
        student_name: 'Priya Nair',
        risk_score: 64,
        level: 'medium',
        missing_assignments: 0,
        current_percent: 84.2,
        days_since_interaction: 1,
        reasons: ['attendance trend', 'advising follow-up due'],
      },
      {
        student_id: 104,
        student_name: 'Elliot Brooks',
        risk_score: 58,
        level: 'medium',
        missing_assignments: 2,
        current_percent: 69.8,
        days_since_interaction: null,
        reasons: ['no recent interaction', 'two unsubmitted assignments'],
      },
    ],
    latest_sync: {
      id: 901,
      status: 'completed',
      started_at: '2026-04-27T08:15:00-05:00',
      finished_at: '2026-04-27T08:16:24-05:00',
    },
  }
}

function profileFor(studentId: number) {
  const student = students.find((item) => item.id === studentId) || students[0]
  const isMaya = student.id === 101

  return {
    student: {
      id: student.id,
      name: studentName(student),
      first_name: student.first_name,
      last_name: student.last_name,
      email: student.email,
      phone_number: student.phone_number,
      student_number: student.student_number,
      institution_name: 'Demo University',
      notes: isMaya ? 'Prefers written feedback before office-hour meetings. Strong research questions; needs help narrowing evidence.' : 'Demo profile notes for screenshot review.',
      is_advisee: student.is_advisee,
      advisee_id: student.is_advisee ? 501 + student.id : null,
    },
    priority_sections: ['alerts', 'attendance_summary', 'recent_interactions', 'grade_overview'],
    alerts: isMaya
      ? [
          {
            id: 801,
            title: 'Methods draft needs revision plan',
            message: 'Schedule a 15-minute check-in and confirm the analysis paragraph is scoped.',
            severity: 'high',
            status: 'active',
            is_pinned: true,
            created_at: '2026-04-25T16:40:00-05:00',
          },
          {
            id: 802,
            title: 'Scholarship reflection due soon',
            message: 'Student asked for a reminder before the Friday deadline.',
            severity: 'medium',
            status: 'active',
            is_pinned: false,
            created_at: '2026-04-24T12:00:00-05:00',
          },
        ]
      : [],
    flags_tags: isMaya ? [{ id: 11, name: 'Research support' }, { id: 12, name: 'Advising priority' }] : [{ id: 13, name: 'Demo learner' }],
    attendance_summary: { present: 22, absent: isMaya ? 1 : 0, tardy: isMaya ? 2 : 1, excused: 1, total_records: 26 },
    courses: [
      {
        course_id: 201,
        name: 'BIO 210: Research Methods',
        section_name: 'A',
        totals: { earned: isMaya ? 52 : 63, possible: 70, percent: isMaya ? 74.29 : 90 },
        assignments: assignments.map((assignment, index) => ({
          assignment_id: assignment.id,
          title: assignment.title,
          source: assignment.source,
          due_at: assignment.due_at,
          points_possible: assignment.points_possible,
          score: isMaya ? [17, 25, null][index] : [19, 28, 10][index],
          status: isMaya && index === 2 ? 'unsubmitted' : 'graded',
          percent: isMaya ? [85, 83.33, null][index] : [95, 93.33, 100][index],
        })),
      },
      {
        course_id: 203,
        name: 'HON 101: Academic Success Studio',
        section_name: 'Seminar',
        totals: { earned: 41, possible: 45, percent: 91.11 },
        assignments: [
          {
            assignment_id: 401,
            title: 'Goal Map',
            source: 'local',
            due_at: dateDaysFromNow(-7),
            points_possible: 15,
            score: 14,
            status: 'graded',
            percent: 93.33,
          },
        ],
      },
    ],
    grade_overview: [
      { course_id: 201, course_name: 'BIO 210: Research Methods', earned: isMaya ? 52 : 63, possible: 70, percent: isMaya ? 74.29 : 90 },
      { course_id: 203, course_name: 'HON 101: Academic Success Studio', earned: 41, possible: 45, percent: 91.11 },
    ],
    student_documents: [
      {
        id: 601,
        title: 'Methods Draft Feedback',
        category: 'Feedback',
        document_type: 'txt',
        current_version: 2,
        updated_at: '2026-04-25T17:15:00-05:00',
        latest_filename: 'methods-feedback.txt',
        latest_size_bytes: 1842,
      },
    ],
    recent_interactions: [
      { id: 901, type: 'Office Visit', summary: 'Discussed narrowing research question and next evidence pass.', occurred_at: '2026-04-25T16:30:00-05:00' },
      { id: 902, type: 'Email Log', summary: 'Sent rubric-linked checklist for Methods Draft revision.', occurred_at: '2026-04-24T10:05:00-05:00' },
    ],
    advising_meetings: [
      { id: 1001, meeting_at: '2026-04-30T14:00:00-05:00', mode: 'in_person', summary: 'Plan final project milestones.' },
    ],
  }
}

function gradebookFor(courseId: number) {
  return {
    course: courses.find((course) => course.id === courseId) || courses[0],
    assignments,
    calculated_columns: [
      { id: 501, name: 'Current %', operation: 'average_percent', assignment_ids: assignments.map((assignment) => assignment.id), display_order: 1 },
    ],
    students: students.slice(0, 4).map((student, index) => {
      const scores = [
        [17, 25, null],
        [19, 28, 10],
        [20, 27, 9],
        [15, null, null],
      ][index]
      const earned = scores.reduce<number>((sum, score) => sum + (typeof score === 'number' ? score : 0), 0)
      const possible = 60
      return {
        student_id: student.id,
        name: studentName(student),
        totals: { earned, possible, percent: Math.round((earned / possible) * 10000) / 100 },
        warnings: index === 0 ? ['One unsubmitted item'] : index === 3 ? ['Missing Methods Draft'] : [],
        assignments: assignments.map((assignment, assignmentIndex) => ({
          assignment_id: assignment.id,
          status: scores[assignmentIndex] === null ? 'missing' : 'graded',
          score: assignment.grading_type === 'points' ? scores[assignmentIndex] : null,
          letter_grade: null,
          completion_status: assignment.grading_type === 'completion' ? (scores[assignmentIndex] === null ? 'missing' : 'complete') : null,
          grade_source: assignment.source === 'canvas' ? 'canvas' : 'local',
          is_out_of_sync: student.id === 101 && assignment.id === 301,
        })),
        calculated_values: [{ column_id: 501, display: `${Math.round((earned / possible) * 100)}%`, value: earned / possible }],
      }
    }),
  }
}

function rubricEvaluations() {
  return [
    {
      id: 801,
      rubric_id: 701,
      rubric_name: 'Research Methods Rubric',
      rubric_max_points: 10,
      student_profile_id: 101,
      course_id: 201,
      course_name: 'BIO 210: Research Methods',
      assignment_id: 302,
      assignment_title: 'Methods Draft',
      evaluator_notes: 'Strong question and source selection. Needs tighter analysis paragraph.',
      total_points: 8,
      created_at: '2026-04-25T17:00:00-05:00',
      items: [
        {
          id: 1,
          criterion_id: 1,
          criterion_title: 'Evidence',
          criterion_type: 'points',
          criterion_max_points: 5,
          rating_id: 2,
          rating_title: 'Proficient',
          rating_description: 'Uses relevant observations and credible sources.',
          points_awarded: 4,
          is_checked: null,
          narrative_comment: null,
        },
        {
          id: 2,
          criterion_id: 2,
          criterion_title: 'Analysis',
          criterion_type: 'points',
          criterion_max_points: 5,
          rating_id: 3,
          rating_title: 'Developing',
          rating_description: 'Claims are visible but need clearer evidence links.',
          points_awarded: 4,
          is_checked: null,
          narrative_comment: null,
        },
      ],
    },
    {
      id: 802,
      rubric_id: 702,
      rubric_name: 'Participation and Preparedness',
      max_points: 6,
      rubric_max_points: 6,
      student_profile_id: 103,
      student_name: 'Priya Nair',
      course_id: 203,
      course_name: 'HON 101: Academic Success Studio',
      assignment_id: 401,
      assignment_title: 'Goal Map',
      evaluator_notes: 'Prepared, thoughtful, and helped peers compare planning strategies.',
      total_points: 6,
      created_at: '2026-04-26T12:00:00-05:00',
      items: [
        {
          id: 3,
          criterion_id: 7301,
          criterion_title: 'Prepared for Discussion',
          criterion_type: 'checkbox',
          criterion_max_points: null,
          rating_id: null,
          rating_title: 'Checked',
          rating_description: 'Brought annotated planning notes.',
          points_awarded: null,
          is_checked: true,
          narrative_comment: 'Brought annotated planning notes.',
        },
        {
          id: 4,
          criterion_id: 7302,
          criterion_title: 'Contribution Quality',
          criterion_type: 'points',
          criterion_max_points: 6,
          rating_id: 7401,
          rating_title: 'Strong',
          rating_description: 'Specific, generous, and advances peer learning.',
          points_awarded: 6,
          is_checked: null,
          narrative_comment: null,
        },
      ],
    },
  ]
}

function attendanceRollCall(courseId: number, meetingId?: number) {
  const meetingIds = [3001, 3002, 3003]
  const activeMeetingId = meetingId && meetingIds.includes(meetingId) ? meetingId : 3002
  const activeIndex = meetingIds.indexOf(activeMeetingId)
  const statusByStudent = [
    ['present', 'present', 'tardy'],
    ['present', 'absent', 'present'],
    ['tardy', 'present', 'present'],
    ['excused', 'present', 'unmarked'],
  ] as const

  return {
    course: {
      ...(courses.find((course) => course.id === courseId) || courses[0]),
      attendance_lateness_weight: 0.8,
      attendance_excluded_from_final_grade: false,
    },
    lateness_weight: 0.8,
    meetings: [
      { id: 3001, meeting_date: '2026-04-21', is_generated: true, is_canceled: false },
      { id: 3002, meeting_date: '2026-04-23', is_generated: true, is_canceled: false },
      { id: 3003, meeting_date: '2026-04-28', is_generated: false, is_canceled: false },
    ],
    active_meeting_id: activeMeetingId,
    students: students.map((student, index) => {
      const statuses = statusByStudent[index]
      const counts = {
        present: statuses.filter((status) => status === 'present').length + 20 - index,
        absent: statuses.filter((status) => status === 'absent').length,
        tardy: statuses.filter((status) => status === 'tardy').length,
        excused: statuses.filter((status) => status === 'excused').length,
        unmarked: statuses.filter((status) => status === 'unmarked').length,
      }
      const counted = counts.present + counts.absent + counts.tardy
      const attendancePercent = counted > 0 ? Math.round(((counts.present + counts.tardy * 0.8) / counted) * 1000) / 10 : null
      return {
        student_id: student.id,
        name: studentName(student),
        email: student.email,
        status: statuses[activeIndex],
        note:
          student.id === 103 && statuses[activeIndex] === 'present'
            ? 'Asked a strong peer-review question.'
            : student.id === 102 && statuses[activeIndex] === 'absent'
              ? 'Emailed ahead about illness.'
              : null,
        counts,
        attendance_percent: attendancePercent,
      }
    }),
  }
}

function reportResultFor(studentId: number, templateId: number) {
  const student = students.find((row) => row.id === studentId) || students[0]
  return {
    run_id: 980 + student.id,
    student_id: student.id,
    pdf_url: `/demo/reports/${student.last_name.toLowerCase()}-${student.first_name.toLowerCase()}.pdf`,
    png_url: `/demo/reports/${student.last_name.toLowerCase()}-${student.first_name.toLowerCase()}.png`,
    pdf_document_id: 690 + student.id,
    png_document_id: 790 + student.id,
    rubric_evaluation_count: rubricEvaluations().filter((row) => !row.student_profile_id || row.student_profile_id === student.id).length,
    interaction_count: profileFor(student.id).recent_interactions.length,
    template_id: templateId,
  }
}

function settingsOptions() {
  return {
    document_categories: ['Record', 'Assignment', 'Feedback', 'Advising', 'Other'],
    interaction_categories: ['Office Visit', 'Email Log', 'Advising Meeting', 'Attendance', 'Phone Call'],
    intervention_rules: [
      {
        name: 'missing-and-low-grade',
        min_score: 60,
        priority: 'high',
        due_days: 2,
        template: 'Follow up with student on missing work and recovery plan.',
      },
    ],
  }
}

function noOpResult(path: string, method: HttpMethod, body?: unknown) {
  if (path === '/tasks/rules/run') return { created_count: 1, skipped_count: 1, evaluated_students: students.length }
  if (path === '/tasks/bulk') return { updated_count: demoTasks.length, missing_ids: [] }
  if (path === '/reports/students/bulk') {
    return {
      created_count: students.length,
      artifacts: students.map((student) => ({
        run_id: 1000 + student.id,
        student_id: student.id,
        student_name: studentName(student),
        pdf_url: `/demo/reports/${student.last_name.toLowerCase()}-${student.first_name.toLowerCase()}.pdf`,
        png_url: `/demo/reports/${student.last_name.toLowerCase()}-${student.first_name.toLowerCase()}.png`,
        pdf_document_id: 1500 + student.id,
        png_document_id: 1600 + student.id,
      })),
    }
  }
  if (path.match(/^\/reports\/students\/\d+$/)) {
    const studentId = Number(path.split('/')[3])
    const templateId =
      body && typeof body === 'object' && 'template_id' in body
        ? Number((body as { template_id?: unknown }).template_id)
        : demoReportTemplates[0].id
    return reportResultFor(studentId, templateId)
  }
  if (path.match(/^\/reports\/templates\/\d+\/duplicate$/)) {
    return { ...demoReportTemplates[0], id: 899, name: `${demoReportTemplates[0].name} Copy`, is_default: false }
  }
  if (path === '/reports/templates' && method === 'POST') {
    return { ...demoReportTemplates[0], id: 898, name: 'Custom Student Report', is_default: false }
  }
  if (path.match(/^\/reports\/templates\/\d+$/)) return demoReportTemplates[0]
  if (path.match(/^\/reports\/templates\/\d+\/assets\/logo$/)) return demoReportTemplates[0]
  if (path === '/attendance/records') return { ok: true, demo_mode: true }
  if (path.match(/^\/attendance\/meetings\/\d+\/mark-all-present$/)) return { ok: true, demo_mode: true }
  if (path.match(/^\/attendance\/meetings\/\d+\/unmark-all$/)) return { ok: true, demo_mode: true }
  if (path === '/attendance/meetings') return { id: 3099, meeting_date: '2026-04-30', is_generated: false, is_canceled: false }
  if (path.match(/^\/attendance\/courses\/\d+\/settings$/)) return { ok: true, demo_mode: true }
  if (path === '/courses/meetings/generate') return { generated_count: 6 }
  if (path === '/rubrics/') return demoRubrics[0]
  if (path.match(/^\/rubrics\/\d+/)) return demoRubrics[0]
  if (path === '/backup/restore') return { restored_tables: 0, restored_files: 0, generated_at: now.toISOString() }
  if (path === '/backup/') return { id: 990, backup_path: 'demo://backup', checksum_sha256: 'demo-mode', encrypted: true, created_at: now.toISOString(), note: 'Demo backup artifact' }
  if (path === '/tasks/' && method === 'POST' && body && typeof body === 'object') {
    const next: DemoTask = {
      id: 900 + demoTasks.length,
      title: 'New demo task',
      status: 'open',
      priority: 'medium',
      due_at: null,
      note: null,
      linked_student_id: null,
      linked_course_id: null,
      linked_interaction_id: null,
      linked_advising_meeting_id: null,
      source: 'manual',
      outcome_tag: null,
      outcome_note: null,
      created_at: now.toISOString(),
      updated_at: now.toISOString(),
      ...(body as Record<string, unknown>),
    }
    demoTasks = [next, ...demoTasks]
    return next
  }
  return { ok: true, demo_mode: true }
}

export function handleDemoRequest(path: string, init?: RequestInit): unknown {
  const method = ((init?.method || 'GET').toUpperCase() || 'GET') as HttpMethod
  const url = new URL(path, 'http://demo.local')
  const pathname = url.pathname
  const body = init?.body && typeof init.body === 'string' ? JSON.parse(init.body) : undefined

  if (method !== 'GET') return noOpResult(pathname, method, body)

  if (pathname === '/dashboard/summary') return dashboardSummary()
  if (pathname === '/students/') return students
  if (pathname.match(/^\/students\/\d+\/profile$/)) return profileFor(Number(pathname.split('/')[2]))
  if (pathname === '/courses/') return courses
  if (pathname.match(/^\/courses\/\d+\/gradebook$/)) return gradebookFor(Number(pathname.split('/')[2]))
  if (pathname.match(/^\/courses\/\d+\/grade-audits$/)) return []
  if (pathname.match(/^\/courses\/\d+\/matches$/)) return []
  if (pathname.match(/^\/courses\/\d+\/matches\/history$/)) return []
  if (pathname.match(/^\/courses\/\d+\/message-candidates$/)) {
    return { count: 2, candidates: [{ student_id: 101, student_name: 'Maya Chen', status: 'missing', score: null, reason: 'Missing Lab Reflection' }] }
  }
  if (pathname === '/tasks/targets') return { students: studentTargets(), courses: courseTargets() }
  if (pathname === '/tasks/') return demoTasks
  if (pathname === '/documents/targets') return { students: studentTargets(), document_categories: settingsOptions().document_categories }
  if (pathname === '/documents/') {
    return [
      {
        id: 601,
        title: 'Methods Draft Feedback',
        category: 'Feedback',
        document_type: 'txt',
        owner_type: 'student',
        owner_id: 101,
        owner_label: 'Maya Chen (S-2026-014)',
        linked_student_ids: [101],
        updated_at: '2026-04-25T17:15:00-05:00',
        current_version: 2,
        latest_filename: 'methods-feedback.txt',
        latest_size_bytes: 1842,
      },
    ]
  }
  if (pathname.match(/^\/documents\/\d+\/text$/)) return { text: 'Demo extracted text: targeted feedback on the Methods Draft, ready for screenshot review.' }
  if (pathname === '/settings/options') return settingsOptions()
  if (pathname === '/backup/') return []
  if (pathname === '/rubrics/evaluations') {
    const rubricId = url.searchParams.get('rubric_id')
    const rows = rubricEvaluations()
    return rubricId ? rows.filter((row) => String(row.rubric_id) === rubricId) : rows
  }
  if (pathname === '/reports/targets') {
    return {
      students: studentTargets(),
      rubrics: demoRubrics.map((rubric) => ({ id: rubric.id, name: rubric.name })),
      assignments: assignments.map((assignment) => ({ ...assignment, course_id: 201 })),
      templates: demoReportTemplates,
    }
  }
  if (pathname === '/reports/templates') return demoReportTemplates
  if (pathname === '/reports/runs') return demoReportRuns
  if (pathname.match(/^\/reports\/students\/\d+\/preview$/)) {
    const profile = profileFor(Number(pathname.split('/')[3]))
    const includeAllRubrics = url.searchParams.get('include_all_rubrics') !== 'false'
    const targetRubricId = url.searchParams.get('rubric_id')
    const evaluations = rubricEvaluations().filter((row) => {
      if (row.student_profile_id && row.student_profile_id !== profile.student.id) return false
      if (!includeAllRubrics && targetRubricId && String(row.rubric_id) !== targetRubricId) return false
      return true
    })
    return {
      student_id: profile.student.id,
      student_name: profile.student.name,
      student_number: profile.student.student_number,
      courses: profile.courses.map((course) => course.name),
      grade_overview: profile.grade_overview,
      attendance: profile.attendance_summary,
      rubric_scope: { include_all_rubrics: true, rubric_id: null, assignment_id: null },
      rubric_evaluations: evaluations,
      recent_interactions: profile.recent_interactions,
      advising_meetings: profile.advising_meetings.map((meeting) => ({
        ...meeting,
        action_items: 'Confirm revision plan, then send a concise rubric-aligned note.',
      })),
      tasks: demoTasks,
      linked_documents: profile.student_documents,
    }
  }
  if (pathname === '/interactions/targets') return { students: studentTargets(), courses: courseTargets(), advisees: studentTargets().filter((student) => student.id !== 102) }
  if (pathname === '/interactions/') return profileFor(101).recent_interactions
  if (pathname === '/advising/advisees') {
    return students.filter((student) => student.is_advisee).map((student) => ({ id: 501 + student.id, student_profile_id: student.id, student_name: studentName(student), email: student.email, student_number: student.student_number }))
  }
  if (pathname === '/advising/meetings') return profileFor(101).advising_meetings
  if (pathname === '/attendance/courses') return courseTargets()
  if (pathname.match(/^\/attendance\/rollcall\/\d+$/)) {
    return attendanceRollCall(Number(pathname.split('/')[3]), Number(url.searchParams.get('meeting_id') || '') || undefined)
  }
  if (pathname === '/canvas/sync/runs') return [dashboardSummary().latest_sync]
  if (pathname.match(/^\/canvas\/sync\/runs\/\d+$/)) return { id: 901, snapshot_counts: { courses: 3, assignments: 12, enrollments: 48, submissions: 144 }, event_counts: { created: 8, updated: 16, deleted: 0 }, recent_events: [] }
  if (pathname.match(/^\/canvas\/sync\/runs\/\d+\/events$/)) return { total: 0, offset: 0, limit: 50, events: [] }
  if (pathname.match(/^\/canvas\/sync\/runs\/\d+\/conflicts$/)) return []
  if (pathname.match(/^\/canvas\/sync\/runs\/\d+\/diff$/)) return { run_id: 901, previous_run_id: 900, entity_type: 'submission', rows: [] }
  if (pathname === '/canvas/courses/discover') return courses.map((course) => ({ canvas_course_id: course.canvas_course_id || `local-${course.id}`, name: course.name, is_selected: true }))
  if (pathname === '/canvas/student-metadata/mapping') return { mappings: [], common_source_paths: ['user.name', 'user.email', 'sis_user_id'] }
  if (pathname === '/canvas/student-metadata/preview') return { canvas_course_id: 'canvas-bio-210-a', sample_count: 0, labels: [], rows: [] }
  if (pathname === '/llm/targets') return { students: studentTargets(), documents: [], rubrics: demoRubrics.map((rubric) => ({ id: rubric.id, name: rubric.name, description: rubric.description, max_points: rubric.max_points })), providers: [{ value: 'ollama', label: 'Ollama', default_model: 'llama3.1', local: true }] }
  if (pathname === '/llm/instructions') return []
  if (pathname === '/llm/workbench/jobs') return []
  if (pathname === '/rubrics/') {
    return url.searchParams.get('archive_state') === 'archived' ? archivedDemoRubrics : demoRubrics
  }
  if (pathname === '/rubrics/targets') return { students: studentTargets(), courses: courseTargets(), assignments: assignments.map((assignment) => ({ ...assignment, course_id: 201 })) }

  return {}
}
