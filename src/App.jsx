
import { useEffect, useState } from 'react'
import {
  BrowserRouter,
  Navigate,
  Outlet,
  Route,
  Routes,
  useLocation,
} from 'react-router-dom'

import { getCurrentUser } from './services/auth.js'
import Login from './pages/Login.jsx'
import ResetPassword from './pages/ResetPassword.jsx'
import AdminDashboard from './pages/AdminDashboard.jsx'
import UserManagement from './pages/UserManagement.jsx'
import EmployeePortal from './pages/EmployeePortal.jsx'

import SystemSettings from './pages/SystemSettings.jsx'

import {
  DocumentOverview,
  ActivityLogs,
  PermissionAudit,
  SecurityMonitoring,
  AdminProfile,
  LogoutPage,
} from './pages/Additionalpages.jsx'

function RoleRoute({ role }) {
  const location = useLocation()
  const [attempt, setAttempt] = useState(0)
  const [state, setState] = useState({ status: 'loading', user: null, error: '' })

  useEffect(() => {
    let active = true
    getCurrentUser()
      .then((user) => {
        if (active) setState({ status: 'ready', user, error: '' })
      })
      .catch((error) => {
        if (active) setState({ status: 'error', user: null, error: error.message })
      })

    return () => {
      active = false
    }
  }, [attempt, location.pathname])

  if (state.status === 'loading') {
    return <div className="p-8 text-sm text-slate-600" role="status">Checking your session…</div>
  }

  if (state.status === 'error') {
    return (
      <main className="p-8 text-sm text-slate-700">
        <p role="alert">Unable to verify your session. {state.error}</p>
        <button
          type="button"
          onClick={() => {
            setState({ status: 'loading', user: null, error: '' })
            setAttempt((value) => value + 1)
          }}
          className="mt-3 font-semibold text-emerald-800 underline"
        >
          Try again
        </button>
      </main>
    )
  }

  if (!state.user) {
    return <Navigate to="/" replace state={{ from: `${location.pathname}${location.search}` }} />
  }

  const actualRole = String(state.user.role || '').toUpperCase()
  if (actualRole !== 'ADMIN' && actualRole !== 'EMPLOYEE') {
    return <Navigate to="/" replace />
  }
  if (actualRole !== role) {
    return <Navigate to={actualRole === 'ADMIN' ? '/admin/dashboard' : '/employee/dashboard'} replace />
  }

  return <Outlet />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Authentication */}
        <Route path="/" element={<Login />} />
        <Route path="/reset-password" element={<ResetPassword />} />

        {/* Administrator */}
        <Route element={<RoleRoute role="ADMIN" />}>
          <Route path="/admin/dashboard" element={<AdminDashboard />} />
          <Route path="/admin/users" element={<UserManagement />} />
          <Route path="/admin/documents" element={<DocumentOverview />} />
          <Route path="/admin/activity" element={<ActivityLogs />} />
          <Route path="/admin/permissions" element={<PermissionAudit />} />
          <Route path="/admin/security" element={<SecurityMonitoring />} />
          <Route path="/admin/settings" element={<SystemSettings />} />
          <Route path="/admin/profile" element={<AdminProfile />} />
        </Route>

        {/* Employee */}
        <Route element={<RoleRoute role="EMPLOYEE" />}>
          <Route path="/employee/*" element={<EmployeePortal />} />
        </Route>

        {/* Logout */}
        <Route path="/logout" element={<LogoutPage />} />

        {/* Unknown routes */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
