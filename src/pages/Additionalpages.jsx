import { useState, useEffect, useCallback } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  ChartNoAxesColumn,
  ChevronRight,
  FileText,
  LockKeyhole,
  Search,
  Shield,
  ShieldCheck,
  UserRound,
  Users,
  LogOut,
  Eye,
  EyeOff,
  X,
  Settings,
  Copy,
  Download,
  KeyRound,
  QrCode,
} from 'lucide-react'
import {
  logout,
  getCurrentUser,
  getTwoFactorStatus,
  enrollTwoFactor,
  verifyEnrollTwoFactor,
  disableTwoFactor,
} from '../services/auth.js'

const adminLinks = [
  ['Dashboard', '/admin/dashboard'],
  ['User Management', '/admin/users'],
  ['Document Overview', '/admin/documents'],
  ['Activity Logs', '/admin/activity'],
  ['Permission Audit', '/admin/permissions'],
  ['Security Monitoring', '/admin/security'],
  ['System Settings', '/admin/settings'],
  ['Profile', '/admin/profile'],
  ['Logout', '/logout'],
]

const iconMap = {
  Dashboard: ChartNoAxesColumn,
  'User Management': Users,
  'Document Overview': FileText,
  'Activity Logs': Activity,
  'Permission Audit': ShieldCheck,
  'Security Monitoring': Shield,
  'System Settings': Settings,
  Profile: UserRound,
  Logout: LogOut,
}

const documents = [
  { id: 'DOC-1001', name: 'Project Proposal.pdf', owner: 'John Doe', type: 'PDF', status: 'Active', date: '20 Oct 2026', access: '3 users' },
  { id: 'DOC-1002', name: 'Financial Report.xlsx', owner: 'Emma Davis', type: 'Spreadsheet', status: 'Restricted', date: '19 Oct 2026', access: '2 users' },
  { id: 'DOC-1003', name: 'Team Guidelines.docx', owner: 'Tom Wilson', type: 'Document', status: 'Active', date: '18 Oct 2026', access: '5 users' },
  { id: 'DOC-1004', name: 'Contract Draft.pdf', owner: 'Mia Taylor', type: 'PDF', status: 'Archived', date: '15 Oct 2026', access: '1 user' },
  { id: 'DOC-1005', name: 'Product Roadmap.pdf', owner: 'John Doe', type: 'PDF', status: 'Active', date: '14 Oct 2026', access: '4 users' },
]

const activities = [
  { date: '20 Oct 2026, 09:24', user: 'Admin User', action: 'Viewed user management', category: 'User Management', result: 'Success' },
  { date: '20 Oct 2026, 09:10', user: 'John Doe', action: 'Uploaded Project Proposal.pdf', category: 'Document', result: 'Success' },
  { date: '19 Oct 2026, 16:42', user: 'Emma Davis', action: 'Updated document permissions', category: 'Permissions', result: 'Success' },
  { date: '19 Oct 2026, 14:08', user: 'Sara Smith', action: 'Opened shared document', category: 'Document', result: 'Success' },
  { date: '18 Oct 2026, 11:31', user: 'Admin User', action: 'Reviewed security alerts', category: 'Security', result: 'Success' },
]

const permissions = [
  { document: 'Project Proposal.pdf', owner: 'John Doe', user: 'Sara Smith', permission: 'View', status: 'Allowed' },
  { document: 'Financial Report.xlsx', owner: 'Emma Davis', user: 'Tom Wilson', permission: 'Edit', status: 'Allowed' },
  { document: 'Contract Draft.pdf', owner: 'Mia Taylor', user: 'Ryan Clark', permission: 'View', status: 'Revoked' },
  { document: 'Product Roadmap.pdf', owner: 'John Doe', user: 'Lisa White', permission: 'View', status: 'Allowed' },
]

const initialAlerts = [
  { id: 1, title: 'Repeated failed login attempts', severity: 'High', status: 'Open', time: '20 Oct 2026, 09:15' },
  { id: 2, title: 'New device sign-in', severity: 'Medium', status: 'Review', time: '20 Oct 2026, 08:40' },
  { id: 3, title: 'Permission updated', severity: 'Low', status: 'Resolved', time: '19 Oct 2026, 16:42' },
]

