import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  CheckCircle,
  ChartNoAxesColumn,
  ChevronRight,
  Database,
  FileText,
  HardDrive,
  History,
  Lock,
  LockKeyhole,
  LogOut,
  RefreshCw,
  RotateCcw,
  Save,
  Server,
  Shield,
  ShieldAlert,
  ShieldCheck,
  SlidersHorizontal,
  Upload,
  UserRound,
  Users,
  X,
} from 'lucide-react'

import {
  getSystemSettings,
  updateSystemSettings,
  resetSystemSettings,
} from '../services/systemSettings.js'

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
  'System Settings': SlidersHorizontal,
  Profile: UserRound,
  Logout: LogOut,
}

const AVAILABLE_EXTENSIONS = [
  { ext: '.pdf', label: 'PDF Document' },
  { ext: '.docx', label: 'Word Document' },
  { ext: '.xlsx', label: 'Excel Spreadsheet' },
  { ext: '.pptx', label: 'PowerPoint Presentation' },
  { ext: '.txt', label: 'Plain Text' },
  { ext: '.csv', label: 'CSV Table' },
  { ext: '.png', label: 'PNG Image' },
  { ext: '.jpg', label: 'JPEG Image' },
  { ext: '.zip', label: 'ZIP Archive' },
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
        <ShieldCheck size={22} className="text-emerald-300" />
        DocTrust
      </button>

      <div className="mb-5 w-fit rounded-full bg-white/15 px-3 py-1 text-xs font-medium tracking-wide">
        {role}
      </div>

      <nav aria-label={`${role} navigation`} className="grid grid-cols-2 gap-1 md:flex md:flex-col">
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
                  ? 'bg-emerald-700 font-semibold text-white shadow-sm'
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

function SectionCard({ id, title, icon: Icon, description, badge, children }) {
  return (
    <section id={id} className="scroll-mt-6 rounded-2xl border border-slate-200/80 bg-white p-5 shadow-xs transition-shadow hover:shadow-sm md:p-6">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-4">
        <div className="flex items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-xl bg-emerald-50 text-emerald-800">
            <Icon size={20} />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-800">{title}</h2>
            {description && <p className="text-xs text-slate-500">{description}</p>}
          </div>
        </div>
        {badge}
      </div>
      <div className="space-y-5">{children}</div>
    </section>
  )
}

function ToggleSwitch({ label, description, checked, onChange, disabled, warning, capability }) {
  return (
    <div className={`flex items-start justify-between gap-4 border-b border-slate-100/70 pb-4 last:border-0 last:pb-0 ${disabled ? 'opacity-60' : ''}`}>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-semibold text-slate-800">{label}</span>
          {capability && (
            <span
              className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                capability.available
                  ? 'bg-emerald-100 text-emerald-800'
                  : 'bg-amber-100 text-amber-800'
              }`}
              title={capability.reason || capability.provider}
            >
              {capability.available ? 'Active' : 'Planned'}
            </span>
          )}
        </div>
        {description && <p className="mt-1 text-xs text-slate-500">{description}</p>}
        {warning && (
          <p className="mt-1.5 flex items-center gap-1.5 text-xs font-medium text-amber-700">
            <AlertTriangle size={13} className="shrink-0" />
            {warning}
          </p>
        )}
      </div>

      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-hidden focus:ring-2 focus:ring-emerald-600 focus:ring-offset-2 ${
          checked ? 'bg-emerald-700' : 'bg-slate-300'
        } ${disabled ? 'cursor-not-allowed opacity-50' : ''}`}
      >
        <span
          className={`pointer-events-none inline-block size-5 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${
            checked ? 'translate-x-5' : 'translate-x-0'
          }`}
        />
      </button>
    </div>
  )
}

function NumberInput({ label, description, value, onChange, min, max, unit, error }) {
  return (
    <div className="flex flex-col justify-between gap-2 border-b border-slate-100/70 pb-4 sm:flex-row sm:items-center last:border-0 last:pb-0">
      <div className="min-w-0 flex-1">
        <label className="text-sm font-semibold text-slate-800">{label}</label>
        {description && <p className="mt-0.5 text-xs text-slate-500">{description}</p>}
        {error && <p className="mt-1 text-xs font-semibold text-rose-600">{error}</p>}
      </div>
      <div className="flex items-center gap-2 self-start sm:self-auto">
        <input
          type="number"
          min={min}
          max={max}
          value={value ?? ''}
          onChange={(e) => onChange(e.target.value === '' ? '' : parseInt(e.target.value, 10))}
          className={`w-28 rounded-lg border px-3 py-1.5 text-right text-sm font-semibold text-slate-800 transition focus:outline-hidden focus:ring-2 ${
            error
              ? 'border-rose-400 bg-rose-50/50 focus:ring-rose-500'
              : 'border-slate-300 bg-slate-50/50 focus:border-emerald-600 focus:bg-white focus:ring-emerald-600'
          }`}
        />
        {unit && <span className="text-xs font-medium text-slate-500">{unit}</span>}
      </div>
    </div>
  )
}

function TextInput({ label, description, value, onChange, placeholder, type = 'text', error }) {
  return (
    <div className="flex flex-col justify-between gap-2 border-b border-slate-100/70 pb-4 sm:flex-row sm:items-center last:border-0 last:pb-0">
      <div className="min-w-0 flex-1">
        <label className="text-sm font-semibold text-slate-800">{label}</label>
        {description && <p className="mt-0.5 text-xs text-slate-500">{description}</p>}
        {error && <p className="mt-1 text-xs font-semibold text-rose-600">{error}</p>}
      </div>
      <div className="w-full sm:w-72">
        <input
          type={type}
          value={value ?? ''}
          placeholder={placeholder}
          onChange={(e) => onChange(e.target.value)}
          className={`w-full rounded-lg border px-3 py-1.5 text-sm font-medium text-slate-800 transition focus:outline-hidden focus:ring-2 ${
            error
              ? 'border-rose-400 bg-rose-50/50 focus:ring-rose-500'
              : 'border-slate-300 bg-slate-50/50 focus:border-emerald-600 focus:bg-white focus:ring-emerald-600'
          }`}
        />
      </div>
    </div>
  )
}

function SelectInput({ label, description, value, onChange, options, error }) {
  return (
    <div className="flex flex-col justify-between gap-2 border-b border-slate-100/70 pb-4 sm:flex-row sm:items-center last:border-0 last:pb-0">
      <div className="min-w-0 flex-1">
        <label className="text-sm font-semibold text-slate-800">{label}</label>
        {description && <p className="mt-0.5 text-xs text-slate-500">{description}</p>}
        {error && <p className="mt-1 text-xs font-semibold text-rose-600">{error}</p>}
      </div>
      <div className="w-full sm:w-60">
        <select
          value={value ?? ''}
          onChange={(e) => onChange(e.target.value)}
          className="w-full rounded-lg border border-slate-300 bg-slate-50/50 px-3 py-1.5 text-sm font-medium text-slate-800 focus:border-emerald-600 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-emerald-600"
        >
          {options.map(([optVal, optLabel]) => (
            <option key={optVal} value={optVal}>
              {optLabel}
            </option>
          ))}
        </select>
      </div>
    </div>
  )
}

function ConfirmationModal({ open, title, description, confirmText, confirmVariant = 'danger', onConfirm, onCancel }) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-xs">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
        <div className="mb-4 flex items-center gap-3">
          <div
            className={`flex size-10 items-center justify-center rounded-xl ${
              confirmVariant === 'danger'
                ? 'bg-rose-100 text-rose-700'
                : 'bg-amber-100 text-amber-700'
            }`}
          >
            <AlertTriangle size={20} />
          </div>
          <h3 className="text-base font-bold text-slate-900">{title}</h3>
        </div>

        <p className="mb-6 text-sm leading-relaxed text-slate-600">{description}</p>

        <div className="flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className={`rounded-lg px-4 py-2 text-sm font-semibold text-white shadow-xs ${
              confirmVariant === 'danger'
                ? 'bg-rose-600 hover:bg-rose-700'
                : 'bg-amber-600 hover:bg-amber-700'
            }`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  )
}

export function SystemSettings() {
  const [originalSettings, setOriginalSettings] = useState(null)
  const [formData, setFormData] = useState({})
  const [systemHealth, setSystemHealth] = useState(null)
  const [capabilities, setCapabilities] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [errorBanner, setErrorBanner] = useState(null)
  const [fieldErrors, setFieldErrors] = useState({})
  const [successBanner, setSuccessBanner] = useState(null)
  const [newRecipientInput, setNewRecipientInput] = useState('')

  // Modals
  const [modalConfig, setModalConfig] = useState({ open: false })

  const loadSettings = async () => {
    try {
      setLoading(true)
      setErrorBanner(null)
      const data = await getSystemSettings()
      const { system_health, capabilities: caps, ...settings } = data
      setOriginalSettings(settings)
      setFormData(settings)
      setSystemHealth(system_health)
      setCapabilities(caps)
    } catch (err) {
      setErrorBanner(err.message || 'Failed to load system settings.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let ignore = false
    getSystemSettings()
      .then((data) => {
        if (!ignore) {
          const { system_health, capabilities: caps, ...settings } = data
          setOriginalSettings(settings)
          setFormData(settings)
          setSystemHealth(system_health)
          setCapabilities(caps)
          setLoading(false)
        }
      })
      .catch((err) => {
        if (!ignore) {
          setErrorBanner(err.message || 'Failed to load system settings.')
          setLoading(false)
        }
      })
    return () => {
      ignore = true
    }
  }, [])

  // Track modified fields
  const changedFields = useMemo(() => {
    if (!originalSettings || !formData) return {}
    const diff = {}
    for (const [key, value] of Object.entries(formData)) {
      if (Array.isArray(value)) {
        const origArr = originalSettings[key] || []
        if (
          value.length !== origArr.length ||
          value.some((item, idx) => item !== origArr[idx])
        ) {
          diff[key] = value
        }
      } else if (value !== originalSettings[key]) {
        diff[key] = value
      }
    }
    return diff
  }, [originalSettings, formData])

  const hasChanges = Object.keys(changedFields).length > 0

  const updateField = (key, value) => {
    setFormData((prev) => ({ ...prev, [key]: value }))
    // Clear field-specific error if present
    if (fieldErrors[key]) {
      setFieldErrors((prev) => {
        const next = { ...prev }
        delete next[key]
        return next
      })
    }
  }

  // File extension toggle
  const toggleFileExtension = (ext) => {
    const current = formData.allowed_file_types || []
    let updated
    if (current.includes(ext)) {
      if (current.length <= 1) {
        setErrorBanner('At least one file extension must remain allowed.')
        return
      }
      updated = current.filter((e) => e !== ext)
    } else {
      updated = [...current, ext]
    }
    updateField('allowed_file_types', updated)
  }

  // Recipient email management
  const addRecipientEmail = () => {
    const email = newRecipientInput.trim().toLowerCase()
    if (!email) return
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(email)) {
      setErrorBanner('Please enter a valid email address.')
      return
    }
    const current = formData.alert_recipients || []
    if (current.includes(email)) {
      setErrorBanner('This email is already in the recipient list.')
      return
    }
    updateField('alert_recipients', [...current, email])
    setNewRecipientInput('')
    setErrorBanner(null)
  }

  const removeRecipientEmail = (email) => {
    const current = formData.alert_recipients || []
    updateField(
      'alert_recipients',
      current.filter((e) => e !== email)
    )
  }

  // Save handler
  const handleSave = async () => {
    if (!hasChanges) return

    try {
      setSaving(true)
      setErrorBanner(null)
      setFieldErrors({})

      const updated = await updateSystemSettings(changedFields)
      const { system_health, capabilities: caps, ...settings } = updated
      setOriginalSettings(settings)
      setFormData(settings)
      if (system_health) setSystemHealth(system_health)
      if (caps) setCapabilities(caps)

      setSuccessBanner(
        `System settings updated successfully. (${Object.keys(changedFields).length} field(s) saved and audited)`
      )
      setTimeout(() => setSuccessBanner(null), 6000)
    } catch (err) {
      if (err.fieldErrors) {
        setFieldErrors(err.fieldErrors)
        setErrorBanner('Please resolve the errors highlighted below.')
      } else {
        setErrorBanner(err.message || 'Failed to update system settings.')
      }
    } finally {
      setSaving(false)
    }
  }

  // Discard handler
  const handleDiscard = () => {
    setFormData(originalSettings)
    setFieldErrors({})
    setErrorBanner(null)
  }

  // Reset to defaults
  const promptReset = () => {
    setModalConfig({
      open: true,
      title: 'Reset All System Settings to Safe Defaults?',
      description:
        'This will immediately revert all 6 sections of system configuration to DocTrust out-of-the-box defaults. An administrative audit event will be recorded.',
      confirmText: 'Reset to Defaults',
      confirmVariant: 'danger',
      onConfirm: async () => {
        setModalConfig({ open: false })
        try {
          setResetting(true)
          setErrorBanner(null)
          const result = await resetSystemSettings()
          const { system_health, capabilities: caps, ...settings } = result
          setOriginalSettings(settings)
          setFormData(settings)
          if (system_health) setSystemHealth(system_health)
          if (caps) setCapabilities(caps)
          setSuccessBanner('All settings have been reset to secure defaults.')
          setTimeout(() => setSuccessBanner(null), 6000)
        } catch (err) {
          setErrorBanner(err.message || 'Failed to reset settings.')
        } finally {
          setResetting(false)
        }
      },
      onCancel: () => setModalConfig({ open: false }),
    })
  }

  // Maintenance mode prompt
  const handleMaintenanceToggle = (newValue) => {
    if (newValue) {
      setModalConfig({
        open: true,
        title: 'Activate Maintenance Mode?',
        description:
          'While maintenance mode is active, non-administrator users will be blocked with HTTP 503 from accessing documents, uploading files, or performing actions. Only administrators will retain access.',
        confirmText: 'Enable Maintenance Mode',
        confirmVariant: 'warning',
        onConfirm: () => {
          updateField('maintenance_mode', true)
          setModalConfig({ open: false })
        },
        onCancel: () => setModalConfig({ open: false }),
      })
    } else {
      updateField('maintenance_mode', false)
    }
  }

  // Legal hold prompt
  const handleLegalHoldToggle = (newValue) => {
    if (newValue) {
      setModalConfig({
        open: true,
        title: 'Enable Organization Legal Hold?',
        description:
          'Activating legal hold strictly disables document purging across the organization. No soft-deleted files can be permanently destroyed while legal hold is active.',
        confirmText: 'Enable Legal Hold',
        confirmVariant: 'warning',
        onConfirm: () => {
          updateField('legal_hold_enabled', true)
          setModalConfig({ open: false })
        },
        onCancel: () => setModalConfig({ open: false }),
      })
    } else {
      updateField('legal_hold_enabled', false)
    }
  }

  return (
    <main className="min-h-screen bg-[#f3f9f6] text-slate-800 md:flex">
      <Sidebar role="Administrator" />

      <div className="min-w-0 flex-1 p-4 pb-28 sm:p-6 sm:pb-32 lg:p-8 lg:pb-36">
        {/* Header */}
        <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold tracking-tight text-slate-900">System Settings</h1>
              <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-bold text-emerald-800">
                Production Config
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-500 sm:text-sm">
              Live administrator configuration for security, storage, retention, and organization policies.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={loadSettings}
              disabled={loading || saving}
              className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 disabled:opacity-50"
            >
              <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
              Reload
            </button>
            <button
              type="button"
              onClick={promptReset}
              disabled={loading || saving || resetting}
              className="inline-flex items-center gap-1.5 rounded-full border border-rose-200 bg-rose-50/70 px-3.5 py-2 text-xs font-semibold text-rose-700 hover:bg-rose-100 disabled:opacity-50"
            >
              <RotateCcw size={13} />
              Reset Defaults
            </button>
          </div>
        </header>

        {/* Global Warnings */}
        {formData.maintenance_mode && (
          <div className="mb-5 flex items-center gap-3 rounded-xl border border-amber-300 bg-amber-50 p-4 text-amber-900 shadow-2xs">
            <ShieldAlert size={22} className="shrink-0 text-amber-600" />
            <div className="text-xs sm:text-sm">
              <strong className="font-semibold">Maintenance Mode is ACTIVE:</strong> Non-administrator users are currently receiving HTTP 503 Service Unavailable.
            </div>
          </div>
        )}

        {formData.legal_hold_enabled && (
          <div className="mb-5 flex items-center gap-3 rounded-xl border border-sky-300 bg-sky-50 p-4 text-sky-900 shadow-2xs">
            <Lock size={22} className="shrink-0 text-sky-600" />
            <div className="text-xs sm:text-sm">
              <strong className="font-semibold">Legal Hold is ACTIVE:</strong> Permanent deletion and document purging are strictly prohibited organization-wide.
            </div>
          </div>
        )}

        {/* Alerts */}
        {successBanner && (
          <div className="mb-5 flex items-center justify-between rounded-xl border border-emerald-300 bg-emerald-50 p-4 text-emerald-900 shadow-2xs">
            <div className="flex items-center gap-2.5 text-xs font-medium sm:text-sm">
              <CheckCircle size={18} className="text-emerald-700" />
              <span>{successBanner}</span>
            </div>
            <button
              type="button"
              onClick={() => setSuccessBanner(null)}
              className="text-emerald-700 hover:text-emerald-900"
            >
              <X size={16} />
            </button>
          </div>
        )}

        {errorBanner && (
          <div className="mb-5 flex items-center justify-between rounded-xl border border-rose-300 bg-rose-50 p-4 text-rose-900 shadow-2xs">
            <div className="flex items-center gap-2.5 text-xs font-medium sm:text-sm">
              <AlertCircle size={18} className="text-rose-700" />
              <span>{errorBanner}</span>
            </div>
            <button
              type="button"
              onClick={() => setErrorBanner(null)}
              className="text-rose-700 hover:text-rose-900"
            >
              <X size={16} />
            </button>
          </div>
        )}

        {loading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-44 animate-pulse rounded-2xl bg-white/70" />
            ))}
          </div>
        ) : (
          <div className="space-y-6">
            {/* Section 0: Live System Health & Infrastructure */}
            {systemHealth && (
              <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-xs md:p-6">
                <div className="mb-4 flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <Server size={18} className="text-emerald-700" />
                    <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700">
                      System Health & Infrastructure
                    </h2>
                  </div>
                  <span
                    className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold ${
                      systemHealth.overall === 'healthy'
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-amber-100 text-amber-800'
                    }`}
                  >
                    <span
                      className={`size-2 rounded-full ${
                        systemHealth.overall === 'healthy' ? 'bg-emerald-500' : 'bg-amber-500'
                      }`}
                    />
                    {systemHealth.overall === 'healthy' ? 'System Healthy' : 'Degraded'}
                  </span>
                </div>

                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-3.5">
                    <div className="flex items-center gap-2 text-xs font-semibold text-slate-500">
                      <Database size={15} /> Database Engine
                    </div>
                    <div className="mt-1 flex items-center justify-between">
                      <span className="text-sm font-bold capitalize text-slate-800">
                        {systemHealth.database?.engine || 'PostgreSQL'}
                      </span>
                      <span className="rounded-md bg-emerald-100 px-2 py-0.5 text-[11px] font-bold text-emerald-800">
                        {systemHealth.database?.status === 'connected' ? 'Connected' : 'Error'}
                      </span>
                    </div>
                  </div>

                  <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-3.5">
                    <div className="flex items-center gap-2 text-xs font-semibold text-slate-500">
                      <HardDrive size={15} /> Private Document Storage
                    </div>
                    <div className="mt-1 flex items-center justify-between">
                      <span className="text-sm font-bold text-slate-800">Filesystem Root</span>
                      <span
                        className={`rounded-md px-2 py-0.5 text-[11px] font-bold ${
                          systemHealth.storage?.status === 'available'
                            ? 'bg-emerald-100 text-emerald-800'
                            : 'bg-rose-100 text-rose-800'
                        }`}
                      >
                        {systemHealth.storage?.status === 'available' ? 'Writable' : 'Unavailable'}
                      </span>
                    </div>
                  </div>

                  <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-3.5 sm:col-span-2 lg:col-span-1">
                    <div className="flex items-center gap-2 text-xs font-semibold text-slate-500">
                      <ShieldCheck size={15} /> Malware & Script Scanner
                    </div>
                    <div className="mt-1 flex items-center justify-between">
                      <span className="text-sm font-bold text-slate-800">Built-in Deep Inspection</span>
                      <span className="rounded-md bg-emerald-100 px-2 py-0.5 text-[11px] font-bold text-emerald-800">
                        Enforcing
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Section 1: General Settings */}
            <SectionCard
              id="section-general"
              title="General Configuration"
              icon={SlidersHorizontal}
              description="Application branding, public support contact, and global access state."
            >
              <TextInput
                label="Application Name"
                description="Branding name displayed across portals, headers, and outgoing emails."
                value={formData.app_name}
                onChange={(val) => updateField('app_name', val)}
                error={fieldErrors.app_name}
              />

              <TextInput
                label="Support Email"
                description="Official support contact provided to users on error pages and alerts."
                type="email"
                value={formData.support_email}
                onChange={(val) => updateField('support_email', val)}
                error={fieldErrors.support_email}
              />

              <ToggleSwitch
                label="Security Notifications"
                description="Deliver security alert notifications when significant account changes occur."
                checked={Boolean(formData.security_notifications_enabled)}
                onChange={(val) => updateField('security_notifications_enabled', val)}
              />

              <ToggleSwitch
                label="Maintenance Mode"
                description="Restrict non-admin access while performing database maintenance or platform updates."
                checked={Boolean(formData.maintenance_mode)}
                onChange={handleMaintenanceToggle}
                warning={
                  formData.maintenance_mode
                    ? 'Maintenance mode is currently blocking all non-administrator users.'
                    : null
                }
              />
            </SectionCard>

            {/* Section 2: Authentication & Session Security */}
            <SectionCard
              id="section-auth"
              title="Authentication & Session Security"
              icon={LockKeyhole}
              description="Idle timeouts, session lifetimes, password policies, and brute-force lockouts."
            >
              <NumberInput
                label="Session Idle Timeout"
                description="Session expires automatically after this many minutes of user inactivity (5–1440)."
                unit="minutes"
                min={5}
                max={1440}
                value={formData.session_idle_timeout_minutes}
                onChange={(val) => updateField('session_idle_timeout_minutes', val)}
                error={fieldErrors.session_idle_timeout_minutes}
              />

              <NumberInput
                label="Maximum Session Lifetime"
                description="Absolute session lifetime requiring re-login regardless of activity (1–168)."
                unit="hours"
                min={1}
                max={168}
                value={formData.max_session_lifetime_hours}
                onChange={(val) => updateField('max_session_lifetime_hours', val)}
                error={fieldErrors.max_session_lifetime_hours}
              />

              <NumberInput
                label="Minimum Password Length"
                description="Enforced on user registration and password reset operations (8–128)."
                unit="characters"
                min={8}
                max={128}
                value={formData.min_password_length}
                onChange={(val) => updateField('min_password_length', val)}
                error={fieldErrors.min_password_length}
              />

              <ToggleSwitch
                label="Require MFA for Administrators"
                description="Multi-factor authentication mandatory for admin accounts."
                checked={Boolean(formData.require_mfa_admins)}
                onChange={(val) => updateField('require_mfa_admins', val)}
                capability={capabilities?.mfa}
              />

              <ToggleSwitch
                label="Require Re-authentication for Sensitive Operations"
                description="Prompt for password verification before permanent deletions and settings changes."
                checked={Boolean(formData.require_reauth_sensitive)}
                onChange={(val) => updateField('require_reauth_sensitive', val)}
              />

              <NumberInput
                label="Failed Login Attempt Limit"
                description="Temporarily lock accounts after consecutive invalid password submissions (3–20)."
                unit="attempts"
                min={3}
                max={20}
                value={formData.failed_login_limit}
                onChange={(val) => updateField('failed_login_limit', val)}
                error={fieldErrors.failed_login_limit}
              />

              <NumberInput
                label="Account Lockout Duration"
                description="Lockout period before an account may attempt password verification again (1–1440)."
                unit="minutes"
                min={1}
                max={1440}
                value={formData.lockout_duration_minutes}
                onChange={(val) => updateField('lockout_duration_minutes', val)}
                error={fieldErrors.lockout_duration_minutes}
              />
            </SectionCard>

            {/* Section 3: File Upload & Storage */}
            <SectionCard
              id="section-storage"
              title="File Upload & Storage Policies"
              icon={Upload}
              description="Allowed file types, upload size boundaries, and organization storage quota enforcement."
            >
              <div className="border-b border-slate-100/70 pb-4">
                <div className="mb-2">
                  <span className="text-sm font-semibold text-slate-800">Permitted Upload File Formats</span>
                  <p className="text-xs text-slate-500">
                    File uploads are strictly validated by magic byte signatures and content structure.
                  </p>
                </div>

                <div className="flex flex-wrap gap-2">
                  {AVAILABLE_EXTENSIONS.map(({ ext, label }) => {
                    const isSelected = (formData.allowed_file_types || []).includes(ext)
                    return (
                      <button
                        key={ext}
                        type="button"
                        onClick={() => toggleFileExtension(ext)}
                        className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-semibold transition ${
                          isSelected
                            ? 'border-emerald-600 bg-emerald-50 text-emerald-900 shadow-2xs'
                            : 'border-slate-200 bg-white text-slate-500 hover:border-slate-300 hover:bg-slate-50'
                        }`}
                      >
                        <span
                          className={`size-2 rounded-full ${
                            isSelected ? 'bg-emerald-600' : 'bg-slate-300'
                          }`}
                        />
                        {ext}
                        <span className="text-[10px] text-slate-400">({label})</span>
                      </button>
                    )
                  })}
                </div>
                {fieldErrors.allowed_file_types && (
                  <p className="mt-1.5 text-xs font-semibold text-rose-600">
                    {fieldErrors.allowed_file_types}
                  </p>
                )}
              </div>

              <NumberInput
                label="Maximum Upload Size"
                description="Per-file upload limit enforced during ingestion (1–500)."
                unit="MB"
                min={1}
                max={500}
                value={formData.max_upload_size_mb}
                onChange={(val) => updateField('max_upload_size_mb', val)}
                error={fieldErrors.max_upload_size_mb}
              />

              <NumberInput
                label="User Storage Quota"
                description="Total storage allocation permitted per active employee (10–50000)."
                unit="MB"
                min={10}
                max={50000}
                value={formData.user_storage_quota_mb}
                onChange={(val) => updateField('user_storage_quota_mb', val)}
                error={fieldErrors.user_storage_quota_mb}
              />

              <NumberInput
                label="Organization Storage Limit"
                description="Aggregate storage boundary across all documents and versions (100–500000)."
                unit="MB"
                min={100}
                max={500000}
                value={formData.org_storage_limit_mb}
                onChange={(val) => updateField('org_storage_limit_mb', val)}
                error={fieldErrors.org_storage_limit_mb}
              />

              <NumberInput
                label="Storage Warning Threshold"
                description="Trigger alerts when user or org storage exceeds this percentage (50–99)."
                unit="%"
                min={50}
                max={99}
                value={formData.storage_warning_threshold_pct}
                onChange={(val) => updateField('storage_warning_threshold_pct', val)}
                error={fieldErrors.storage_warning_threshold_pct}
              />

              <ToggleSwitch
                label="Block Executable File Uploads"
                description="Hard rejection of executable, batch, script, and macro-enabled files (.exe, .bat, .sh, .cmd)."
                checked={Boolean(formData.block_executable_uploads)}
                onChange={(val) => updateField('block_executable_uploads', val)}
              />
            </SectionCard>

            {/* Section 4: Organization Document Security Policies */}
            <SectionCard
              id="section-security-policies"
              title="Organization Document Security Policies"
              icon={Shield}
              description="Default document visibility, external sharing boundaries, and download permissions."
            >
              <SelectInput
                label="Default Document Visibility"
                description="Baseline visibility assigned when an employee uploads a new document."
                value={formData.default_document_visibility}
                onChange={(val) => updateField('default_document_visibility', val)}
                options={[
                  ['PRIVATE', 'Private (Owner only)'],
                  ['RESTRICTED', 'Restricted (Organization explicit shares)'],
                ]}
                error={fieldErrors.default_document_visibility}
              />

              <ToggleSwitch
                label="Allow External Sharing"
                description="Permit document owners to invite external collaborators outside the organization."
                checked={Boolean(formData.allow_external_sharing)}
                onChange={(val) => updateField('allow_external_sharing', val)}
              />

              <ToggleSwitch
                label="Allow Public Share Links"
                description="Permit generating unauthenticated public view links for documents."
                checked={Boolean(formData.allow_public_links)}
                onChange={(val) => updateField('allow_public_links', val)}
              />

              <SelectInput
                label="Default Share Permission Level"
                description="Default capability granted when adding a new collaborator."
                value={formData.default_share_permission}
                onChange={(val) => updateField('default_share_permission', val)}
                options={[
                  ['VIEW', 'View Only'],
                  ['COMMENT', 'Comment'],
                  ['EDIT', 'Edit'],
                ]}
                error={fieldErrors.default_share_permission}
              />

              <ToggleSwitch
                label="Allow Document Downloads"
                description="Allow collaborators to download original decrypted document binaries."
                checked={Boolean(formData.allow_downloads)}
                onChange={(val) => updateField('allow_downloads', val)}
              />

              <ToggleSwitch
                label="Allow Document Printing"
                description="Allow browser document print operations."
                checked={Boolean(formData.allow_printing)}
                onChange={(val) => updateField('allow_printing', val)}
                capability={capabilities?.printing_enforcement}
              />

              <NumberInput
                label="Maximum Share Duration"
                description="Upper limit on document sharing lifespans before access revokes automatically (1–365)."
                unit="days"
                min={1}
                max={365}
                value={formData.max_share_duration_days}
                onChange={(val) => updateField('max_share_duration_days', val)}
                error={fieldErrors.max_share_duration_days}
              />

              <ToggleSwitch
                label="Require Administrator Approval for Ownership Transfer"
                description="Document re-assignment between employees must be authorized by an admin."
                checked={Boolean(formData.require_transfer_approval)}
                onChange={(val) => updateField('require_transfer_approval', val)}
              />
            </SectionCard>

            {/* Section 5: Retention & Recovery */}
            <SectionCard
              id="section-retention"
              title="Retention & Recovery Policies"
              icon={History}
              description="Trash bin recovery lifespans, audit trail compliance retention, and legal hold."
            >
              <NumberInput
                label="Soft-Deleted Document Recovery Window"
                description="Days soft-deleted documents remain in trash and can be restored by owners (1–365)."
                unit="days"
                min={1}
                max={365}
                value={formData.deleted_recovery_days}
                onChange={(val) => updateField('deleted_recovery_days', val)}
                error={fieldErrors.deleted_recovery_days}
              />

              <NumberInput
                label="Audit Log Retention Period"
                description="Compliant immutable retention window for audit trail records (90–3650)."
                unit="days"
                min={90}
                max={3650}
                value={formData.audit_retention_days}
                onChange={(val) => updateField('audit_retention_days', val)}
                error={fieldErrors.audit_retention_days}
              />

              <ToggleSwitch
                label="Organization Legal Hold"
                description="Strict compliance lock. Completely blocks all document purges across the system."
                checked={Boolean(formData.legal_hold_enabled)}
                onChange={handleLegalHoldToggle}
                warning={
                  formData.legal_hold_enabled
                    ? 'Legal hold is active: document purge operations are strictly blocked.'
                    : null
                }
              />

              <ToggleSwitch
                label="Automatic Permanent Purge on Expiry"
                description="Automatically destroy physical file bytes once the recovery window expires."
                checked={Boolean(formData.auto_permanent_delete)}
                onChange={(val) => updateField('auto_permanent_delete', val)}
              />

              <NumberInput
                label="Pre-Deletion Reminder Window"
                description="Days before permanent purge to send notice. Must be fewer days than recovery window (1–30)."
                unit="days"
                min={1}
                max={30}
                value={formData.deletion_reminder_days}
                onChange={(val) => updateField('deletion_reminder_days', val)}
                error={fieldErrors.deletion_reminder_days}
              />
            </SectionCard>

            {/* Section 6: Audit, Monitoring & Alerts */}
            <SectionCard
              id="section-audit"
              title="Audit, Monitoring & Security Alerts"
              icon={Activity}
              description="Audit logging granular switches, intrusion thresholds, and security alert recipients."
            >
              <div className="space-y-4 border-b border-slate-100/70 pb-4">
                <span className="text-sm font-semibold text-slate-800">Granular Audit Logging Events</span>
                <div className="grid gap-3 sm:grid-cols-2">
                  <label className="flex items-center gap-2.5 text-xs font-medium text-slate-700">
                    <input
                      type="checkbox"
                      checked={Boolean(formData.log_document_access)}
                      onChange={(e) => updateField('log_document_access', e.target.checked)}
                      className="size-4 rounded-sm border-slate-300 accent-emerald-700"
                    />
                    Document View & Access Events
                  </label>

                  <label className="flex items-center gap-2.5 text-xs font-medium text-slate-700">
                    <input
                      type="checkbox"
                      checked={Boolean(formData.log_permission_changes)}
                      onChange={(e) => updateField('log_permission_changes', e.target.checked)}
                      className="size-4 rounded-sm border-slate-300 accent-emerald-700"
                    />
                    Permission Changes & Shares
                  </label>

                  <label className="flex items-center gap-2.5 text-xs font-medium text-slate-700">
                    <input
                      type="checkbox"
                      checked={Boolean(formData.log_failed_logins)}
                      onChange={(e) => updateField('log_failed_logins', e.target.checked)}
                      className="size-4 rounded-sm border-slate-300 accent-emerald-700"
                    />
                    Failed Authentication Attempts
                  </label>

                  <label className="flex items-center gap-2.5 text-xs font-medium text-slate-700">
                    <input
                      type="checkbox"
                      checked={Boolean(formData.log_file_downloads)}
                      onChange={(e) => updateField('log_file_downloads', e.target.checked)}
                      className="size-4 rounded-sm border-slate-300 accent-emerald-700"
                    />
                    Binary File Download Events
                  </label>

                  <label className="flex items-center gap-2.5 text-xs font-medium text-slate-700">
                    <input
                      type="checkbox"
                      checked={Boolean(formData.log_admin_actions)}
                      onChange={(e) => updateField('log_admin_actions', e.target.checked)}
                      className="size-4 rounded-sm border-slate-300 accent-emerald-700"
                    />
                    System Settings & Administrative Actions
                  </label>
                </div>
              </div>

              <NumberInput
                label="Failed Login Alert Threshold"
                description="Trigger an automated alert after this many failed logins from a single account (3–50)."
                unit="attempts"
                min={3}
                max={50}
                value={formData.failed_login_alert_threshold}
                onChange={(val) => updateField('failed_login_alert_threshold', val)}
                error={fieldErrors.failed_login_alert_threshold}
              />

              <NumberInput
                label="Unusual Download Spike Threshold"
                description="Detect rapid successive document downloads in an anomaly window (5–200)."
                unit="downloads"
                min={5}
                max={200}
                value={formData.unusual_download_alert_threshold}
                onChange={(val) => updateField('unusual_download_alert_threshold', val)}
                error={fieldErrors.unusual_download_alert_threshold}
              />

              {/* Alert Recipient Emails */}
              <div className="border-b border-slate-100/70 pb-4">
                <label className="text-sm font-semibold text-slate-800">Security Alert Recipient List</label>
                <p className="mt-0.5 text-xs text-slate-500">
                  Security team and compliance emails notified upon critical security events.
                </p>

                <div className="mt-2.5 flex flex-wrap gap-2">
                  {(formData.alert_recipients || []).map((email) => (
                    <span
                      key={email}
                      className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700 shadow-2xs"
                    >
                      {email}
                      <button
                        type="button"
                        onClick={() => removeRecipientEmail(email)}
                        className="text-slate-400 hover:text-rose-600"
                      >
                        <X size={13} />
                      </button>
                    </span>
                  ))}
                  {(formData.alert_recipients || []).length === 0 && (
                    <span className="text-xs text-slate-400">No alert recipients designated yet.</span>
                  )}
                </div>

                <div className="mt-3 flex max-w-md items-center gap-2">
                  <input
                    type="email"
                    placeholder="security-lead@company.com"
                    value={newRecipientInput}
                    onChange={(e) => setNewRecipientInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault()
                        addRecipientEmail()
                      }
                    }}
                    className="flex-1 rounded-lg border border-slate-300 bg-slate-50/50 px-3 py-1.5 text-xs text-slate-800 focus:border-emerald-600 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-emerald-600"
                  />
                  <button
                    type="button"
                    onClick={addRecipientEmail}
                    className="rounded-lg bg-emerald-800 px-3 py-1.5 text-xs font-semibold text-white shadow-2xs hover:bg-emerald-900"
                  >
                    Add Recipient
                  </button>
                </div>
              </div>

              <SelectInput
                label="Security Alert Delivery Channel"
                description="Delivery method used for dispatching high-priority security notifications."
                value={formData.security_notification_method}
                onChange={(val) => updateField('security_notification_method', val)}
                options={[
                  ['email', 'Email Notifications Only'],
                  ['in_app', 'In-App Alerts Only'],
                  ['both', 'Both Email & In-App Alerts'],
                ]}
                error={fieldErrors.security_notification_method}
              />
            </SectionCard>
          </div>
        )}
      </div>

      {/* Floating Action Bar */}
      {hasChanges && (
        <aside
          aria-label="Pending changes"
          className="fixed bottom-0 left-0 right-0 z-40 border-t border-slate-200 bg-white/95 px-4 py-3 shadow-xl backdrop-blur-md md:left-60"
        >
          <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="flex size-6 items-center justify-center rounded-full bg-amber-100 text-xs font-bold text-amber-800">
                {Object.keys(changedFields).length}
              </span>
              <span className="text-xs font-semibold text-slate-700 sm:text-sm">
                Unsaved modifications pending persistence
              </span>
            </div>

            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleDiscard}
                disabled={saving}
                className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50 sm:text-sm"
              >
                Discard
              </button>
              <button
                type="button"
                onClick={handleSave}
                disabled={saving}
                className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-700 px-5 py-2 text-xs font-semibold text-white shadow-md hover:bg-emerald-800 disabled:opacity-50 sm:text-sm"
              >
                {saving ? (
                  <>
                    <RefreshCw size={14} className="animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save size={14} />
                    Save Changes
                  </>
                )}
              </button>
            </div>
          </div>
        </aside>
      )}

      {/* Confirmation Modal */}
      <ConfirmationModal
        open={modalConfig.open}
        title={modalConfig.title}
        description={modalConfig.description}
        confirmText={modalConfig.confirmText}
        confirmVariant={modalConfig.confirmVariant}
        onConfirm={modalConfig.onConfirm}
        onCancel={modalConfig.onCancel}
      />
    </main>
  )
}
export default SystemSettings
