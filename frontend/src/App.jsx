import { useState, useEffect } from 'react'
import AuthForm from './AuthForm'
import PlanForm from './PlanForm'
import Results from './Results'
import { optimizeAllocation } from './api'

const TOKEN_KEY = 'finguard_token'
const USERNAME_KEY = 'finguard_username'

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY))
  const [username, setUsername] = useState(() => localStorage.getItem(USERNAME_KEY))
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  }, [token])

  useEffect(() => {
    if (username) localStorage.setItem(USERNAME_KEY, username)
    else localStorage.removeItem(USERNAME_KEY)
  }, [username])

  function handleAuthenticated(newToken, newUsername) {
    setToken(newToken)
    setUsername(newUsername)
  }

  function handleLogout() {
    setToken(null)
    setUsername(null)
    setResult(null)
  }

  async function handleSubmit(payload) {
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const data = await optimizeAllocation(token, payload)
      setResult(data)
    } catch (err) {
      if (err.message.includes('401')) {
        handleLogout()
        setError('Your session expired. Please log in again.')
      } else {
        setError(err.message)
      }
    } finally {
      setLoading(false)
    }
  }

  if (!token) {
    return (
      <div className="app-shell">
        <AuthForm onAuthenticated={handleAuthenticated} />
      </div>
    )
  }

  return (
    <div className="app-shell">
      <div className="app-header">
        <div>
          <h1 className="app-title">FinGuard</h1>
          <div className="app-subtitle">Algorithmic debt &amp; savings optimizer</div>
        </div>
        <div className="top-bar" style={{ marginBottom: 0 }}>
          <span style={{ alignSelf: 'center', color: 'var(--text-dim)', fontSize: 13 }}>
            Signed in as <b>{username}</b>
          </span>
          <button className="secondary" onClick={handleLogout}>
            Log out
          </button>
        </div>
      </div>

      <PlanForm onSubmit={handleSubmit} loading={loading} />

      {error && <div className="error-box">{error}</div>}

      <Results result={result} />
    </div>
  )
}
