import { useState } from 'react'
import { login, register } from './api'

export default function AuthForm({ onAuthenticated }) {
  const [mode, setMode] = useState('login') // 'login' | 'register'
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const fn = mode === 'login' ? login : register
      const { access_token } = await fn(username, password)
      onAuthenticated(access_token, username)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card" style={{ maxWidth: 380, margin: '80px auto' }}>
      <h2>{mode === 'login' ? 'Log in' : 'Create account'}</h2>
      {error && <div className="error-box">{error}</div>}
      <form onSubmit={handleSubmit}>
        <label>Username</label>
        <input value={username} onChange={(e) => setUsername(e.target.value)} required />

        <label>Password</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={mode === 'register' ? 8 : undefined}
        />

        <button type="submit" disabled={loading} style={{ width: '100%' }}>
          {loading ? 'Please wait…' : mode === 'login' ? 'Log in' : 'Sign up'}
        </button>
      </form>

      <div className="auth-toggle">
        {mode === 'login' ? (
          <>
            No account?{' '}
            <a onClick={() => { setMode('register'); setError('') }}>Sign up</a>
          </>
        ) : (
          <>
            Already have an account?{' '}
            <a onClick={() => { setMode('login'); setError('') }}>Log in</a>
          </>
        )}
      </div>

      <div className="auth-toggle" style={{ marginTop: 20 }}>
        Demo credentials: <b>demo</b> / <b>demopassword</b>
      </div>
    </div>
  )
}
