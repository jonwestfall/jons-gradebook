import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/layout/AppShell'
import { AdvisingPage } from './pages/AdvisingPage'
import { AttendancePage } from './pages/AttendancePage'
import { CanvasSyncPage } from './pages/CanvasSyncPage'
import { CourseMatchWorkbenchPage } from './pages/CourseMatchWorkbenchPage'
import { CourseGradebookPage } from './pages/CourseGradebookPage'
import { CoursesPage } from './pages/CoursesPage'
import { DashboardPage } from './pages/DashboardPage'
import { DocumentsPage } from './pages/DocumentsPage'
import { InteractionsPage } from './pages/InteractionsPage'
import { LLMWorkbenchPage } from './pages/LLMWorkbenchPage'
import { ReportsPage } from './pages/ReportsPage'
import { RubricsPage } from './pages/RubricsPage'
import { SettingsPage } from './pages/SettingsPage'
import { StudentProfilePage } from './pages/StudentProfilePage'
import { StudentsPage } from './pages/StudentsPage'
import { TaskQueuePage } from './pages/TaskQueuePage'

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/canvas-sync" element={<CanvasSyncPage />} />
        <Route path="/courses" element={<CoursesPage />} />
        <Route path="/courses/:courseId/gradebook" element={<CourseGradebookPage />} />
        <Route path="/courses/:courseId/matches" element={<CourseMatchWorkbenchPage />} />
        <Route path="/students" element={<StudentsPage />} />
        <Route path="/students/:studentId" element={<StudentProfilePage />} />
        <Route path="/advising" element={<AdvisingPage />} />
        <Route path="/attendance" element={<AttendancePage />} />
        <Route path="/interactions" element={<InteractionsPage />} />
        <Route path="/rubrics" element={<RubricsPage />} />
        <Route path="/documents" element={<DocumentsPage />} />
        <Route path="/llm" element={<LLMWorkbenchPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/tasks" element={<TaskQueuePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
