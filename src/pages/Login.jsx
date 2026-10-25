import { useCallback, useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
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
  Copy,
  Download,
} from 'lucide-react'
import {
  getCurrentUser,
  login,
  requestPasswordReset,
  verifyLoginTwoFactor,
  setupLoginTwoFactor,
} from '../services/auth.js'

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('Administrator')
  const [showPassword, setShowPassword] = useState(false)
  const [rememberMe, setRememberMe] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  // 2FA Challenge state
  const [mfaChallenge, setMfaChallenge] = useState(null)
  const [mfaCode, setMfaCode] = useState('')
  const [mfaUseRecovery, setMfaUseRecovery] = useState(false)
  const [mfaSetupData, setMfaSetupData] = useState(null)
  const [mfaRecoveryCodes, setMfaRecoveryCodes] = useState(null)
  const [mfaCopiedCodes, setMfaCopiedCodes] = useState(false)
  const [mfaVerifiedUser, setMfaVerifiedUser] = useState(null)
  const [mfaLoading, setMfaLoading] = useState(false)
  const [mfaError, setMfaError] = useState('')

  // Forgot password modal state
  const [showForgotModal, setShowForgotModal] = useState(false)
  const [forgotEmail, setForgotEmail] = useState('')
  const [forgotLoading, setForgotLoading] = useState(false)
  const [forgotMessage, setForgotMessage] = useState('')
  const [forgotError, setForgotError] = useState('')

  const navigateForRole = useCallback((userRole) => {
    const rolePrefix = userRole === 'ADMIN' ? '/admin/' : '/employee/'
    const defaultRoute = userRole === 'ADMIN' ? '/admin/dashboard' : '/employee/dashboard'
    const destination = location.state?.from
    navigate(
      typeof destination === 'string' && destination.startsWith(rolePrefix)
        ? destination
        : defaultRoute,
      { replace: true },
    )
  }, [location.state, navigate])

  useEffect(() => {
    let active = true
    getCurrentUser().then((user) => {
      if (active && user) {
        navigateForRole(user.role)
      }
    }).catch((err) => {
      if (active) {
        setError(`Unable to verify your existing session. ${err.message}`)
      }
    })
    return () => {
      active = false
    }
  }, [navigateForRole])

  async function handleSubmit(event) {
    event.preventDefault()
    setLoading(true)
    setError('')
    setMessage('')

    const roleMap = { Administrator: 'ADMIN', Employee: 'EMPLOYEE' }
    const expectedRole = roleMap[role] || 'ADMIN'

    try {
      const res = await login({ username, password, rememberMe, expectedRole })
      if (res.mfa_required) {
        setMfaChallenge({
          mfaToken: res.mfa_token,
          setupRequired: Boolean(res.mfa_setup_required),
          expectedRole,
        })
        setMfaCode('')
        setMfaError('')
        setMfaUseRecovery(false)
        if (res.mfa_setup_required) {
          handleStartMfaSetup(res.mfa_token)
        }
        return
      }

      // Redirect according to verified user role from backend
      navigateForRole(res.role)
    } catch (err) {
      setError(err.message || 'Invalid username/email or password.')
    } finally {
      setLoading(false)
    }
  }

  async function handleStartMfaSetup(token) {
    setMfaLoading(true)
    setMfaError('')
    try {
      const setupData = await setupLoginTwoFactor({ mfaToken: token, action: 'start' })
      setMfaSetupData(setupData)
    } catch (err) {
      setMfaError(err.message || 'Failed to start mandatory two-factor setup.')
    } finally {
      setMfaLoading(false)
    }
  }

  async function handleVerifyMfaLogin(e) {
    e.preventDefault()
    if (!mfaCode.trim()) {
      setMfaError(mfaUseRecovery ? 'Please enter a recovery code.' : 'Please enter the 6-digit verification code.')
      return
    }

    setMfaLoading(true)
    setMfaError('')
    try {
      const verifiedUser = await verifyLoginTwoFactor({
        mfaToken: mfaChallenge.mfaToken,
        code: mfaCode.trim(),
      })
      navigateForRole(verifiedUser.role)
    } catch (err) {
      setMfaError(err.message || 'Verification failed. Please check the code and try again.')
    } finally {
      setMfaLoading(false)
    }
  }

  async function handleVerifyMfaSetup(e) {
    e.preventDefault()
    if (!mfaCode.trim() || mfaCode.trim().length !== 6) {
      setMfaError('Please enter the 6-digit code from your authenticator app.')
      return
    }

    setMfaLoading(true)
    setMfaError('')
    try {
      const res = await setupLoginTwoFactor({
        mfaToken: mfaChallenge.mfaToken,
        action: 'verify',
        code: mfaCode.trim(),
      })
      setMfaRecoveryCodes(res.recovery_codes || [])
      setMfaVerifiedUser(res.user)
    } catch (err) {
      setMfaError(err.message || 'Setup verification failed. Check the code.')
    } finally {
      setMfaLoading(false)
    }
  }

  function handleFinishMandatorySetup() {
    navigateForRole(mfaVerifiedUser?.role)
  }

  function handleCopyMfaRecoveryCodes() {
    if (mfaRecoveryCodes?.length) {
      navigator.clipboard.writeText(mfaRecoveryCodes.join('\n'))
      setMfaCopiedCodes(true)
      setTimeout(() => setMfaCopiedCodes(false), 2500)
    }
  }

  function handleDownloadMfaRecoveryCodes() {
    if (!mfaRecoveryCodes?.length) return
    const content = [
      'DocTrust Two-Factor Authentication Recovery Codes',
      `Account: ${username}`,
      `Generated: ${new Date().toISOString()}`,
      '',
      'Important:',
      '- Each code is single-use and can only be used once.',
      '- Keep these codes safe. If you lose your authenticator, they are your only recovery option.',
      '',
      ...mfaRecoveryCodes.map((c, i) => `${i + 1}. ${c}`),
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

  function handleCancelMfaChallenge() {
    setMfaChallenge(null)
    setMfaCode('')
    setMfaError('')
    setMfaSetupData(null)
    setMfaRecoveryCodes(null)
    setMfaVerifiedUser(null)
    setMfaUseRecovery(false)
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
            {/* Case 1: Recovery Codes Display After Mandatory Setup */}
            {mfaRecoveryCodes ? (
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <span className="flex size-11 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-800">
                    <ShieldCheck size={24} />
                  </span>
                  <div>
                    <h2 className="text-2xl font-bold tracking-tight text-[#172033]">
                      Two-Factor Setup Complete
                    </h2>
                    <p className="text-xs text-slate-500">
                      Save your emergency recovery codes
                    </p>
                  </div>
                </div>

                <div className="mt-5 rounded-2xl border-2 border-emerald-500 bg-emerald-50/50 p-4 sm:p-5">
                  <p className="text-xs text-slate-700 leading-relaxed mb-3">
                    <strong>Important:</strong> These recovery codes are only displayed once. Store them in a secure password manager or offline safe. If you lose your authenticator app, each code can be used once to access your account.
                  </p>

                  <div className="grid grid-cols-2 gap-2 font-mono text-center text-xs font-bold text-slate-800 mb-4">
                    {mfaRecoveryCodes.map((code, idx) => (
                      <div key={idx} className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 shadow-2xs tracking-wider">
                        {code}
                      </div>
                    ))}
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      onClick={handleCopyMfaRecoveryCodes}
                      className="inline-flex items-center gap-1.5 rounded-full bg-white border border-slate-300 px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition"
                    >
                      <Copy size={14} /> {mfaCopiedCodes ? 'Copied to Clipboard!' : 'Copy All Codes'}
                    </button>
                    <button
                      type="button"
                      onClick={handleDownloadMfaRecoveryCodes}
                      className="inline-flex items-center gap-1.5 rounded-full bg-white border border-slate-300 px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition"
                    >
                      <Download size={14} /> Download .txt
                    </button>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleFinishMandatorySetup}
                  className="mt-6 flex w-full items-center justify-center gap-2 rounded-full bg-[#087c5b] px-5 py-3.5 font-bold text-white transition hover:bg-[#06684d]"
                >
                  <LogIn size={19} /> Continue to Dashboard
                </button>
              </div>
            ) : mfaChallenge?.setupRequired ? (
              /* Case 2: Mandatory Admin 2FA Setup Flow */
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <span className="flex size-11 items-center justify-center rounded-2xl bg-amber-100 text-amber-800">
                    <ShieldCheck size={24} />
                  </span>
                  <div>
                    <h2 className="text-xl font-bold tracking-tight text-[#172033] sm:text-2xl">
                      Two-Factor Setup Required
                    </h2>
                    <p className="text-xs text-slate-500">
                      Mandatory security policy for administrator accounts
                    </p>
                  </div>
                </div>

                {mfaLoading && !mfaSetupData ? (
                  <div className="py-12 text-center text-sm text-slate-500">
                    Initializing secure authenticator setup...
                  </div>
                ) : mfaSetupData ? (
                  <form onSubmit={handleVerifyMfaSetup} className="mt-5 space-y-4">
                    <div className="rounded-2xl border border-emerald-100 bg-emerald-50/40 p-4 text-xs text-slate-700 space-y-3">
                      <p>
                        <strong>1.</strong> Scan this QR code using an authenticator app (e.g. Google Authenticator, Microsoft Authenticator):
                      </p>
                      <div className="flex flex-wrap items-center gap-4">
                        {(() => {
                          const qrSrc = mfaSetupData?.qr_code || mfaSetupData?.qr_code_svg || (typeof mfaSetupData === 'string' ? mfaSetupData : '')
                          return qrSrc ? (
                            <img
                              src={qrSrc}
                              alt="Authenticator Setup QR Code"
                              className="size-36 rounded-xl border border-slate-200 bg-white p-2 shadow-2xs"
                            />
                          ) : (
                            <div className="flex size-36 items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white text-xs text-slate-400">
                              Loading QR code...
                            </div>
                          )
                        })()}
                        <div className="text-xs">
                          <p className="text-slate-500 mb-1">Manual entry key:</p>
                          <code className="rounded-lg bg-white border border-slate-300 px-2.5 py-1.5 font-mono text-xs font-semibold text-slate-800 tracking-wider">
                            {mfaSetupData.secret}
                          </code>
                        </div>
                      </div>
                      <p>
                        <strong>2.</strong> Enter the 6-digit code shown in your app to activate:
                      </p>
                    </div>

                    <div>
                      <label htmlFor="mfa-setup-code" className="mb-2 block text-sm font-semibold text-slate-800">
                        6-Digit Verification Code
                      </label>
                      <input
                        id="mfa-setup-code"
                        type="text"
                        inputMode="numeric"
                        maxLength={6}
                        autoComplete="one-time-code"
                        placeholder="123456"
                        value={mfaCode}
                        onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, ''))}
                        required
                        autoFocus
                        className="w-full rounded-2xl border border-slate-300 px-4 py-3.5 text-center font-mono text-2xl tracking-widest outline-none transition focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
                      />
                    </div>

                    {mfaError && (
                      <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
                        {mfaError}
                      </p>
                    )}

                    <button
                      type="submit"
                      disabled={mfaLoading || mfaCode.length !== 6}
                      className="flex w-full items-center justify-center gap-2 rounded-full bg-[#087c5b] px-5 py-3.5 font-bold text-white transition hover:bg-[#06684d] disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      <ShieldCheck size={19} />
                      {mfaLoading ? 'Verifying...' : 'Verify & Enable 2FA'}
                    </button>

                    <button
                      type="button"
                      onClick={handleCancelMfaChallenge}
                      className="flex w-full items-center justify-center rounded-full border border-slate-300 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition"
                    >
                      Cancel and Back to Sign In
                    </button>
                  </form>
                ) : null}
              </div>
            ) : mfaChallenge ? (
              /* Case 3: Standard 2FA Verification Challenge */
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <span className="flex size-11 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-800">
                    <ShieldCheck size={24} />
                  </span>
                  <div>
                    <h2 className="text-2xl font-bold tracking-tight text-[#172033]">
                      Two-Factor Verification
                    </h2>
                    <p className="text-sm text-slate-500">
                      {mfaUseRecovery
                        ? 'Enter an 8-character single-use recovery code'
                        : 'Enter the 6-digit code from your authenticator app'}
                    </p>
                  </div>
                </div>

                <form onSubmit={handleVerifyMfaLogin} className="mt-5 space-y-4">
                  <div>
                    <label htmlFor="mfa-login-code" className="mb-2 block text-sm font-semibold text-slate-800">
                      {mfaUseRecovery ? 'Recovery Code' : 'Verification Code'}
                    </label>
                    <input
                      id="mfa-login-code"
                      type="text"
                      autoComplete="one-time-code"
                      placeholder={mfaUseRecovery ? 'XXXX-XXXX' : '123456'}
                      value={mfaCode}
                      onChange={(e) => {
                        const val = e.target.value.trim()
                        setMfaCode(mfaUseRecovery ? val.toUpperCase() : val.replace(/\s+/g, ''))
                      }}
                      maxLength={mfaUseRecovery ? 10 : 6}
                      required
                      autoFocus
                      className="w-full rounded-2xl border border-slate-300 px-4 py-3.5 text-center font-mono text-2xl tracking-widest outline-none transition focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
                    />
                  </div>

                  <div className="flex justify-between items-center text-xs">
                    <button
                      type="button"
                      onClick={() => {
                        setMfaUseRecovery(!mfaUseRecovery)
                        setMfaCode('')
                        setMfaError('')
                      }}
                      className="font-semibold text-emerald-800 hover:text-emerald-950 transition"
                    >
                      {mfaUseRecovery
                        ? '← Use 6-digit authenticator code'
                        : 'Lost authenticator? Use single-use recovery code'}
                    </button>
                  </div>

                  {mfaError && (
                    <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
                      {mfaError}
                    </p>
                  )}

                  <button
                    type="submit"
                    disabled={mfaLoading || !mfaCode.trim()}
                    className="flex w-full items-center justify-center gap-2 rounded-full bg-[#087c5b] px-5 py-3.5 font-bold text-white transition hover:bg-[#06684d] disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <LogIn size={19} />
                    {mfaLoading ? 'Verifying...' : 'Log In'}
                  </button>

                  <button
                    type="button"
                    onClick={handleCancelMfaChallenge}
                    className="flex w-full items-center justify-center rounded-full border border-slate-300 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition"
                  >
                    Back to Sign In
                  </button>
                </form>
              </div>
            ) : (
              /* Case 4: Default Login Form */
              <>
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
              </>
            )}
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