function Sidebar({ role = 'Administrator' }) {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <aside className="w-full shrink-0 bg-gradient-to-b from-[#07523f] to-[#00372b] p-4 text-white md:min-h-screen md:w-60">
      <button
        type="button"
        onClick={() => navigate('/admin/dashboard')}
        className="mb-5 flex items-center gap-2 px-2 text-lg font-bold"
      >
        <ShieldCheck size={22} />
        DocTrust
      </button>

      <div className="mb-5 w-fit rounded-full bg-white/15 px-3 py-1 text-xs">
        {role}
      </div>

      <nav
        aria-label={`${role} navigation`}
        className="grid grid-cols-2 gap-1 md:flex md:flex-col"
      >
        {adminLinks.map(([label, path]) => {
          const active = location.pathname === path
          const Icon = iconMap[label] || ChevronRight

          return (
            <button
              key={path}
              type="button"
              aria-current={active ? 'page' : undefined}
              onClick={() => navigate(path)}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition-colors ${
                active
                  ? 'bg-emerald-700 font-semibold text-white'
                  : 'text-white/80 hover:bg-white/10'
              }`}
            >
              <Icon size={18} className="shrink-0" />
              <span>{label}</span>
            </button>
          )
        })}
      </nav>
    </aside>
  )
}

function Shell({ title, subtitle, role = 'Administrator', children }) {
  return (
    <main className="min-h-screen bg-[#eafbf3] text-slate-800 md:flex">
      <Sidebar role={role} />

      <div className="min-w-0 flex-1 p-4 sm:p-6 lg:p-8">
        <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
            <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
          </div>

          <span className="flex items-center gap-2 rounded-full border border-emerald-100 bg-white px-3 py-2 text-xs">
            <UserRound size={15} />
            {role}
          </span>
        </header>

        {children}

        <p className="mt-5 text-xs text-slate-500">
          Frontend demonstration using sample data. Backend persistence and
          security checks are not connected yet.
        </p>
      </div>
    </main>
  )
}

function Stat({ label, value, icon: Icon, detail }) {
  return (
    <section className="rounded-2xl border border-emerald-50 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">{label}</p>
        <span className="rounded-xl bg-emerald-50 p-2 text-emerald-800">
          <Icon size={18} />
        </span>
      </div>
      <p className="mt-3 text-2xl font-bold">{value}</p>
      <p className="mt-1 text-xs text-slate-500">{detail}</p>
    </section>
  )
}

function SearchField({ value, onChange, placeholder = 'Search records...' }) {
  return (
    <label className="flex min-w-0 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2.5">
      <Search size={16} className="shrink-0 text-slate-400" />
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="min-w-0 flex-1 text-sm outline-none"
      />
    </label>
  )
}

function Pill({ value }) {
  const good = ['Active', 'Allowed', 'Success', 'Resolved', 'Enabled']
  const warning = ['Restricted', 'Review', 'Medium']

  const classes = good.includes(value)
    ? 'bg-emerald-100 text-emerald-800'
    : warning.includes(value)
      ? 'bg-amber-100 text-amber-800'
      : 'bg-rose-100 text-rose-800'

  return (
    <span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold ${classes}`}>
      {value}
    </span>
  )
}

function Table({ headers, rows }) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-slate-100 bg-white">
      <table className="w-full min-w-[650px] text-left text-xs">
        <thead className="bg-slate-50 text-slate-500">
          <tr>
            {headers.map((header) => (
              <th key={header} className="px-4 py-3 font-semibold">
                {header}
              </th>
            ))}
          </tr>
        </thead>

        <tbody>
          {rows.length ? (
            rows.map((row, index) => (
              <tr key={index} className="border-t border-slate-100">
                {row.map((cell, i) => (
                  <td key={i} className="px-4 py-3">
                    {cell}
                  </td>
                ))}
              </tr>
            ))
          ) : (
            <tr>
              <td
                colSpan={headers.length}
                className="px-4 py-10 text-center text-slate-500"
              >
                No records found.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

function Details({ title, data, onClose }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4"
      onMouseDown={(event) =>
        event.target === event.currentTarget && onClose()
      }
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl"
      >
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 className="text-lg font-bold">{title}</h2>
          <button type="button" onClick={onClose} aria-label="Close">
            <X size={19} />
          </button>
        </div>

        <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {Object.entries(data).map(([key, value]) => (
            <div key={key} className="rounded-xl bg-slate-50 p-3">
              <dt className="text-xs capitalize text-slate-500">{key}</dt>
              <dd className="mt-1 break-words text-sm font-semibold">
                {String(value)}
              </dd>
            </div>
          ))}
        </dl>

        <button
          type="button"
          onClick={onClose}
          className="mt-5 rounded-full bg-emerald-700 px-5 py-2 text-sm font-semibold text-white"
        >
          Close
        </button>
      </section>
    </div>
  )
}

export function DocumentOverview() {
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('All statuses')
  const [selected, setSelected] = useState(null)

  const rows = documents.filter(
    (doc) =>
      `${doc.name} ${doc.owner} ${doc.id}`
        .toLowerCase()
        .includes(query.toLowerCase()) &&
      (status === 'All statuses' || doc.status === status),
  )

  return (
    <Shell title="Document Overview" subtitle="Review document records, ownership and access status">
      <div className="mb-5 grid gap-3 sm:grid-cols-3">
        <Stat label="Total documents" value="128" icon={FileText} detail="Demo total" />
        <Stat label="Active documents" value="96" icon={CheckCircle} detail="Sample data" />
        <Stat label="Restricted" value="12" icon={LockKeyhole} detail="Access limited" />
      </div>

      <div className="mb-4 grid gap-3 sm:grid-cols-[1fr_200px]">
        <SearchField value={query} onChange={setQuery} placeholder="Search document, owner or ID" />
        <select
          value={status}
          onChange={(event) => setStatus(event.target.value)}
          className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm"
        >
          <option>All statuses</option>
          <option>Active</option>
          <option>Restricted</option>
          <option>Archived</option>
        </select>
      </div>

      <Table
        headers={['Document', 'Owner', 'Type', 'Uploaded', 'Access', 'Status', 'Details']}
        rows={rows.map((doc) => [
          <span key={doc.id} className="font-semibold">
            {doc.name}
            <span className="mt-1 block text-slate-400">{doc.id}</span>
          </span>,
          doc.owner,
          doc.type,
          doc.date,
          doc.access,
          <Pill key={`${doc.id}-status`} value={doc.status} />,
          <button
            key={`${doc.id}-view`}
            type="button"
            onClick={() => setSelected(doc)}
            className="inline-flex items-center gap-1 font-semibold text-emerald-800"
          >
            <Eye size={14} /> View
          </button>,
        ])}
      />

      {selected && (
        <Details title={selected.name} data={selected} onClose={() => setSelected(null)} />
      )}
    </Shell>
  )
}

export function ActivityLogs() {
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('All categories')

  const rows = activities.filter(
    (item) =>
      `${item.user} ${item.action} ${item.category}`
        .toLowerCase()
        .includes(query.toLowerCase()) &&
      (category === 'All categories' || item.category === category),
  )

  return (
    <Shell title="Activity Logs" subtitle="Review recorded actions and events">
      <div className="mb-5 grid gap-3 sm:grid-cols-3">
        <Stat label="Events shown" value={rows.length} icon={Activity} detail="Filtered demo records" />
        <Stat label="Successful actions" value="100%" icon={CheckCircle} detail="Sample data" />
        <Stat label="Audit trail" value="Demo" icon={ShieldCheck} detail="Not connected to backend" />
      </div>

      <div className="mb-4 grid gap-3 sm:grid-cols-[1fr_220px]">
        <SearchField value={query} onChange={setQuery} />
        <select
          value={category}
          onChange={(event) => setCategory(event.target.value)}
          className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm"
        >
          <option>All categories</option>
          <option>User Management</option>
          <option>Document</option>
          <option>Permissions</option>
          <option>Security</option>
        </select>
      </div>

      <Table
        headers={['Date and time', 'User', 'Action', 'Category', 'Result']}
        rows={rows.map((item) => [
          item.date,
          item.user,
          item.action,
          item.category,
          <Pill key={item.date} value={item.result} />,
        ])}
      />
    </Shell>
  )
}

export function PermissionAudit() {
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState('All permissions')

  const rows = permissions.filter(
    (item) =>
      `${item.document} ${item.owner} ${item.user}`
        .toLowerCase()
        .includes(query.toLowerCase()) &&
      (filter === 'All permissions' || item.status === filter),
  )

  return (
    <Shell title="Permission Audit" subtitle="Review document access and permission decisions">
      <div className="mb-4 grid gap-3 sm:grid-cols-[1fr_200px]">
        <SearchField value={query} onChange={setQuery} placeholder="Search document, owner or user" />
        <select
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
          className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm"
        >
          <option>All permissions</option>
          <option>Allowed</option>
          <option>Revoked</option>
        </select>
      </div>

      <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        <ShieldCheck size={17} className="mr-2 inline" />
        Review access against each document owner's policy. These are example records.
      </div>

      <Table
        headers={['Document', 'Owner', 'User', 'Permission', 'Decision']}
        rows={rows.map((item) => [
          item.document,
          item.owner,
          item.user,
          item.permission,
          <Pill key={item.document} value={item.status} />,
        ])}
      />
    </Shell>
  )
}

export function SecurityMonitoring() {
  const [alerts, setAlerts] = useState(initialAlerts)
  const [filter, setFilter] = useState('All alerts')

  const visible = alerts.filter(
    (alert) =>
      filter === 'All alerts' ||
      alert.severity === filter ||
      alert.status === filter,
  )

  function toggleAlert(id) {
    setAlerts((current) =>
      current.map((alert) =>
        alert.id === id
          ? { ...alert, status: alert.status === 'Resolved' ? 'Open' : 'Resolved' }
          : alert,
      ),
    )
  }

  return (
    <Shell title="Security Monitoring" subtitle="Review sample alerts and update their demo status">
      <div className="mb-5 grid gap-3 sm:grid-cols-3">
        <Stat label="Open alerts" value={alerts.filter((a) => a.status !== 'Resolved').length} icon={AlertTriangle} detail="Sample alerts" />
        <Stat label="High severity" value={alerts.filter((a) => a.severity === 'High').length} icon={Shield} detail="Requires review" />
        <Stat label="Resolved" value={alerts.filter((a) => a.status === 'Resolved').length} icon={CheckCircle} detail="Demo status" />
      </div>

      <div className="mb-4">
        <select
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
          className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm sm:w-64"
        >
          <option>All alerts</option>
          <option>High</option>
          <option>Medium</option>
          <option>Low</option>
          <option>Open</option>
          <option>Review</option>
          <option>Resolved</option>
        </select>
      </div>

      <Table
        headers={['Alert', 'Severity', 'Date', 'Status', 'Action']}
        rows={visible.map((alert) => [
          alert.title,
          <Pill key={`${alert.id}-severity`} value={alert.severity} />,
          alert.time,
          <Pill key={`${alert.id}-status`} value={alert.status} />,
          <button
            key={`${alert.id}-action`}
            type="button"
            onClick={() => toggleAlert(alert.id)}
            className="font-semibold text-emerald-800"
          >
            {alert.status === 'Resolved' ? 'Reopen' : 'Mark resolved'}
          </button>,
        ])}
      />
    </Shell>
  )
}

export { SystemSettings } from './SystemSettings.jsx'

function ProfilePage({ role }) {
  const [name, setName] = useState(
    role === 'Administrator' ? 'Admin User' : `Demo ${role}`,
  )
  const [email, setEmail] = useState(
    role === 'Administrator' ? 'admin@example.com' : 'demo@example.com',
  )
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPasswords, setShowPasswords] = useState(false)
  const [message, setMessage] = useState('')

  // Real 2FA state from backend
  const [tfaStatus, setTfaStatus] = useState({
    is_enabled: false,
    enabled_at: null,
    recovery_codes_remaining: 0,
    mfa_required_by_policy: false,
  })
  const [tfaLoading, setTfaLoading] = useState(true)
  const [tfaActionLoading, setTfaActionLoading] = useState(false)
  const [tfaError, setTfaError] = useState('')
  const [tfaSuccess, setTfaSuccess] = useState('')

  // 2FA Enrollment state
  const [enrollData, setEnrollData] = useState(null)
  const [verifyCode, setVerifyCode] = useState('')
  const [newRecoveryCodes, setNewRecoveryCodes] = useState(null)
  const [copiedCodes, setCopiedCodes] = useState(false)
  const [copiedKey, setCopiedKey] = useState(false)

  // 2FA Disable modal state
  const [showDisableModal, setShowDisableModal] = useState(false)
  const [disablePassword, setDisablePassword] = useState('')
  const [disableCode, setDisableCode] = useState('')
  const [showDisablePassword, setShowDisablePassword] = useState(false)
  const [disabling, setDisabling] = useState(false)
  const [disableError, setDisableError] = useState('')

  const isAdmin = role === 'Administrator'

  const loadProfileAndTfa = useCallback(async () => {
    try {
      setTfaLoading(true)
      const [user, status] = await Promise.all([
        getCurrentUser().catch(() => null),
        getTwoFactorStatus().catch((err) => {
          console.error('Failed to load 2FA status:', err)
          return null
        }),
      ])

      if (user) {
        if (user.first_name || user.last_name) {
          setName(`${user.first_name} ${user.last_name}`.trim())
        } else if (user.username) {
          setName(user.username)
        }
        if (user.email) {
          setEmail(user.email)
        }
      }

      if (status) {
        setTfaStatus(status)
      }
    } finally {
      setTfaLoading(false)
    }
  }, [])

  useEffect(() => {
    loadProfileAndTfa()
  }, [loadProfileAndTfa])

  async function handleStartEnroll() {
    setTfaError('')
    setTfaSuccess('')
    setTfaActionLoading(true)
    try {
      const data = await enrollTwoFactor()
      setEnrollData(data)
      setVerifyCode('')
      setNewRecoveryCodes(null)
    } catch (err) {
      setTfaError(err.message || 'Failed to start 2FA enrollment.')
    } finally {
      setTfaActionLoading(false)
    }
  }

  async function handleVerifyEnroll(e) {
    if (e) e.preventDefault()
    if (!verifyCode || verifyCode.trim().length !== 6) {
      setTfaError('Please enter a valid 6-digit verification code.')
      return
    }

    setTfaError('')
    setTfaSuccess('')
    setTfaActionLoading(true)
    try {
      const res = await verifyEnrollTwoFactor(verifyCode.trim())
      setTfaSuccess('Two-factor authentication has been successfully activated on your account.')
      setNewRecoveryCodes(res.recovery_codes || [])
      setEnrollData(null)
      setVerifyCode('')
      await loadProfileAndTfa()
    } catch (err) {
      setTfaError(err.message || 'Verification failed. Please check the code and try again.')
    } finally {
      setTfaActionLoading(false)
    }
  }

  function handleCancelEnroll() {
    setEnrollData(null)
    setVerifyCode('')
    setTfaError('')
  }

  function handleCopySecret() {
    if (enrollData?.secret) {
      navigator.clipboard.writeText(enrollData.secret)
      setCopiedKey(true)
      setTimeout(() => setCopiedKey(false), 2500)
    }
  }

  function handleCopyRecoveryCodes() {
    if (newRecoveryCodes && newRecoveryCodes.length > 0) {
      navigator.clipboard.writeText(newRecoveryCodes.join('\n'))
      setCopiedCodes(true)
      setTimeout(() => setCopiedCodes(false), 2500)
    }
  }

  function handleDownloadRecoveryCodes() {
    if (!newRecoveryCodes || newRecoveryCodes.length === 0) return
    const content = [
      'DocTrust Two-Factor Authentication Recovery Codes',
      `Account: ${email}`,
      `Generated: ${new Date().toISOString()}`,
      '',
      'Important:',
      '- Each code is single-use and can only be used once.',
      '- Keep these codes in a secure, offline password manager or safe vault.',
      '- If you lose your authenticator app, these codes are the only way to recover access.',
      '',
      ...newRecoveryCodes.map((c, i) => `${i + 1}. ${c}`),
    ].join('\n')

    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `doctrust-recovery-codes-${Date.now()}.txt`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  async function handleDisableSubmit(e) {
    e.preventDefault()
    if (!disablePassword) {
      setDisableError('Current password is required.')
      return
    }
    if (!disableCode) {
      setDisableError('Authenticator or recovery code is required.')
      return
    }

    setDisabling(true)
    setDisableError('')
    try {
      await disableTwoFactor({ password: disablePassword, code: disableCode.trim() })
      setShowDisableModal(false)
      setDisablePassword('')
      setDisableCode('')
      setTfaSuccess('Two-factor authentication has been disabled.')
      await loadProfileAndTfa()
    } catch (err) {
      setDisableError(err.message || 'Failed to disable 2FA. Verify your password and code.')
    } finally {
      setDisabling(false)
    }
  }

  function handlePasswordUpdate(event) {
    event.preventDefault()

    if (newPassword.length < 8) {
      setMessage('New password must contain at least 8 characters.')
      return
    }

    if (newPassword !== confirmPassword) {
      setMessage('New password and confirmation do not match.')
      return
    }

    setMessage('Demo only: connect the backend to securely change your password.')
  }

  return (
    <Shell title="Profile" subtitle="Your account details and security" role={role}>
      <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-2">
        <section className="rounded-2xl bg-white p-5 shadow-sm">
          <h2 className="mb-4 flex items-center gap-2 font-bold">
            <UserRound size={18} /> Account Details
          </h2>

          <div className="space-y-3 text-sm text-slate-600">
            <p>Name: <span className="font-semibold text-slate-800">{name}</span></p>
            <p>Email: <span className="font-semibold text-slate-800">{email}</span></p>
            <p>Role: <span className="font-semibold text-slate-800">{role}</span></p>
            <p className="flex items-center gap-2">
              Status:
              <Pill value="Active" />
            </p>
            <p>Last login: <span className="font-semibold text-slate-800">20 Oct 2026, 10:24</span></p>
          </div>

          <form
            onSubmit={(event) => {
              event.preventDefault()
              setMessage('Profile updated in this demo.')
            }}
            className="mt-5 space-y-3 border-t border-slate-100 pt-4"
          >
            <label className="block text-sm font-medium">
              Edit name
              <input
                required
                value={name}
                onChange={(event) => setName(event.target.value)}
                className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal"
              />
            </label>

            <label className="block text-sm font-medium">
              Edit email
              <input
                required
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal"
              />
            </label>

            <button type="submit" className="rounded-full bg-emerald-700 px-5 py-2.5 text-sm font-semibold text-white">
              Save Profile
            </button>
          </form>
        </section>

        <section className="rounded-2xl bg-white p-5 shadow-sm">
          <h2 className="mb-4 flex items-center gap-2 font-bold">
            <LockKeyhole size={18} /> Change Password
          </h2>

          <form onSubmit={handlePasswordUpdate} className="space-y-4">
            {[
              { label: 'Current Password', value: currentPassword, setter: setCurrentPassword },
              { label: 'New Password', value: newPassword, setter: setNewPassword },
              { label: 'Confirm New Password', value: confirmPassword, setter: setConfirmPassword },
            ].map((field) => (
              <label key={field.label} className="block text-sm font-medium">
                {field.label}
                <div className="mt-1 flex gap-2">
                  <input
                    required
                    type={showPasswords ? 'text' : 'password'}
                    value={field.value}
                    onChange={(event) => {
                      field.setter(event.target.value)
                      setMessage('')
                    }}
                    placeholder={`Enter ${field.label.toLowerCase()}`}
                    className="min-w-0 flex-1 rounded-xl border border-slate-200 px-3 py-2.5 font-normal"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPasswords(!showPasswords)}
                    aria-label={showPasswords ? 'Hide passwords' : 'Show passwords'}
                    className="rounded-xl border border-slate-200 px-3 text-emerald-800"
                  >
                    <Eye size={17} />
                  </button>
                </div>
              </label>
            ))}

            <button type="submit" className="inline-flex items-center gap-2 rounded-full bg-emerald-700 px-5 py-2.5 text-sm font-semibold text-white">
              <CheckCircle size={16} /> Update Password
            </button>
          </form>

          {message && (
            <p role="status" className="mt-3 text-sm text-amber-800">{message}</p>
          )}

          <p className="mt-3 text-xs text-slate-500">
            Password updates are a demonstration until connected to the authentication backend.
          </p>
        </section>
      </div>

      {isAdmin && (
        <>
          <section className="mt-4 rounded-2xl bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
              <h2 className="flex items-center gap-2 font-bold text-slate-900">
                <ShieldCheck size={18} className="text-emerald-700" /> Two-Factor Authentication
              </h2>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">Status:</span>
                <Pill value={tfaStatus.is_enabled ? 'Enabled' : 'Not enabled'} />
              </div>
            </div>

            <p className="text-sm text-slate-600">
              Add a mandatory second verification step using an authenticator app (TOTP) to secure your account.
            </p>

            {tfaStatus.mfa_required_by_policy && (
              <div className="mt-3 flex items-start gap-2 rounded-xl bg-amber-50 p-3 text-xs text-amber-800 border border-amber-200">
                <AlertTriangle size={15} className="shrink-0 mt-0.5 text-amber-600" />
                <span>
                  <strong>Security Policy:</strong> Multi-factor authentication is required for all Administrator accounts on this system.
                </span>
              </div>
            )}

            {tfaSuccess && (
              <div className="mt-3 flex items-center justify-between gap-2 rounded-xl bg-emerald-50 p-3 text-xs text-emerald-900 border border-emerald-200">
                <div className="flex items-center gap-2">
                  <CheckCircle size={15} className="shrink-0 text-emerald-700" />
                  <span>{tfaSuccess}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setTfaSuccess('')}
                  className="text-emerald-700 hover:text-emerald-900"
                >
                  <X size={14} />
                </button>
              </div>
            )}

            {tfaError && (
              <div className="mt-3 flex items-center justify-between gap-2 rounded-xl bg-rose-50 p-3 text-xs text-rose-800 border border-rose-200">
                <div className="flex items-center gap-2">
                  <AlertTriangle size={15} className="shrink-0 text-rose-600" />
                  <span>{tfaError}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setTfaError('')}
                  className="text-rose-700 hover:text-rose-900"
                >
                  <X size={14} />
                </button>
              </div>
            )}

            {/* Display Recovery Codes Once After Enrollment */}
            {newRecoveryCodes && newRecoveryCodes.length > 0 && (
              <div className="mt-4 rounded-xl border-2 border-emerald-500 bg-emerald-50/50 p-4">
                <div className="flex items-center gap-2 text-emerald-900 font-bold text-sm mb-1">
                  <KeyRound size={17} className="text-emerald-700" />
                  Save Your Recovery Codes
                </div>
                <p className="text-xs text-slate-700 mb-3">
                  These single-use codes will only be shown <strong>once</strong>. Store them in a secure password manager or offline safe. If you ever lose access to your authenticator app, each code can be used once to sign in.
                </p>

                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 font-mono text-center text-xs font-bold text-slate-800 mb-3">
                  {newRecoveryCodes.map((code, idx) => (
                    <div key={idx} className="rounded-lg border border-slate-300 bg-white px-2 py-2 shadow-2xs tracking-wider">
                      {code}
                    </div>
                  ))}
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={handleCopyRecoveryCodes}
                    className="inline-flex items-center gap-1.5 rounded-full bg-white border border-slate-300 px-3.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition"
                  >
                    <Copy size={13} /> {copiedCodes ? 'Copied to Clipboard!' : 'Copy All Codes'}
                  </button>
                  <button
                    type="button"
                    onClick={handleDownloadRecoveryCodes}
                    className="inline-flex items-center gap-1.5 rounded-full bg-white border border-slate-300 px-3.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition"
                  >
                    <Download size={13} /> Download .txt
                  </button>
                  <button
                    type="button"
                    onClick={() => setNewRecoveryCodes(null)}
                    className="ml-auto inline-flex items-center gap-1.5 rounded-full bg-emerald-700 px-4 py-1.5 text-xs font-semibold text-white hover:bg-emerald-800 transition"
                  >
                    <CheckCircle size={13} /> I Have Saved These Codes
                  </button>
                </div>
              </div>
            )}

            {/* If 2FA is NOT enabled and NOT currently enrolling */}
            {!tfaStatus.is_enabled && !enrollData && (
              <div className="mt-4">
                <button
                  type="button"
                  disabled={tfaActionLoading || tfaLoading}
                  onClick={handleStartEnroll}
                  className="inline-flex items-center gap-2 rounded-full bg-[#087c5b] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#06684d] disabled:opacity-60"
                >
                  <ShieldCheck size={16} />
                  {tfaActionLoading ? 'Preparing Setup...' : 'Enable Two-Factor Authentication'}
                </button>
              </div>
            )}

            {/* If enrolling: QR code and verification input */}
            {enrollData && (
              <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50/30 p-5">
                <h3 className="text-sm font-bold text-slate-900 mb-3 flex items-center gap-2">
                  <QrCode size={17} className="text-emerald-700" />
                  Set Up Authenticator App
                </h3>

                <ol className="space-y-3 text-xs text-slate-700">
                  <li className="flex items-start gap-2">
                    <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-emerald-700 text-[10px] font-bold text-white">1</span>
                    <span>Install an authenticator app such as Google Authenticator, Microsoft Authenticator, 1Password, or Authy on your mobile device.</span>
                  </li>

                  <li className="flex items-start gap-2">
                    <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-emerald-700 text-[10px] font-bold text-white">2</span>
                    <div className="flex-1">
                      <p>Scan this QR code with your authenticator app:</p>
                      <div className="mt-2.5 flex flex-wrap items-center gap-4">
                        {(() => {
                          const qrSrc = enrollData?.qr_code || enrollData?.qr_code_svg || (typeof enrollData === 'string' ? enrollData : '')
                          return qrSrc ? (
                            <img
                              src={qrSrc}
                              alt="Two-Factor QR Code"
                              className="size-44 rounded-xl border border-slate-200 bg-white p-2 shadow-xs"
                            />
                          ) : (
                            <div className="flex size-44 items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white text-xs text-slate-400">
                              Loading QR code...
                            </div>
                          )
                        })()}
                        <div className="text-xs">
                          <p className="text-slate-500 mb-1">Cannot scan? Enter code manually:</p>
                          <div className="flex items-center gap-2">
                            <code className="rounded bg-white border border-slate-300 px-2 py-1 font-mono text-xs font-semibold text-slate-800 tracking-wider">
                              {enrollData.secret}
                            </code>
                            <button
                              type="button"
                              onClick={handleCopySecret}
                              className="rounded-lg border border-slate-300 bg-white p-1.5 text-slate-600 hover:bg-slate-50"
                              title="Copy Secret"
                            >
                              <Copy size={13} />
                            </button>
                          </div>
                          {copiedKey && <span className="text-[10px] text-emerald-700 font-semibold mt-1 block">Secret copied!</span>}
                        </div>
                      </div>
                    </div>
                  </li>

                  <li className="flex items-start gap-2 pt-1">
                    <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-emerald-700 text-[10px] font-bold text-white">3</span>
                    <form onSubmit={handleVerifyEnroll} className="flex-1">
                      <label htmlFor="tfa-verify-code" className="block text-slate-700 mb-1 font-semibold">
                        Enter the 6-digit verification code from your authenticator:
                      </label>
                      <div className="flex flex-wrap items-center gap-2">
                        <input
                          id="tfa-verify-code"
                          type="text"
                          inputMode="numeric"
                          maxLength={6}
                          autoComplete="one-time-code"
                          value={verifyCode}
                          onChange={(e) => setVerifyCode(e.target.value.replace(/\D/g, ''))}
                          placeholder="123456"
                          className="w-36 rounded-xl border border-slate-300 bg-white px-3 py-2 text-center font-mono text-base tracking-widest outline-none focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
                        />
                        <button
                          type="submit"
                          disabled={tfaActionLoading || verifyCode.trim().length !== 6}
                          className="inline-flex items-center gap-1.5 rounded-full bg-[#087c5b] px-4 py-2 text-xs font-semibold text-white transition hover:bg-[#06684d] disabled:opacity-50"
                        >
                          <CheckCircle size={14} />
                          {tfaActionLoading ? 'Verifying...' : 'Confirm & Activate 2FA'}
                        </button>
                        <button
                          type="button"
                          onClick={handleCancelEnroll}
                          disabled={tfaActionLoading}
                          className="rounded-full border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-50"
                        >
                          Cancel
                        </button>
                      </div>
                    </form>
                  </li>
                </ol>
              </div>
            )}

            {/* If 2FA IS enabled */}
            {tfaStatus.is_enabled && (
              <div className="mt-4 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-slate-50 border border-slate-200 p-3.5 text-xs text-slate-700">
                  <div className="space-y-1">
                    <p>
                      <strong>Active Authenticator:</strong> RFC 6238 TOTP Standard
                    </p>
                    {tfaStatus.enabled_at && (
                      <p className="text-slate-500">
                        Configured on: {new Date(tfaStatus.enabled_at).toLocaleString()}
                      </p>
                    )}
                    <p className="text-slate-500">
                      Unused recovery codes remaining: <strong>{tfaStatus.recovery_codes_remaining}</strong>
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setShowDisableModal(true)
                      setDisableError('')
                      setDisablePassword('')
                      setDisableCode('')
                    }}
                    className="rounded-full border border-rose-200 bg-white px-3.5 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-50 transition"
                  >
                    Disable 2FA
                  </button>
                </div>
              </div>
            )}
          </section>

          {/* Disable 2FA Modal */}
          {showDisableModal && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-xs">
              <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl sm:p-7">
                <div className="mb-4 flex items-center justify-between">
                  <div className="flex items-center gap-2 text-rose-700 font-bold text-lg">
                    <LockKeyhole size={20} />
                    Disable Two-Factor Authentication
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowDisableModal(false)}
                    className="rounded-full p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                  >
                    <X size={18} />
                  </button>
                </div>

                <p className="mb-4 text-xs text-slate-600">
                  To protect your account, please enter your current account password and either a valid 6-digit code from your authenticator app or a single-use recovery code.
                </p>

                {tfaStatus.mfa_required_by_policy && (
                  <p className="mb-3 rounded-lg bg-amber-50 border border-amber-200 p-2.5 text-[11px] text-amber-800">
                    <strong>Notice:</strong> MFA is required by security policy. Disabling 2FA will require you to set it up again at your next sign in.
                  </p>
                )}

                <form onSubmit={handleDisableSubmit} className="space-y-3.5">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Current Password
                    </label>
                    <div className="flex gap-2">
                      <input
                        type={showDisablePassword ? 'text' : 'password'}
                        required
                        value={disablePassword}
                        onChange={(e) => setDisablePassword(e.target.value)}
                        placeholder="Enter current password"
                        className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
                      />
                      <button
                        type="button"
                        onClick={() => setShowDisablePassword(!showDisablePassword)}
                        className="rounded-xl border border-slate-200 px-3 text-slate-500 hover:bg-slate-50"
                      >
                        {showDisablePassword ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Authenticator Code or Recovery Code
                    </label>
                    <input
                      type="text"
                      required
                      value={disableCode}
                      onChange={(e) => setDisableCode(e.target.value)}
                      placeholder="123456 or XXXX-XXXX"
                      className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm font-mono outline-none focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
                    />
                  </div>

                  {disableError && (
                    <p className="rounded-xl bg-rose-50 border border-rose-200 p-2.5 text-xs text-rose-800">
                      {disableError}
                    </p>
                  )}

                  <div className="mt-5 flex justify-end gap-2.5 pt-2">
                    <button
                      type="button"
                      onClick={() => setShowDisableModal(false)}
                      disabled={disabling}
                      className="rounded-full border border-slate-300 px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={disabling}
                      className="rounded-full bg-rose-700 px-4 py-2 text-xs font-semibold text-white hover:bg-rose-800 disabled:opacity-60"
                    >
                      {disabling ? 'Verifying...' : 'Confirm Disable 2FA'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}

          <section className="mt-4 rounded-2xl bg-white p-5 shadow-sm">
            <h2 className="mb-4 flex items-center gap-2 font-bold">
              <Activity size={18} /> Recent Account Activity
            </h2>

            <div className="overflow-x-auto">
              <table className="w-full min-w-[560px] text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-100 text-slate-500">
                    <th className="px-3 py-3 font-semibold">Date / time</th>
                    <th className="px-3 py-3 font-semibold">Activity</th>
                    <th className="px-3 py-3 font-semibold">IP address</th>
                    <th className="px-3 py-3 font-semibold">Result</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    { date: '20 Oct 2026, 10:24', action: 'Logged in', ip: '192.0.2.30', result: 'Success' },
                    { date: '19 Oct 2026, 09:10', action: 'Password change requested', ip: '192.0.2.30', result: 'Success' },
                    { date: '18 Oct 2026, 08:55', action: 'Login attempt', ip: '192.0.2.99', result: 'Failed' },
                  ].map((item) => (
                    <tr key={`${item.date}-${item.action}`} className="border-b border-slate-100 last:border-0">
                      <td className="px-3 py-3">{item.date}</td>
                      <td className="px-3 py-3">{item.action}</td>
                      <td className="px-3 py-3">{item.ip}</td>
                      <td className="px-3 py-3">
                        <Pill value={item.result} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <p className="mt-3 text-xs text-slate-500">
              Sample activity only. Real audit records must come from the backend.
            </p>
          </section>
        </>
      )}
    </Shell>
  )
}

