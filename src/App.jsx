
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import Login from './pages/Login.jsx'
import ResetPassword from './pages/ResetPassword.jsx'
import AdminDashboard from './pages/AdminDashboard.jsx'
import UserManagement from './pages/UserManagement.jsx'
import EmployeePortal from './pages/EmployeePortal.jsx'

import {
  DocumentOverview,
  ActivityLogs,
  PermissionAudit,
  SecurityMonitoring,
  SystemSettings,
  AdminProfile,
  LogoutPage,
} from './pages/Additionalpages.jsx'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Authentication */}
        <Route path="/" element={<Login />} />
        <Route path="/reset-password" element={<ResetPassword />} />

        {/* Administrator */}
        <Route path="/admin/dashboard" element={<AdminDashboard />} />
        <Route path="/admin/users" element={<UserManagement />} />
        <Route path="/admin/documents" element={<DocumentOverview />} />
        <Route path="/admin/activity" element={<ActivityLogs />} />
        <Route path="/admin/permissions" element={<PermissionAudit />} />
        <Route path="/admin/security" element={<SecurityMonitoring />} />
        <Route path="/admin/settings" element={<SystemSettings />} />
        <Route path="/admin/profile" element={<AdminProfile />} />

        {/* Employee */}
        <Route path="/employee/*" element={<EmployeePortal />} />

        {/* Logout */}
        <Route path="/logout" element={<LogoutPage />} />

        {/* Unknown routes */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
