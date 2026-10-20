import { useState } from 'react'
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
  Save,
  X,
  Settings,
} from 'lucide-react'

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

const ownerLinks = [
  ['My Documents', '/owner/documents'],
  ['Shared Access', '/owner/access'],
  ['Activity', '/owner/activity'],
  ['Profile', '/owner/profile'],
  ['Logout', '/logout'],
]

const viewerLinks = [
  ['Shared Documents', '/viewer/documents'],
  ['Recent Activity', '/viewer/activity'],
  ['Profile', '/viewer/profile'],
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
  'My Documents': FileText,
  'Shared Access': Users,
  Activity,
  'Recent Activity': Activity,
  'Shared Documents': FileText,
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

  const links =
    role === 'Document Owner'
      ? ownerLinks
      : role === 'Viewer'
        ? viewerLinks
        : adminLinks

  const home =
    role === 'Document Owner'
      ? '/owner/documents'
      : role === 'Viewer'
        ? '/viewer/documents'
        : '/admin/dashboard'

  return (
    <aside className="w-full shrink-0 bg-gradient-to-b from-[#07523f] to-[#00372b] p-4 text-white md:min-h-screen md:w-60">
      <button
        type="button"
        onClick={() => navigate(home)}
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
        {links.map(([label, path]) => {
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

export function SystemSettings() {
  const [settings, setSettings] = useState({
    notifications: true,
    maintenance: false,
    review: true,
  })
  const [saved, setSaved] = useState(false)

  const options = [
    ['notifications', 'Security notifications', 'Show important account event notifications.'],
    ['maintenance', 'Maintenance mode', 'Demo toggle only; it does not disable real users.'],
    ['review', 'Require permission review', 'Recommend reviewing sensitive access changes.'],
  ]

  return (
    <Shell title="System Settings" subtitle="Configure application preferences">
      <section className="max-w-3xl rounded-2xl bg-white p-5 shadow-sm">
        <h2 className="mb-4 text-lg font-bold">General settings</h2>

        <div className="space-y-5">
          {options.map(([key, title, description]) => (
            <label key={key} className="flex items-start justify-between gap-4 border-b border-slate-100 pb-4">
              <span>
                <span className="block text-sm font-semibold">{title}</span>
                <span className="mt-1 block text-xs text-slate-500">{description}</span>
              </span>
              <input
                type="checkbox"
                checked={settings[key]}
                onChange={(event) => {
                  setSettings({ ...settings, [key]: event.target.checked })
                  setSaved(false)
                }}
                className="mt-1 size-4 accent-emerald-700"
              />
            </label>
          ))}
        </div>

        <button
          type="button"
          onClick={() => setSaved(true)}
          className="mt-5 inline-flex items-center gap-2 rounded-full bg-emerald-700 px-5 py-2.5 text-sm font-semibold text-white"
        >
          <Save size={16} /> Save demo settings
        </button>

        {saved && (
          <p role="status" className="mt-3 text-sm text-emerald-800">
            Settings saved for this page session.
          </p>
        )}
      </section>
    </Shell>
  )
}

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
  const [twoFactorEnabled] = useState(false)

  const isAdmin = role === 'Administrator'

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
            <h2 className="mb-3 flex items-center gap-2 font-bold">
              <ShieldCheck size={18} /> Two-Factor Authentication
            </h2>

            <p className="text-sm text-slate-600">
              Status:{' '}
              <Pill value={twoFactorEnabled ? 'Enabled' : 'Not enabled'} />
            </p>

            <p className="mt-3 text-sm text-slate-500">
              Add an extra layer of security to your account.
            </p>

            <button
              type="button"
              onClick={() => setMessage('Two-factor authentication requires backend integration before it can be enabled securely.')}
              className="mt-4 inline-flex items-center gap-2 rounded-full border border-emerald-200 px-4 py-2.5 text-sm font-semibold text-emerald-800 hover:bg-emerald-50"
            >
              <ShieldCheck size={16} /> Enable Two-Factor Authentication
            </button>

            <p className="mt-3 text-xs text-slate-500">
              Demonstration only. Real two-factor authentication is not configured.
            </p>
          </section>

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

export function OwnerProfile() {
  return <ProfilePage role="Document Owner" />
}

export function ViewerProfile() {
  return <ProfilePage role="Viewer" />
}

export function OwnerDocuments() {
  const [query, setQuery] = useState('')
  const [notice, setNotice] = useState('')

  const mine = documents.filter((doc) => doc.owner === 'John Doe')
  const rows = mine.filter((doc) => doc.name.toLowerCase().includes(query.toLowerCase()))

  return (
    <Shell role="Document Owner" title="My Documents" subtitle="Manage your document records and review access">
      <div className="mb-4 flex flex-wrap gap-3">
        <div className="min-w-[220px] flex-1">
          <SearchField value={query} onChange={setQuery} placeholder="Search my documents" />
        </div>
        <button
          type="button"
          onClick={() => setNotice('File upload will be connected to backend storage later.')}
          className="rounded-full bg-emerald-700 px-5 py-2.5 text-sm font-semibold text-white"
        >
          Upload document
        </button>
      </div>

      {notice && <p role="status" className="mb-4 rounded-xl bg-emerald-50 p-3 text-sm text-emerald-900">{notice}</p>}

      <Table
        headers={['Document', 'Type', 'Date', 'Access', 'Status', 'Actions']}
        rows={rows.map((doc) => [
          doc.name,
          doc.type,
          doc.date,
          doc.access,
          <Pill key={`${doc.id}-status`} value={doc.status} />,
          <button
            key={`${doc.id}-access`}
            type="button"
            onClick={() => setNotice(`Access management for ${doc.name} will be connected to the backend.`)}
            className="font-semibold text-emerald-800"
          >
            Manage access
          </button>,
        ])}
      />
    </Shell>
  )
}

export function OwnerAccess() {
  return (
    <Shell role="Document Owner" title="Shared Access" subtitle="Review who can access your documents">
      <Table
        headers={['Document', 'Owner', 'Shared with', 'Permission', 'Status']}
        rows={permissions.filter((item) => item.owner === 'John Doe').map((item) => [
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

export function OwnerActivity() {
  return (
    <Shell role="Document Owner" title="My Activity" subtitle="Recent actions related to your documents">
      <Table
        headers={['Date', 'User', 'Action', 'Category', 'Result']}
        rows={activities.filter((item) => item.user === 'John Doe' || item.action.toLowerCase().includes('document')).map((item) => [
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

export function ViewerDocuments() {
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState(null)

  const shared = documents.filter((doc) => ['DOC-1001', 'DOC-1003', 'DOC-1005'].includes(doc.id))
  const rows = shared.filter((doc) => doc.name.toLowerCase().includes(query.toLowerCase()))

  return (
    <Shell role="Viewer" title="Shared Documents" subtitle="Open documents shared with you">
      <div className="mb-4">
        <SearchField value={query} onChange={setQuery} placeholder="Search shared documents" />
      </div>

      <Table
        headers={['Document', 'Owner', 'Type', 'Status', 'Action']}
        rows={rows.map((doc) => [
          doc.name,
          doc.owner,
          doc.type,
          <Pill key={`${doc.id}-status`} value="Allowed" />,
          <button
            key={`${doc.id}-details`}
            type="button"
            onClick={() => setSelected(doc)}
            className="inline-flex items-center gap-1 font-semibold text-emerald-800"
          >
            <Eye size={14} /> View details
          </button>,
        ])}
      />

      {selected && <Details title={selected.name} data={selected} onClose={() => setSelected(null)} />}
    </Shell>
  )
}

export function ViewerActivity() {
  return (
    <Shell role="Viewer" title="Recent Activity" subtitle="Recent sample activity for shared documents">
      <Table
        headers={['Date', 'Action', 'Category', 'Result']}
        rows={activities.filter((item) => item.category === 'Document').map((item) => [
          item.date,
          item.action,
          item.category,
          <Pill key={item.date} value={item.result} />,
        ])}
      />
    </Shell>
  )
}

export function LogoutPage() {
  const navigate = useNavigate()

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#eafbf3] p-4">
      <section className="w-full max-w-md rounded-2xl bg-white p-8 text-center shadow-sm">
        <span className="mx-auto flex size-14 items-center justify-center rounded-full bg-amber-100 text-amber-800">
          <LogOut size={24} />
        </span>

        <h1 className="mt-4 text-2xl font-bold">Log out of DocTrust?</h1>
        <p className="mt-2 text-sm text-slate-500">
          This demo returns you to login. Real session termination requires authentication integration.
        </p>

        <div className="mt-6 flex justify-center gap-3">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="rounded-full border px-5 py-2.5 text-sm"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => navigate('/')}
            className="rounded-full bg-emerald-700 px-5 py-2.5 text-sm font-semibold text-white"
          >
            Return to login
          </button>
        </div>
      </section>
    </main>
  )
}