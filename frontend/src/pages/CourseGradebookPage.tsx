import { FormEvent, KeyboardEvent, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { readLocalStorage, writeLocalStorage } from '../utils/storage'

type AssignmentMeta = {
  id: number
  title: string
  source: 'canvas' | 'local'
  due_at?: string | null
  points_possible?: number | null
  grading_type: 'points' | 'letter' | 'completion'
  display_order?: number
}

type CalculatedColumn = {
  id: number
  name: string
  operation: 'average_percent' | 'sum_points' | 'completion_rate'
  assignment_ids: number[]
  display_order: number
}

type StudentAssignment = {
  assignment_id: number
  status: 'graded' | 'missing' | 'excused' | 'unsubmitted'
  score?: number | null
  letter_grade?: string | null
  completion_status?: 'complete' | 'incomplete' | 'missing' | 'excused' | null
  grade_source?: 'canvas' | 'local' | 'manual_override' | null
  is_out_of_sync?: boolean
}

type StudentCalculatedValue = {
  column_id: number
  display: string
  value?: number | null
}

type GradebookPayload = {
  course: { id: number; name: string; section_name?: string | null }
  assignments: AssignmentMeta[]
  calculated_columns: CalculatedColumn[]
  students: {
    student_id: number
    name: string
    totals: { earned: number; possible: number; percent?: number | null }
    warnings: string[]
    assignments: StudentAssignment[]
    calculated_values: StudentCalculatedValue[]
  }[]
}

type ActiveEditor = {
  rowIndex: number
  colIndex: number
  studentId: number
  studentName: string
  assignment: AssignmentMeta
  current?: StudentAssignment
}

type ColumnDef =
  | { kind: 'assignment'; id: number; assignment: AssignmentMeta }
  | { kind: 'calculated'; id: number; calculated: CalculatedColumn }

type GradeAudit = {
  id: number
  assignment_id: number
  assignment_title?: string | null
  student_id: number
  student_name?: string | null
  action: string
  before: Record<string, unknown>
  after: Record<string, unknown>
  was_undone: boolean
  created_at: string
}

type MessageFilterKind = 'not_submitted' | 'not_graded' | 'missing' | 'score_below' | 'score_above'

type MessageCandidate = {
  student_id: number
  student_name: string
  status: string
  score?: number | null
  reason: string
}

type SavedGradebookView = {
  name: string
  studentSearch: string
  assignmentSearch: string
  rowSortColumn: 'student_lastname' | 'student_name' | 'percent'
  rowSortDirection: 'asc' | 'desc'
}

function parseName(fullName: string) {
  const parts = fullName.trim().split(/\s+/)
  const first = parts[0] || ''
  const last = parts.length > 1 ? parts[parts.length - 1] : first
  return { first, last }
}

function moveId(order: number[], draggedId: number, targetId: number): number[] {
  if (draggedId === targetId) return order
  const next = order.filter((id) => id !== draggedId)
  const targetIndex = next.indexOf(targetId)
  if (targetIndex < 0) {
    next.push(draggedId)
    return next
  }
  next.splice(targetIndex, 0, draggedId)
  return next
}

function normalizeCompletionStatus(entry?: StudentAssignment): 'complete' | 'incomplete' | 'missing' | 'excused' {
  if (entry?.completion_status) return entry.completion_status
  if (entry?.status === 'missing') return 'missing'
  if (entry?.status === 'excused') return 'excused'
  return 'incomplete'
}

function nextCompletionStatus(current: 'complete' | 'incomplete' | 'missing' | 'excused') {
  if (current === 'complete') return 'incomplete'
  if (current === 'incomplete') return 'missing'
  if (current === 'missing') return 'excused'
  return 'complete'
}

function renderAssignmentValue(entry: StudentAssignment | undefined, assignment: AssignmentMeta): string {
  if (!entry) return '—'

  if (assignment.grading_type === 'points') {
    if (entry.score !== null && entry.score !== undefined) return String(entry.score)
    if (entry.status === 'excused') return 'EX'
    if (entry.status === 'missing') return 'M'
    return '—'
  }

  if (assignment.grading_type === 'letter') {
    if (entry.letter_grade) return entry.letter_grade
    if (entry.status === 'excused') return 'EX'
    if (entry.status === 'missing') return 'M'
    return '—'
  }

  if (entry.completion_status === 'complete') return 'Complete'
  if (entry.completion_status === 'incomplete') return 'Incomplete'
  if (entry.completion_status === 'missing') return 'Missing'
  if (entry.completion_status === 'excused') return 'Excused'
  return 'Incomplete'
}

export function CourseGradebookPage() {
  const { courseId } = useParams<{ courseId: string }>()

  const [gradebook, setGradebook] = useState<GradebookPayload | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [studentSearch, setStudentSearch] = useState('')
  const [assignmentSearch, setAssignmentSearch] = useState('')
  const [rowSortColumn, setRowSortColumn] = useState<'student_lastname' | 'student_name' | 'percent'>('student_lastname')
  const [rowSortDirection, setRowSortDirection] = useState<'asc' | 'desc'>('asc')

  const [assignmentOrder, setAssignmentOrder] = useState<number[]>([])
  const [calculatedOrder, setCalculatedOrder] = useState<number[]>([])

  const [activeCell, setActiveCell] = useState<{ row: number; col: number } | null>(null)
  const [activeEditor, setActiveEditor] = useState<ActiveEditor | null>(null)
  const [savingGrade, setSavingGrade] = useState(false)
  const [editStatus, setEditStatus] = useState<'graded' | 'missing' | 'excused' | 'unsubmitted'>('graded')
  const [editScore, setEditScore] = useState('')
  const [editLetter, setEditLetter] = useState('')
  const [editCompletion, setEditCompletion] = useState<'complete' | 'incomplete' | 'missing' | 'excused'>('incomplete')

  const [newTitle, setNewTitle] = useState('')
  const [newDueAt, setNewDueAt] = useState('')
  const [newPoints, setNewPoints] = useState('100')
  const [newGradingType, setNewGradingType] = useState<'points' | 'letter' | 'completion'>('points')
  const [creatingAssignment, setCreatingAssignment] = useState(false)

  const [calcEditId, setCalcEditId] = useState<number | null>(null)
  const [calcName, setCalcName] = useState('')
  const [calcOperation, setCalcOperation] = useState<'average_percent' | 'sum_points' | 'completion_rate'>('average_percent')
  const [calcAssignmentIds, setCalcAssignmentIds] = useState<number[]>([])
  const [savingCalc, setSavingCalc] = useState(false)
  const [dragColumn, setDragColumn] = useState<ColumnDef | null>(null)
  const [showDetailsPane, setShowDetailsPane] = useState(true)
  const [detailsPaneExpanded, setDetailsPaneExpanded] = useState(false)
  const [showReorderArrows, setShowReorderArrows] = useState(false)

  const [audits, setAudits] = useState<GradeAudit[]>([])
  const [loadingAudits, setLoadingAudits] = useState(false)
  const [undoBusyId, setUndoBusyId] = useState<number | null>(null)

  const [messageAssignmentId, setMessageAssignmentId] = useState<number | null>(null)
  const [messageFilterKind, setMessageFilterKind] = useState<MessageFilterKind>('not_submitted')
  const [messageThreshold, setMessageThreshold] = useState('70')
  const [messageIncludeExcused, setMessageIncludeExcused] = useState(false)
  const [messageSubject, setMessageSubject] = useState('Gradebook follow-up')
  const [messageBody, setMessageBody] = useState('Please review your assignment status and follow up if you need support.')
  const [messageTemplateName, setMessageTemplateName] = useState('General reminder')
  const [messageRecurrenceDays, setMessageRecurrenceDays] = useState('7')
  const [messageCreateTask, setMessageCreateTask] = useState(true)
  const [messageCandidates, setMessageCandidates] = useState<MessageCandidate[]>([])
  const [messageBusy, setMessageBusy] = useState(false)
  const [messageResult, setMessageResult] = useState<string | null>(null)

  const [savedViews, setSavedViews] = useState<SavedGradebookView[]>([])
  const [viewName, setViewName] = useState('')

  async function loadGradebook() {
    if (!courseId) return
    try {
      const data = await api.get<GradebookPayload>(`/courses/${courseId}/gradebook`)
      setGradebook(data)
      setAssignmentOrder(data.assignments.map((a) => a.id))
      setCalculatedOrder(data.calculated_columns.map((c) => c.id))
      if (!messageAssignmentId && data.assignments.length > 0) {
        setMessageAssignmentId(data.assignments[0].id)
      }
      setError(null)
    } catch (err) {
      setError((err as Error).message)
    }
  }

  async function loadAudits() {
    if (!courseId) return
    setLoadingAudits(true)
    try {
      const rows = await api.get<GradeAudit[]>(`/courses/${courseId}/grade-audits?limit=120`)
      setAudits(rows)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoadingAudits(false)
    }
  }

  async function undoAudit(auditId: number) {
    if (!courseId) return
    setUndoBusyId(auditId)
    setError(null)
    try {
      await api.post(`/courses/${courseId}/grade-audits/${auditId}/undo`)
      await Promise.all([loadGradebook(), loadAudits()])
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setUndoBusyId(null)
    }
  }

  useEffect(() => {
    void Promise.all([loadGradebook(), loadAudits()])
  }, [courseId])

  useEffect(() => {
    const key = courseId ? `gradebook_saved_views:${courseId}` : null
    if (!key) return
    const raw = readLocalStorage(key)
    if (!raw) return
    try {
      const parsed = JSON.parse(raw) as SavedGradebookView[]
      if (Array.isArray(parsed)) {
        setSavedViews(parsed)
      }
    } catch {
      // ignore malformed local storage payload
    }
  }, [courseId])

  const orderedAssignments = useMemo(() => {
    if (!gradebook) return []
    const byId = new Map(gradebook.assignments.map((a) => [a.id, a]))
    const ordered = assignmentOrder.map((id) => byId.get(id)).filter((a): a is AssignmentMeta => Boolean(a))
    const remainder = gradebook.assignments.filter((a) => !assignmentOrder.includes(a.id))
    return [...ordered, ...remainder]
  }, [gradebook, assignmentOrder])

  const orderedCalculated = useMemo(() => {
    if (!gradebook) return []
    const byId = new Map(gradebook.calculated_columns.map((c) => [c.id, c]))
    const ordered = calculatedOrder.map((id) => byId.get(id)).filter((c): c is CalculatedColumn => Boolean(c))
    const remainder = gradebook.calculated_columns.filter((c) => !calculatedOrder.includes(c.id))
    return [...ordered, ...remainder]
  }, [gradebook, calculatedOrder])

  const filteredAssignments = useMemo(() => {
    const search = assignmentSearch.trim().toLowerCase()
    return orderedAssignments.filter((assignment) => assignment.title.toLowerCase().includes(search))
  }, [orderedAssignments, assignmentSearch])

  const filteredStudents = useMemo(() => {
    if (!gradebook) return []
    const search = studentSearch.trim().toLowerCase()
    let rows = gradebook.students.filter((student) => student.name.toLowerCase().includes(search))

    rows = [...rows].sort((a, b) => {
      let cmp = 0
      if (rowSortColumn === 'student_lastname') {
        const an = parseName(a.name)
        const bn = parseName(b.name)
        cmp = an.last.localeCompare(bn.last) || an.first.localeCompare(bn.first)
      } else if (rowSortColumn === 'student_name') {
        cmp = a.name.localeCompare(b.name)
      } else {
        cmp = (a.totals.percent ?? -1) - (b.totals.percent ?? -1)
      }
      return rowSortDirection === 'asc' ? cmp : -cmp
    })

    return rows
  }, [gradebook, rowSortColumn, rowSortDirection, studentSearch])

  const visibleColumns: ColumnDef[] = useMemo(
    () => [
      ...filteredAssignments.map((assignment) => ({ kind: 'assignment' as const, id: assignment.id, assignment })),
      ...orderedCalculated.map((calculated) => ({ kind: 'calculated' as const, id: calculated.id, calculated })),
    ],
    [filteredAssignments, orderedCalculated],
  )

  const outOfSyncCount = useMemo(() => {
    if (!gradebook) return 0
    return gradebook.students.flatMap((s) => s.assignments).filter((a) => a.is_out_of_sync).length
  }, [gradebook])

  function persistViews(next: SavedGradebookView[]) {
    setSavedViews(next)
    if (!courseId) return
    writeLocalStorage(`gradebook_saved_views:${courseId}`, JSON.stringify(next))
  }

  function saveCurrentView() {
    const name = viewName.trim()
    if (!name) return
    const nextView: SavedGradebookView = {
      name,
      studentSearch,
      assignmentSearch,
      rowSortColumn,
      rowSortDirection,
    }
    const merged = [nextView, ...savedViews.filter((view) => view.name.toLowerCase() !== name.toLowerCase())].slice(0, 12)
    persistViews(merged)
    setViewName('')
  }

  function applySavedView(view: SavedGradebookView) {
    setStudentSearch(view.studentSearch)
    setAssignmentSearch(view.assignmentSearch)
    setRowSortColumn(view.rowSortColumn)
    setRowSortDirection(view.rowSortDirection)
  }

  function deleteSavedView(name: string) {
    persistViews(savedViews.filter((view) => view.name !== name))
  }

  async function previewMessageCandidates() {
    if (!courseId || !messageAssignmentId) return
    setMessageBusy(true)
    setError(null)
    setMessageResult(null)
    try {
      const params = new URLSearchParams({
        assignment_id: String(messageAssignmentId),
        filter_kind: messageFilterKind,
      })
      if (messageThreshold.trim()) params.set('threshold', messageThreshold.trim())
      if (messageIncludeExcused) params.set('include_excused', 'true')
      const response = await api.get<{ count: number; candidates: MessageCandidate[] }>(
        `/courses/${courseId}/message-candidates?${params.toString()}`,
      )
      setMessageCandidates(response.candidates || [])
      setMessageResult(`Preview loaded: ${response.count} students.`)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setMessageBusy(false)
    }
  }

  async function sendMessagesToCandidates() {
    if (!courseId || !messageAssignmentId) return
    setMessageBusy(true)
    setError(null)
    setMessageResult(null)
    try {
      const response = await api.post<{ sent_count: number; task_count: number }>(`/courses/${courseId}/message-students`, {
        assignment_id: messageAssignmentId,
        filter_kind: messageFilterKind,
        threshold: messageThreshold.trim() ? Number(messageThreshold) : null,
        include_excused: messageIncludeExcused,
        subject: messageSubject.trim(),
        message: messageBody.trim(),
        template_name: messageTemplateName.trim() || null,
        recurrence_days: messageCreateTask ? Number(messageRecurrenceDays || '7') : null,
        create_followup_tasks: messageCreateTask,
      })
      setMessageResult(
        `Logged outreach for ${response.sent_count} students. Follow-up tasks created: ${response.task_count}.`,
      )
      await Promise.all([loadAudits(), loadGradebook()])
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setMessageBusy(false)
    }
  }

  async function persistColumnOrder(nextAssignmentOrder: number[], nextCalculatedOrder: number[]) {
    if (!courseId) return
    setAssignmentOrder(nextAssignmentOrder)
    setCalculatedOrder(nextCalculatedOrder)
    try {
      await api.post(`/courses/${courseId}/gradebook/columns/reorder`, {
        assignment_order: nextAssignmentOrder,
        calculated_column_order: nextCalculatedOrder,
      })
    } catch (err) {
      setError((err as Error).message)
    }
  }

  function moveAssignment(assignmentId: number, direction: -1 | 1) {
    const idx = assignmentOrder.indexOf(assignmentId)
    if (idx < 0) return
    const next = [...assignmentOrder]
    const swap = idx + direction
    if (swap < 0 || swap >= next.length) return
    ;[next[idx], next[swap]] = [next[swap], next[idx]]
    void persistColumnOrder(next, calculatedOrder)
  }

  function moveCalculated(columnId: number, direction: -1 | 1) {
    const idx = calculatedOrder.indexOf(columnId)
    if (idx < 0) return
    const next = [...calculatedOrder]
    const swap = idx + direction
    if (swap < 0 || swap >= next.length) return
    ;[next[idx], next[swap]] = [next[swap], next[idx]]
    void persistColumnOrder(assignmentOrder, next)
  }

  function openCellEditor(
    rowIndex: number,
    colIndex: number,
    assignment: AssignmentMeta,
    current?: StudentAssignment,
    typedStart?: string,
  ) {
    const student = filteredStudents[rowIndex]
    if (!student) return

    setActiveCell({ row: rowIndex, col: colIndex })
    setActiveEditor({
      rowIndex,
      colIndex,
      studentId: student.student_id,
      studentName: student.name,
      assignment,
      current,
    })

    if (assignment.grading_type === 'points') {
      setEditStatus(current?.status ?? 'graded')
      setEditScore(typedStart ?? (current?.score !== null && current?.score !== undefined ? String(current.score) : ''))
      setEditLetter('')
      setEditCompletion('incomplete')
    } else if (assignment.grading_type === 'letter') {
      setEditStatus(current?.status ?? 'graded')
      setEditLetter(typedStart ?? (current?.letter_grade || ''))
      setEditScore('')
      setEditCompletion('incomplete')
    } else {
      setEditCompletion(normalizeCompletionStatus(current))
      setEditStatus(current?.status ?? 'graded')
      setEditScore('')
      setEditLetter('')
    }
  }

  async function saveGradeEdit(event: FormEvent) {
    event.preventDefault()
    if (!courseId || !activeEditor) return

    const assignment = activeEditor.assignment
    const payload: Record<string, unknown> = {
      student_id: activeEditor.studentId,
    }

    if (assignment.grading_type === 'points') {
      payload.score = editScore.trim() === '' ? null : Number(editScore)
      payload.status = editStatus
    } else if (assignment.grading_type === 'letter') {
      payload.letter_grade = editLetter.trim() || null
      payload.status = editStatus
    } else {
      payload.completion_status = editCompletion
      payload.status = editCompletion === 'missing' ? 'missing' : editCompletion === 'excused' ? 'excused' : 'graded'
    }

    setSavingGrade(true)
    try {
      await api.post(`/courses/${courseId}/assignments/${assignment.id}/grades`, payload)
      const nextRow = activeEditor.rowIndex
      const nextCol = Math.min(activeEditor.colIndex + 1, visibleColumns.length - 1)
      setActiveEditor(null)
      await Promise.all([loadGradebook(), loadAudits()])
      setActiveCell({ row: nextRow, col: nextCol })
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSavingGrade(false)
    }
  }

  async function quickToggleCompletion(
    rowIndex: number,
    colIndex: number,
    assignment: AssignmentMeta,
    current: StudentAssignment | undefined,
  ) {
    if (!courseId) return
    const student = filteredStudents[rowIndex]
    if (!student) return
    const currentValue = normalizeCompletionStatus(current)
    const nextValue = nextCompletionStatus(currentValue)
    const nextStatus = nextValue === 'missing' ? 'missing' : nextValue === 'excused' ? 'excused' : 'graded'

    setActiveCell({ row: rowIndex, col: colIndex })
    openCellEditor(rowIndex, colIndex, assignment, current)
    try {
      await api.post(`/courses/${courseId}/assignments/${assignment.id}/grades`, {
        student_id: student.student_id,
        completion_status: nextValue,
        status: nextStatus,
      })
      await Promise.all([loadGradebook(), loadAudits()])
    } catch (err) {
      setError((err as Error).message)
    }
  }

  function handleGridKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (!filteredStudents.length || !visibleColumns.length || activeEditor) return

    const current = activeCell || { row: 0, col: 0 }
    let next = { ...current }

    if (event.key === 'ArrowRight') {
      next.col = Math.min(current.col + 1, visibleColumns.length - 1)
      event.preventDefault()
    } else if (event.key === 'ArrowLeft') {
      next.col = Math.max(current.col - 1, 0)
      event.preventDefault()
    } else if (event.key === 'ArrowDown') {
      next.row = Math.min(current.row + 1, filteredStudents.length - 1)
      event.preventDefault()
    } else if (event.key === 'ArrowUp') {
      next.row = Math.max(current.row - 1, 0)
      event.preventDefault()
    } else if (event.key === 'Tab') {
      next.col = event.shiftKey ? Math.max(current.col - 1, 0) : Math.min(current.col + 1, visibleColumns.length - 1)
      event.preventDefault()
    } else if (event.key === 'Enter' || event.key === 'F2') {
      const col = visibleColumns[current.col]
      if (col?.kind === 'assignment') {
        const student = filteredStudents[current.row]
        const map = new Map(student.assignments.map((entry) => [entry.assignment_id, entry]))
        openCellEditor(current.row, current.col, col.assignment, map.get(col.assignment.id))
      }
      event.preventDefault()
      return
    } else if (event.key === ' ') {
      const col = visibleColumns[current.col]
      if (col?.kind === 'assignment' && col.assignment.grading_type === 'completion') {
        const student = filteredStudents[current.row]
        const map = new Map(student.assignments.map((entry) => [entry.assignment_id, entry]))
        void quickToggleCompletion(current.row, current.col, col.assignment, map.get(col.assignment.id))
        event.preventDefault()
        return
      }
    } else if (event.key.length === 1 && !event.altKey && !event.ctrlKey && !event.metaKey) {
      const col = visibleColumns[current.col]
      if (col?.kind === 'assignment' && col.assignment.grading_type !== 'completion') {
        const student = filteredStudents[current.row]
        const map = new Map(student.assignments.map((entry) => [entry.assignment_id, entry]))
        openCellEditor(current.row, current.col, col.assignment, map.get(col.assignment.id), event.key)
        event.preventDefault()
        return
      }
    }

    setActiveCell(next)
  }

  function reorderByDrop(target: ColumnDef) {
    if (!dragColumn || dragColumn.kind !== target.kind) return
    if (dragColumn.kind === 'assignment' && target.kind === 'assignment') {
      const nextAssignments = moveId(assignmentOrder, dragColumn.assignment.id, target.assignment.id)
      setDragColumn(null)
      void persistColumnOrder(nextAssignments, calculatedOrder)
      return
    }
    if (dragColumn.kind === 'calculated' && target.kind === 'calculated') {
      const nextCalculated = moveId(calculatedOrder, dragColumn.calculated.id, target.calculated.id)
      setDragColumn(null)
      void persistColumnOrder(assignmentOrder, nextCalculated)
    }
  }

  async function createLocalAssignment(event: FormEvent) {
    event.preventDefault()
    if (!courseId || !newTitle.trim()) return
    setCreatingAssignment(true)
    try {
      await api.post(`/courses/${courseId}/assignments/local`, {
        title: newTitle.trim(),
        grading_type: newGradingType,
        points_possible: newGradingType === 'points' ? Number(newPoints || '0') : null,
        due_at: newDueAt ? new Date(newDueAt).toISOString() : null,
      })
      setNewTitle('')
      setNewDueAt('')
      setNewPoints('100')
      setNewGradingType('points')
      await loadGradebook()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setCreatingAssignment(false)
    }
  }

  async function saveCalculatedColumn(event: FormEvent) {
    event.preventDefault()
    if (!courseId || !calcName.trim()) return
    setSavingCalc(true)
    try {
      if (calcEditId) {
        await api.patch(`/courses/${courseId}/calculated-columns/${calcEditId}`, {
          name: calcName.trim(),
          operation: calcOperation,
          assignment_ids: calcAssignmentIds,
        })
      } else {
        await api.post(`/courses/${courseId}/calculated-columns`, {
          name: calcName.trim(),
          operation: calcOperation,
          assignment_ids: calcAssignmentIds,
        })
      }
      setCalcEditId(null)
      setCalcName('')
      setCalcOperation('average_percent')
      setCalcAssignmentIds([])
      await loadGradebook()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSavingCalc(false)
    }
  }

  async function deleteCalculatedColumn(columnId: number) {
    if (!courseId) return
    try {
      await api.delete(`/courses/${courseId}/calculated-columns/${columnId}`)
      if (calcEditId === columnId) {
        setCalcEditId(null)
        setCalcName('')
        setCalcOperation('average_percent')
        setCalcAssignmentIds([])
      }
      await loadGradebook()
    } catch (err) {
      setError((err as Error).message)
    }
  }

  function beginEditCalculated(column: CalculatedColumn) {
    setCalcEditId(column.id)
    setCalcName(column.name)
    setCalcOperation(column.operation)
    setCalcAssignmentIds(column.assignment_ids)
  }

  if (!gradebook) {
    return (
      <section>
        <h2>Merged Gradebook</h2>
        {error ? <p className="error">{error}</p> : <p>Loading...</p>}
      </section>
    )
  }

  return (
    <section>
      <h2>Merged Gradebook</h2>
      <p>
        Course: <strong>{gradebook.course.name}</strong>
      </p>
      <article className="card action-bar">
        <div className="gradebook-toolbar compact-grid">
          <button type="button" onClick={() => void loadGradebook()}>Refresh Gradebook</button>
          <button type="button" onClick={() => void loadAudits()} disabled={loadingAudits}>
            {loadingAudits ? 'Loading Audits...' : 'Refresh Audit Log'}
          </button>
          <Link className="nav-link" to={`/courses/${gradebook.course.id}/matches`}>Open Match Queue</Link>
          <div className="muted-badge">Out-of-sync overrides: {outOfSyncCount}</div>
        </div>
        <div className="gradebook-toolbar compact-grid" style={{ marginTop: '0.5rem' }}>
          <input
            value={viewName}
            onChange={(event) => setViewName(event.target.value)}
            placeholder="Save filter/sort view as..."
          />
          <button type="button" onClick={saveCurrentView}>Save View</button>
        </div>
        <div className="chip-row" style={{ marginTop: '0.5rem' }}>
          {savedViews.map((view) => (
            <span key={view.name} className="chip">
              <button type="button" onClick={() => applySavedView(view)}>{view.name}</button>
              <button type="button" onClick={() => deleteSavedView(view.name)} title={`Delete view ${view.name}`}>x</button>
            </span>
          ))}
          {savedViews.length === 0 ? <span className="table-subtle">No saved views yet.</span> : null}
        </div>
      </article>

      {outOfSyncCount > 0 ? <p className="warning">{outOfSyncCount} cells are locally overridden and not synchronized with Canvas.</p> : null}
      {error ? <p className="error">{error}</p> : null}

      <article className="card" style={{ marginTop: '0.8rem' }}>
        <h3>Create Local Assignment</h3>
        <form className="form gradebook-toolbar" onSubmit={createLocalAssignment}>
          <input value={newTitle} onChange={(event) => setNewTitle(event.target.value)} placeholder="Assignment title" required />
          <select value={newGradingType} onChange={(event) => setNewGradingType(event.target.value as typeof newGradingType)}>
            <option value="points">Points</option>
            <option value="letter">Letter Grade</option>
            <option value="completion">Complete/Incomplete</option>
          </select>
          {newGradingType === 'points' ? (
            <input value={newPoints} onChange={(event) => setNewPoints(event.target.value)} type="number" min="0" step="0.01" placeholder="Points possible" />
          ) : (
            <div className="muted-badge">No points required</div>
          )}
          <input value={newDueAt} onChange={(event) => setNewDueAt(event.target.value)} type="datetime-local" />
          <button type="submit" disabled={creatingAssignment}>{creatingAssignment ? 'Creating...' : 'Add Assignment'}</button>
        </form>
      </article>

      <div className="gradebook-layout">
        <article className="card action-bar">
          <h3>Filters</h3>
          <div className="gradebook-toolbar compact-grid">
            <input placeholder="Search students" value={studentSearch} onChange={(event) => setStudentSearch(event.target.value)} />
            <input placeholder="Search assignments" value={assignmentSearch} onChange={(event) => setAssignmentSearch(event.target.value)} />
            <select value={rowSortColumn} onChange={(event) => setRowSortColumn(event.target.value as typeof rowSortColumn)}>
              <option value="student_lastname">Sort: Last Name</option>
              <option value="student_name">Sort: Full Name</option>
              <option value="percent">Sort: Percent</option>
            </select>
            <select value={rowSortDirection} onChange={(event) => setRowSortDirection(event.target.value as typeof rowSortDirection)}>
              <option value="asc">Ascending</option>
              <option value="desc">Descending</option>
            </select>
          </div>
          <div className="chip-row" style={{ marginTop: '0.5rem' }}>
            {studentSearch.trim() ? <span className="chip">Student: {studentSearch}</span> : null}
            {assignmentSearch.trim() ? <span className="chip">Assignment: {assignmentSearch}</span> : null}
            <span className="chip">Sort: {rowSortColumn} ({rowSortDirection})</span>
          </div>
          <p className="subtitle">Keyboard: arrows/tab to move, Enter/F2/type to edit, Space cycles completion states (Complete -&gt; Incomplete -&gt; Missing -&gt; Excused). Drag headers to reorder columns.</p>
        </article>

        <article className="card">
          <h3>Calculated Columns</h3>
          <form className="form" onSubmit={saveCalculatedColumn}>
            <input value={calcName} onChange={(event) => setCalcName(event.target.value)} placeholder="Column name" required />
            <select value={calcOperation} onChange={(event) => setCalcOperation(event.target.value as typeof calcOperation)}>
              <option value="average_percent">Average Percent</option>
              <option value="sum_points">Sum Points</option>
              <option value="completion_rate">Completion Rate</option>
            </select>
            <select
              multiple
              value={calcAssignmentIds.map(String)}
              onChange={(event) => {
                const ids = Array.from(event.target.selectedOptions).map((opt) => Number(opt.value))
                setCalcAssignmentIds(ids)
              }}
              style={{ minHeight: '120px' }}
            >
              {orderedAssignments.map((assignment) => (
                <option key={assignment.id} value={assignment.id}>
                  {assignment.title}
                </option>
              ))}
            </select>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button type="submit" disabled={savingCalc}>{savingCalc ? 'Saving...' : calcEditId ? 'Update Column' : 'Add Column'}</button>
              {calcEditId ? (
                <button
                  type="button"
                  onClick={() => {
                    setCalcEditId(null)
                    setCalcName('')
                    setCalcOperation('average_percent')
                    setCalcAssignmentIds([])
                  }}
                >
                  Cancel
                </button>
              ) : null}
            </div>
          </form>
          <div className="list compact" style={{ maxHeight: '180px', overflow: 'auto' }}>
            {orderedCalculated.map((column, idx) => (
              <div key={column.id} className="card">
                <strong>{column.name}</strong> ({column.operation})
                <div style={{ display: 'flex', gap: '0.35rem', marginTop: '0.35rem' }}>
                  {showReorderArrows ? (
                    <>
                      <button type="button" onClick={() => moveCalculated(column.id, -1)} disabled={idx === 0}>◀</button>
                      <button type="button" onClick={() => moveCalculated(column.id, 1)} disabled={idx === orderedCalculated.length - 1}>▶</button>
                    </>
                  ) : null}
                  <button type="button" onClick={() => beginEditCalculated(column)}>Edit</button>
                  <button type="button" onClick={() => void deleteCalculatedColumn(column.id)}>Delete</button>
                </div>
              </div>
            ))}
            {orderedCalculated.length === 0 ? <p>No calculated columns yet.</p> : null}
          </div>
        </article>
      </div>

      <div className={`gradebook-workspace ${showDetailsPane ? (detailsPaneExpanded ? 'details-expanded' : 'details-visible') : 'details-hidden'}`}>
        <div className="card gradebook-table-wrap" tabIndex={0} onKeyDown={handleGridKeyDown}>
          <table className="gradebook-table">
            <thead>
              <tr>
                <th className="sticky-col">Student</th>
                <th>Percent</th>
                {visibleColumns.map((column) => {
                  if (column.kind === 'assignment') {
                    const assignment = column.assignment
                    const orderIdx = assignmentOrder.indexOf(assignment.id)
                    return (
                      <th
                        key={`a-${assignment.id}`}
                        draggable
                        onDragStart={() => setDragColumn(column)}
                        onDragEnd={() => setDragColumn(null)}
                        onDragOver={(event) => event.preventDefault()}
                        onDrop={() => reorderByDrop(column)}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                          <span>{assignment.title}</span>
                          {showReorderArrows ? (
                            <>
                              <button type="button" onClick={() => moveAssignment(assignment.id, -1)} disabled={orderIdx <= 0}>◀</button>
                              <button type="button" onClick={() => moveAssignment(assignment.id, 1)} disabled={orderIdx < 0 || orderIdx >= assignmentOrder.length - 1}>▶</button>
                            </>
                          ) : null}
                        </div>
                        <div className="table-subtle">
                          {assignment.grading_type} • {assignment.source === 'canvas' ? 'Canvas' : 'Local'}
                        </div>
                      </th>
                    )
                  }
                  return (
                    <th
                      key={`c-${column.calculated.id}`}
                      draggable
                      onDragStart={() => setDragColumn(column)}
                      onDragEnd={() => setDragColumn(null)}
                      onDragOver={(event) => event.preventDefault()}
                      onDrop={() => reorderByDrop(column)}
                    >
                      <div>{column.calculated.name}</div>
                      <div className="table-subtle">calculated</div>
                    </th>
                  )
                })}
              </tr>
            </thead>
            <tbody>
              {filteredStudents.map((student, rowIndex) => {
                const assignmentMap = new Map(student.assignments.map((entry) => [entry.assignment_id, entry]))
                const calcMap = new Map(student.calculated_values.map((value) => [value.column_id, value]))

                return (
                  <tr key={student.student_id}>
                    <td className="sticky-col">{student.name}</td>
                    <td>{student.totals.percent === null || student.totals.percent === undefined ? 'N/A' : `${student.totals.percent}%`}</td>
                    {visibleColumns.map((column, colIndex) => {
                      const isActive = activeCell?.row === rowIndex && activeCell?.col === colIndex
                      if (column.kind === 'assignment') {
                        const entry = assignmentMap.get(column.assignment.id)
                        const className = [
                          'grade-cell',
                          entry?.is_out_of_sync ? 'out-of-sync-cell' : '',
                          isActive ? 'cell-active' : '',
                        ]
                          .filter(Boolean)
                          .join(' ')

                        return (
                          <td key={`cell-${student.student_id}-${column.assignment.id}`} className={className}>
                            <button
                              className="grade-cell-button"
                              onClick={() => openCellEditor(rowIndex, colIndex, column.assignment, entry)}
                              onDoubleClick={() => {
                                if (column.assignment.grading_type === 'completion') {
                                  void quickToggleCompletion(rowIndex, colIndex, column.assignment, entry)
                                }
                              }}
                              title={entry?.is_out_of_sync ? 'Local override differs from Canvas' : 'Edit'}
                            >
                              {renderAssignmentValue(entry, column.assignment)}
                            </button>
                          </td>
                        )
                      }

                      const calc = calcMap.get(column.calculated.id)
                      return (
                        <td
                          key={`calc-${student.student_id}-${column.calculated.id}`}
                          className={isActive ? 'cell-active' : ''}
                          onClick={() => setActiveCell({ row: rowIndex, col: colIndex })}
                        >
                          {calc?.display || 'N/A'}
                        </td>
                      )
                    })}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        {showDetailsPane ? (
          <aside className="card gradebook-details-pane">
            <div className="gradebook-details-header">
              <h3>Grade Details</h3>
              <button type="button" onClick={() => setShowDetailsPane(false)}>Collapse</button>
            </div>
            {activeEditor ? (
              <>
                <p>
                  <strong>{activeEditor.studentName}</strong> • <strong>{activeEditor.assignment.title}</strong>
                  {activeEditor.assignment.source === 'canvas' ? ' (Canvas item, local override)' : ''}
                </p>
                <form className="form gradebook-toolbar" onSubmit={saveGradeEdit}>
                  {activeEditor.assignment.grading_type === 'points' ? (
                    <>
                      <input value={editScore} onChange={(event) => setEditScore(event.target.value)} type="number" step="0.01" placeholder="Score" />
                      <select value={editStatus} onChange={(event) => setEditStatus(event.target.value as typeof editStatus)}>
                        <option value="graded">Graded</option>
                        <option value="missing">Missing</option>
                        <option value="excused">Excused</option>
                        <option value="unsubmitted">Unsubmitted</option>
                      </select>
                    </>
                  ) : null}
                  {activeEditor.assignment.grading_type === 'letter' ? (
                    <>
                      <input value={editLetter} onChange={(event) => setEditLetter(event.target.value)} placeholder="Letter grade" />
                      <select value={editStatus} onChange={(event) => setEditStatus(event.target.value as typeof editStatus)}>
                        <option value="graded">Graded</option>
                        <option value="missing">Missing</option>
                        <option value="excused">Excused</option>
                        <option value="unsubmitted">Unsubmitted</option>
                      </select>
                    </>
                  ) : null}
                  {activeEditor.assignment.grading_type === 'completion' ? (
                    <select value={editCompletion} onChange={(event) => setEditCompletion(event.target.value as typeof editCompletion)}>
                      <option value="complete">Complete</option>
                      <option value="incomplete">Incomplete</option>
                      <option value="missing">Missing</option>
                      <option value="excused">Excused</option>
                    </select>
                  ) : null}
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button type="submit" disabled={savingGrade}>{savingGrade ? 'Saving...' : 'Save'}</button>
                    <button type="button" onClick={() => setActiveEditor(null)} disabled={savingGrade}>Clear</button>
                  </div>
                </form>
              </>
            ) : (
              <p>Select a grade cell to edit details here.</p>
            )}
          </aside>
        ) : null}
      </div>

      <div className="gradebook-layout" style={{ marginTop: '0.8rem' }}>
        <article className="card">
          <h3>Message Students Who...</h3>
          <form
            className="form"
            onSubmit={(event) => {
              event.preventDefault()
              void sendMessagesToCandidates()
            }}
          >
            <select
              value={messageAssignmentId ?? ''}
              onChange={(event) => setMessageAssignmentId(event.target.value ? Number(event.target.value) : null)}
              required
            >
              {orderedAssignments.map((assignment) => (
                <option key={assignment.id} value={assignment.id}>
                  {assignment.title}
                </option>
              ))}
            </select>
            <select value={messageFilterKind} onChange={(event) => setMessageFilterKind(event.target.value as MessageFilterKind)}>
              <option value="not_submitted">Not Submitted</option>
              <option value="not_graded">Not Graded</option>
              <option value="missing">Missing</option>
              <option value="score_below">Score Below Threshold</option>
              <option value="score_above">Score Above Threshold</option>
            </select>
            {messageFilterKind === 'score_below' || messageFilterKind === 'score_above' ? (
              <input
                type="number"
                min="0"
                max="100"
                value={messageThreshold}
                onChange={(event) => setMessageThreshold(event.target.value)}
                placeholder="Threshold"
              />
            ) : null}
            <input value={messageSubject} onChange={(event) => setMessageSubject(event.target.value)} placeholder="Subject" required />
            <textarea value={messageBody} onChange={(event) => setMessageBody(event.target.value)} placeholder="Message template" required />
            <input
              value={messageTemplateName}
              onChange={(event) => setMessageTemplateName(event.target.value)}
              placeholder="Template name (optional)"
            />
            <label>
              <input
                type="checkbox"
                checked={messageIncludeExcused}
                onChange={(event) => setMessageIncludeExcused(event.target.checked)}
              /> Include excused students
            </label>
            <label>
              <input
                type="checkbox"
                checked={messageCreateTask}
                onChange={(event) => setMessageCreateTask(event.target.checked)}
              /> Create follow-up tasks
            </label>
            {messageCreateTask ? (
              <input
                type="number"
                min="1"
                max="30"
                value={messageRecurrenceDays}
                onChange={(event) => setMessageRecurrenceDays(event.target.value)}
                placeholder="Follow-up task due in days"
              />
            ) : null}
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              <button type="button" onClick={() => void previewMessageCandidates()} disabled={messageBusy}>
                {messageBusy ? 'Working...' : 'Preview Recipients'}
              </button>
              <button type="submit" disabled={messageBusy || messageCandidates.length === 0}>
                Send / Log Outreach
              </button>
            </div>
          </form>
          {messageResult ? <p>{messageResult}</p> : null}
        </article>

        <article className="card">
          <h3>Message Preview</h3>
          <ul className="list compact" style={{ maxHeight: '320px', overflow: 'auto' }}>
            {messageCandidates.map((candidate) => (
              <li key={candidate.student_id} className="card">
                <strong>{candidate.student_name}</strong> — {candidate.reason}
                <div className="table-subtle">
                  Status: {candidate.status}
                  {candidate.score !== undefined && candidate.score !== null ? ` | Score: ${candidate.score}` : ''}
                </div>
              </li>
            ))}
          </ul>
          {messageCandidates.length === 0 ? <p>No preview loaded yet.</p> : null}
        </article>
      </div>

      <article className="card" style={{ marginTop: '0.8rem' }}>
        <h3>Recent Grade Changes (Audit + Undo)</h3>
        {loadingAudits ? <p>Loading audit history...</p> : null}
        <div className="students-grid-wrap">
          <table className="students-grid-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Student</th>
                <th>Assignment</th>
                <th>Action</th>
                <th>Before</th>
                <th>After</th>
                <th>Undo</th>
              </tr>
            </thead>
            <tbody>
              {audits.map((audit) => (
                <tr key={audit.id}>
                  <td>{new Date(audit.created_at).toLocaleString()}</td>
                  <td>{audit.student_name || audit.student_id}</td>
                  <td>{audit.assignment_title || audit.assignment_id}</td>
                  <td>{audit.action}</td>
                  <td>{JSON.stringify(audit.before || {})}</td>
                  <td>{JSON.stringify(audit.after || {})}</td>
                  <td>
                    <button
                      type="button"
                      disabled={audit.was_undone || undoBusyId === audit.id}
                      onClick={() => void undoAudit(audit.id)}
                    >
                      {audit.was_undone ? 'Undone' : undoBusyId === audit.id ? 'Undoing...' : 'Undo'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {audits.length === 0 && !loadingAudits ? <p>No grade changes recorded yet.</p> : null}
        </div>
      </article>

      <article className="card" style={{ marginTop: '0.8rem' }}>
        <h3>Editor Options</h3>
        <div className="gradebook-editor-options">
          <label>
            <input type="checkbox" checked={showDetailsPane} onChange={(event) => setShowDetailsPane(event.target.checked)} /> Show right details pane
          </label>
          <label>
            <input
              type="checkbox"
              checked={detailsPaneExpanded}
              onChange={(event) => setDetailsPaneExpanded(event.target.checked)}
              disabled={!showDetailsPane}
            /> Expand details pane width
          </label>
          <label>
            <input type="checkbox" checked={showReorderArrows} onChange={(event) => setShowReorderArrows(event.target.checked)} /> Show left/right reorder arrows
          </label>
        </div>
      </article>
    </section>
  )
}
