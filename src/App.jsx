
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import Login from './pages/Login.jsx'
import AdminDashboard from './pages/AdminDashboard.jsx'
import UserManagement from './pages/UserManagement.jsx'

import {
  DocumentOverview,
  ActivityLogs,
  PermissionAudit,
  SecurityMonitoring,
  SystemSettings,
  AdminProfile,
  LogoutPage,
  OwnerDocuments,
  OwnerAccess,
  OwnerActivity,
  OwnerProfile,
  ViewerDocuments,
  ViewerActivity,
  ViewerProfile,
} from './pages/Additionalpages.jsx'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Login */}
        <Route path="/" element={<Login />} />

        {/* Administrator */}
        <Route path="/admin/dashboard" element={<AdminDashboard />} />
        <Route path="/admin/users" element={<UserManagement />} />
        <Route path="/admin/documents" element={<DocumentOverview />} />
        <Route path="/admin/activity" element={<ActivityLogs />} />
        <Route path="/admin/permissions" element={<PermissionAudit />} />
        <Route path="/admin/security" element={<SecurityMonitoring />} />
        <Route path="/admin/settings" element={<SystemSettings />} />
        <Route path="/admin/profile" element={<AdminProfile />} />

        {/* Document Owner */}
        <Route path="/owner/documents" element={<OwnerDocuments />} />
        <Route path="/owner/access" element={<OwnerAccess />} />
        <Route path="/owner/activity" element={<OwnerActivity />} />
        <Route path="/owner/profile" element={<OwnerProfile />} />

        {/* Viewer */}
        <Route path="/viewer/documents" element={<ViewerDocuments />} />
        <Route path="/viewer/activity" element={<ViewerActivity />} />
        <Route path="/viewer/profile" element={<ViewerProfile />} />

        {/* Logout */}
        <Route path="/logout" element={<LogoutPage />} />

        {/* Unknown routes */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
