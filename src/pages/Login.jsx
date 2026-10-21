import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ShieldCheck,
  LockKeyhole,
  History,
  UserRound,
  Eye,
  EyeOff,
  LogIn,
  ArrowRight,
  X,
} from 'lucide-react'
import { getCurrentUser, login, requestPasswordReset } from '../services/auth.js'

export default function Login() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('Administrator')
  const [showPassword, setShowPassword] = useState(false)
  const [rememberMe, setRememberMe] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  // Forgot password modal state
  const [showForgotModal, setShowForgotModal] = useState(false)
  const [forgotEmail, setForgotEmail] = useState('')
  const [forgotLoading, setForgotLoading] = useState(false)
  const [forgotMessage, setForgotMessage] = useState('')
  const [forgotError, setForgotError] = useState('')

  useEffect(() => {
    let active = true
    getCurrentUser().then((user) => {
      if (active && user) {
        if (user.role === 'ADMIN') {
          navigate('/admin/dashboard', { replace: true })
        } else {
          navigate('/employee/dashboard', { replace: true })
        }
      }
    })
    return () => {
      active = false
    }
  }, [navigate])

  async function handleSubmit(event) {
    event.preventDefault()
    setLoading(true)
    setError('')
    setMessage('')

    const roleMap = { Administrator: 'ADMIN', Employee: 'EMPLOYEE' }
    const expectedRole = roleMap[role] || 'ADMIN'

    try {
      const user = await login({ username, password, rememberMe, expectedRole })
      // Redirect according to verified user role from backend
      if (user.role === 'ADMIN') {
        navigate('/admin/dashboard')
      } else {
        navigate('/employee/dashboard')
      }
    } catch (err) {
      setError(err.message || 'Invalid username/email or password.')
    } finally {
      setLoading(false)
    }
  }

  async function handleForgotSubmit(e) {
    e.preventDefault()
    setForgotLoading(true)
    setForgotError('')
    setForgotMessage('')

    try {
      const res = await requestPasswordReset(forgotEmail)
      setForgotMessage(
        res.detail || 'If an account exists for that email, password reset instructions will be sent.'
      )
    } catch (err) {
      setForgotError(err.message || 'Unable to process password reset request.')
    } finally {
      setForgotLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-[#eafbf3] p-0 sm:p-5">
      <div className="grid min-h-screen overflow-hidden bg-white sm:min-h-[calc(100vh-40px)] lg:grid-cols-[1.1fr_1fr]">
        <section className="flex flex-col justify-center bg-gradient-to-b from-[#064b3b] to-[#00382c] px-8 py-12 text-white sm:px-12 lg:px-[9%]">
          <div className="mb-7 flex items-center gap-3">
            <ShieldCheck size={39} strokeWidth={2.2} />
            <span className="text-4xl font-bold tracking-tight">DocTrust</span>
          </div>

          <h1 className="mb-5 text-xl font-bold leading-snug sm:text-2xl">
            Secure document sharing and permission management
          </h1>

          <ul className="space-y-5 text-base text-white/80 sm:text-lg">
            <li className="flex items-center gap-3">
              <LockKeyhole size={23} />
              <span>Role-based access control</span>
            </li>
            <li className="flex items-center gap-3">
              <ShieldCheck size={23} />
              <span>Document-specific permissions</span>
            </li>
            <li className="flex items-center gap-3">
              <History size={23} />
              <span>Complete audit trail</span>
            </li>
          </ul>

          <div className="mt-9 flex flex-wrap gap-3 text-sm font-semibold">
            <span className="flex items-center gap-2 rounded-full bg-white/15 px-4 py-2">
              <ShieldCheck size={17} /> Administrator
            </span>
            <span className="flex items-center gap-2 rounded-full bg-white/15 px-4 py-2">
              <UserRound size={17} /> Employee
            </span>
          </div>
        </section>

        <section className="flex items-center justify-center bg-[#eafbf3] px-5 py-10 sm:px-10 lg:px-12">
          <div className="w-full max-w-[580px] rounded-[26px] bg-white p-6 shadow-[0_8px_32px_rgba(20,80,55,0.09)] sm:p-9">
            <h2 className="text-2xl font-bold tracking-tight text-[#172033] sm:text-[30px]">
              {role} Login
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-slate-500 sm:text-base">
              Sign in to manage users, audit activity and monitor security
            </p>

            <form onSubmit={handleSubmit} className="mt-5 space-y-4">
              <div>
                <label htmlFor="role" className="mb-2 block text-sm font-semibold text-slate-800">
                  Sign in as
                </label>
                <select
                  id="role"
                  value={role}
                  onChange={(event) => setRole(event.target.value)}
                  className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3.5 text-base outline-none focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
                >
                  <option>Administrator</option>
                  <option>Employee</option>
                </select>
              </div>
              <div>
                <label htmlFor="username" className="mb-2 block text-sm font-semibold text-slate-800">
                  Email or username
                </label>
                <input
                  id="username"
                  name="username"
                  type="text"
                  autoComplete="username"
                  placeholder="admin@example.com"
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  required
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3.5 text-base outline-none transition focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
                />
              </div>

              <div>
                <label htmlFor="password" className="mb-2 block text-sm font-semibold text-slate-800">
                  Password
                </label>
                <div className="flex items-center gap-2">
                  <input
                    id="password"
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    placeholder="Enter your password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    required
                    className="min-w-0 flex-1 rounded-2xl border border-slate-300 px-4 py-3.5 text-base outline-none transition focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((visible) => !visible)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    className="flex size-12 shrink-0 items-center justify-center rounded-full border border-slate-300 text-emerald-800 transition hover:bg-emerald-50"
                  >
                    {showPassword ? <EyeOff size={22} /> : <Eye size={22} />}
                  </button>
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
                <label className="flex cursor-pointer items-center gap-3 font-medium text-slate-800">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(event) => setRememberMe(event.target.checked)}
                    className="size-5 accent-emerald-700"
                  />
                  Remember me
                </label>

                <button
                  type="button"
                  onClick={() => {
                    setShowForgotModal(true)
                    setForgotMessage('')
                    setForgotError('')
                  }}
                  className="flex items-center gap-2 font-semibold text-emerald-800 hover:text-emerald-950"
                >
                  <LockKeyhole size={18} />
                  Forgot password?
                </button>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="flex w-full items-center justify-center gap-2 rounded-full bg-[#087c5b] px-5 py-3.5 font-bold text-white transition hover:bg-[#06684d] focus-visible:outline-offset-4 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <LogIn size={19} />
                {loading ? 'Signing In...' : 'Log In'}
                <ArrowRight size={16} className="sr-only" />
              </button>

              {error && (
                <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
                  {error}
                </p>
              )}

              {message && (
                <p role="status" className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-900">
                  {message}
                </p>
              )}

              <p className="pt-1 text-xs leading-relaxed text-slate-500">
                Protected by DocTrust enterprise role-based authorization and session security.
              </p>
            </form>
          </div>
        </section>
      </div>

      {/* Forgot Password Modal */}
      {showForgotModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl sm:p-8">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <span className="flex size-10 items-center justify-center rounded-xl bg-emerald-100 text-emerald-800">
                  <LockKeyhole size={20} />
                </span>
                <h3 className="text-xl font-bold text-slate-900">Reset Password</h3>
              </div>
              <button
                type="button"
                onClick={() => setShowForgotModal(false)}
                className="rounded-full p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                aria-label="Close"
              >
                <X size={20} />
              </button>
            </div>

            <p className="mb-4 text-sm text-slate-600">
              Enter your registered email address and we will send password reset instructions.
            </p>

            <form onSubmit={handleForgotSubmit} className="space-y-4">
              <div>
                <label htmlFor="forgot-email" className="mb-2 block text-sm font-semibold text-slate-800">
                  Registered Email
                </label>
                <input
                  id="forgot-email"
                  type="email"
                  required
                  placeholder="user@example.com"
                  value={forgotEmail}
                  onChange={(e) => setForgotEmail(e.target.value)}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 text-base outline-none transition focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
                />
              </div>

              {forgotError && (
                <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">
                  {forgotError}
                </p>
              )}

              {forgotMessage && (
                <div role="status" className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-900">
                  <p className="font-semibold">{forgotMessage}</p>
                  <p className="mt-1 text-emerald-700">Check your inbox or developer terminal for the reset link.</p>
                </div>
              )}

              <div className="mt-6 flex justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setShowForgotModal(false)}
                  className="rounded-full border border-slate-300 px-5 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  Close
                </button>
                <button
                  type="submit"
                  disabled={forgotLoading}
                  className="rounded-full bg-[#087c5b] px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#06684d] disabled:opacity-60"
                >
                  {forgotLoading ? 'Sending...' : 'Send Reset Link'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </main>
  )
}
