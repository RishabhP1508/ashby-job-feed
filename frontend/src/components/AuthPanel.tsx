import { useState } from 'react'
import type { User } from '../types'
import { login, register } from '../api'

interface Props {
  onAuth: (user: User) => void
}

export function AuthPanel({ onAuth }: Props) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async () => {
    setError('')
    setBusy(true)
    try {
      const user = mode === 'login' ? await login(email, password) : await register(email, password)
      onAuth(user)
    } catch (e) {
      setError(String((e as Error).message))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form
      className="auth"
      onSubmit={(event) => {
        event.preventDefault()
        submit()
      }}
    >
      <div className="auth-head">
        <div>
          <span className="auth-kicker">Private workspace</span>
          <h2 id="auth-title">{mode === 'login' ? 'Welcome back' : 'Create your account'}</h2>
        </div>
        <button
          type="button"
          className="link-btn"
          onClick={() => {
            setMode(mode === 'login' ? 'register' : 'login')
            setError('')
          }}
        >
          {mode === 'login' ? 'Register' : 'Log in'}
        </button>
      </div>
      <p className="auth-copy">
        {mode === 'login'
          ? 'Access saved searches, seen roles, and application tracking.'
          : 'Save searches and keep your job pipeline in one place.'}
      </p>
      <div className="auth-row">
        <label htmlFor="auth-email">Email</label>
        <input
          id="auth-email"
          className="auth-input"
          type="email"
          placeholder="you@example.com"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <label htmlFor="auth-password">Password</label>
        <input
          id="auth-password"
          className="auth-input"
          type="password"
          placeholder="8+ characters"
          autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        <button type="submit" className="btn btn-primary" disabled={busy}>
          {busy ? 'Working…' : mode === 'login' ? 'Log in' : 'Create account'}
        </button>
      </div>
      {error && (
        <div className="auth-error" role="alert">
          {error}
        </div>
      )}
    </form>
  )
}
