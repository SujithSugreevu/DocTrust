import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import {
  ShieldCheck,
  LockKeyhole,
  Eye,
  EyeOff,
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react'
import { confirmPasswordReset } from '../services/auth.js'

export default function ResetPassword() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const uid = searchParams.get('uid') || ''
  const token = searchParams.get('token') || ''

  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  const isLinkInvalid = !uid || !token

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    if (newPassword.length < 10) {
      setError('Password must be at least 10 characters long.')
      return
    }

    setLoading(true)

    try {
      await confirmPasswordReset({
        uid,
        token,
        newPassword,
        confirmPassword,
      })
      setSuccess(true)
    } catch (err) {
      setError(err.message || 'The password reset link is invalid or has expired.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-[#eafbf3] p-0 sm:p-5">
      <div className="flex min-h-screen items-center justify-center sm:min-h-[calc(100vh-40px)]">
        <div className="w-full max-w-[520px] rounded-[26px] bg-white p-6 shadow-[0_8px_32px_rgba(20,80,55,0.09)] sm:p-10">
          <div className="mb-6 flex items-center gap-3">
            <span className="flex size-12 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-800">
              <ShieldCheck size={28} />
            </span>
            <div>
              <span className="text-2xl font-bold tracking-tight text-[#172033]">DocTrust</span>
              <p className="text-xs text-slate-500">Security Credentials</p>
            </div>
          </div>

          <h1 className="text-2xl font-bold tracking-tight text-[#172033]">
            Set New Password
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            Please choose a strong password containing at least 10 characters.
          </p>

          {isLinkInvalid ? (
            <div className="mt-6 space-y-4">
              <div role="alert" className="flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
                <AlertTriangle size={20} className="shrink-0 text-rose-700" />
                <div>
                  <p className="font-semibold">Invalid or missing reset link</p>
                  <p className="mt-1 text-xs text-rose-700">
                    This password reset link is incomplete. Please request a new link from the login page.
                  </p>
                </div>
              </div>

              <Link
                to="/"
                className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-[#087c5b] px-5 py-3.5 font-bold text-white transition hover:bg-[#06684d]"
              >
                <ArrowLeft size={16} /> Return to Login
              </Link>
            </div>
          ) : success ? (
            <div className="mt-6 space-y-4">
              <div role="status" className="flex items-start gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
                <CheckCircle2 size={22} className="shrink-0 text-emerald-700" />
                <div>
                  <p className="font-semibold">Password Reset Successful</p>
                  <p className="mt-1 text-xs text-emerald-800">
                    Your password has been changed. You can now log in using your new credentials.
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={() => navigate('/')}
                className="flex w-full items-center justify-center gap-2 rounded-full bg-[#087c5b] px-5 py-3.5 font-bold text-white transition hover:bg-[#06684d]"
              >
                Proceed to Login
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="mt-6 space-y-4">
              <div>
                <label
                  htmlFor="new-password"
                  className="mb-2 block text-sm font-semibold text-slate-800"
                >
                  New Password
                </label>
                <div className="flex items-center gap-2">
                  <input
                    id="new-password"
                    name="new-password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    placeholder="At least 10 characters"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
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

              <div>
                <label
                  htmlFor="confirm-password"
                  className="mb-2 block text-sm font-semibold text-slate-800"
                >
                  Confirm New Password
                </label>
                <input
                  id="confirm-password"
                  name="confirm-password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  placeholder="Repeat your new password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3.5 text-base outline-none transition focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
                />
              </div>

              {error && (
                <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="flex w-full items-center justify-center gap-2 rounded-full bg-[#087c5b] px-5 py-3.5 font-bold text-white transition hover:bg-[#06684d] focus-visible:outline-offset-4 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <LockKeyhole size={18} />
                {loading ? 'Saving New Password...' : 'Save New Password'}
              </button>

              <div className="pt-2 text-center">
                <Link
                  to="/"
                  className="inline-flex items-center gap-2 text-sm font-semibold text-emerald-800 hover:text-emerald-950"
                >
                  <ArrowLeft size={16} /> Back to Login
                </Link>
              </div>
            </form>
          )}
        </div>
      </div>
    </main>
  )
}
