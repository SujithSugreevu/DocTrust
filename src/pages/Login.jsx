
import { useState } from 'react'
import {
  ShieldCheck,
  LockKeyhole,
  History,
  Folder,
  Eye,
  EyeOff,
  LogIn,
  ArrowRight,
} from 'lucide-react'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [rememberMe, setRememberMe] = useState(false)
  const [message, setMessage] = useState('')

  function handleSubmit(event) {
    event.preventDefault()
    setMessage('Login authentication will be connected later.')
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
              <Folder size={17} /> Document Owner
            </span>
            <span className="flex items-center gap-2 rounded-full bg-white/15 px-4 py-2">
              <Eye size={17} /> Viewer
            </span>
          </div>
        </section>

        <section className="flex items-center justify-center bg-[#eafbf3] px-5 py-10 sm:px-10 lg:px-12">
          <div className="w-full max-w-[580px] rounded-[26px] bg-white p-6 shadow-[0_8px_32px_rgba(20,80,55,0.09)] sm:p-9">
            <h2 className="text-2xl font-bold tracking-tight text-[#172033] sm:text-[30px]">
              Administrator Login
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-slate-500 sm:text-base">
              Sign in to manage users, audit activity and monitor security
            </p>

            <form onSubmit={handleSubmit} className="mt-5 space-y-4">
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
                  onClick={() => setMessage('Password recovery will be implemented in a later step.')}
                  className="flex items-center gap-2 font-semibold text-emerald-800 hover:text-emerald-950"
                >
                  <LockKeyhole size={18} />
                  Forgot password?
                </button>
              </div>

              <button
                type="submit"
                className="flex w-full items-center justify-center gap-2 rounded-full bg-[#087c5b] px-5 py-3.5 font-bold text-white transition hover:bg-[#06684d] focus-visible:outline-offset-4"
              >
                <LogIn size={19} />
                Log In
                <ArrowRight size={16} className="sr-only" />
              </button>

              {message && (
                <p role="status" className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-900">
                  {message}
                </p>
              )}

              <p className="pt-1 text-sm leading-relaxed text-slate-500">
                The server verifies your account and role. Only active Administrator
                accounts can sign in here. Failed attempts are recorded.
              </p>
            </form>
          </div>
        </section>
      </div>
    </main>
  )
}