export function AdminProfile() {
  return <ProfilePage role="Administrator" />
}

export function LogoutPage() {
  const navigate = useNavigate()
  const [loggingOut, setLoggingOut] = useState(false)

  async function handleConfirmLogout() {
    setLoggingOut(true)
    try {
      await logout()
    } finally {
      setLoggingOut(false)
      navigate('/')
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#eafbf3] p-4">
      <section className="w-full max-w-md rounded-2xl bg-white p-8 text-center shadow-sm">
        <span className="mx-auto flex size-14 items-center justify-center rounded-full bg-amber-100 text-amber-800">
          <LogOut size={24} />
        </span>

        <h1 className="mt-4 text-2xl font-bold">Log out of DocTrust?</h1>
        <p className="mt-2 text-sm text-slate-500">
          Your active session will be securely terminated on the server.
        </p>

        <div className="mt-6 flex justify-center gap-3">
          <button
            type="button"
            onClick={() => navigate(-1)}
            disabled={loggingOut}
            className="rounded-full border px-5 py-2.5 text-sm transition hover:bg-slate-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleConfirmLogout}
            disabled={loggingOut}
            className="rounded-full bg-emerald-700 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-800 disabled:opacity-60"
          >
            {loggingOut ? 'Signing out...' : 'Sign Out'}
          </button>
        </div>
      </section>
    </main>
  )
}