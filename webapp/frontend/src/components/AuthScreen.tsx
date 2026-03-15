import React, { useState } from 'react'

interface Props {
  onAuth: (email: string) => void
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    height: '100vh',
    background: '#1a1a2e',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  card: {
    background: '#16213e',
    padding: 40,
    borderRadius: 12,
    width: 360,
    boxShadow: '0 4px 24px rgba(0,0,0,0.3)',
  },
  title: {
    fontSize: 28,
    fontWeight: 700,
    color: '#e94560',
    textAlign: 'center' as const,
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    color: '#999',
    textAlign: 'center' as const,
    marginBottom: 24,
  },
  input: {
    width: '100%',
    padding: '10px 14px',
    marginBottom: 12,
    background: '#0f3460',
    border: '1px solid #333',
    borderRadius: 6,
    color: '#e0e0e0',
    fontSize: 14,
    boxSizing: 'border-box' as const,
  },
  button: {
    width: '100%',
    padding: '10px 0',
    background: '#e94560',
    border: 'none',
    borderRadius: 6,
    color: '#fff',
    fontSize: 15,
    fontWeight: 600,
    cursor: 'pointer',
    marginTop: 4,
  },
  toggle: {
    textAlign: 'center' as const,
    marginTop: 16,
    fontSize: 13,
    color: '#999',
  },
  link: {
    color: '#e94560',
    cursor: 'pointer',
    background: 'none',
    border: 'none',
    fontSize: 13,
  },
  error: {
    color: '#ff6b6b',
    fontSize: 13,
    marginBottom: 12,
    textAlign: 'center' as const,
  },
}

export default function AuthScreen({ onAuth }: Props) {
  const [isLogin, setIsLogin] = useState(true)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    const endpoint = isLogin ? '/api/auth/login' : '/api/auth/register'
    const resp = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })

    const data = await resp.json()
    if (data.ok) {
      onAuth(data.email)
    } else {
      setError(data.error || 'Something went wrong')
    }
  }

  return (
    <div style={styles.container}>
      <form style={styles.card} onSubmit={handleSubmit}>
        <div style={styles.title}>PodcastCut</div>
        <div style={styles.subtitle}>AI Podcast Post-Production</div>

        {error && <div style={styles.error}>{error}</div>}

        <input
          style={styles.input}
          type="email"
          placeholder="Email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          required
        />
        <input
          style={styles.input}
          type="password"
          placeholder="Password"
          value={password}
          onChange={e => setPassword(e.target.value)}
          required
          minLength={6}
        />
        <button style={styles.button} type="submit">
          {isLogin ? 'Login' : 'Register'}
        </button>

        <div style={styles.toggle}>
          {isLogin ? "Don't have an account? " : 'Already have an account? '}
          <button
            type="button"
            style={styles.link}
            onClick={() => { setIsLogin(!isLogin); setError('') }}
          >
            {isLogin ? 'Register' : 'Login'}
          </button>
        </div>
      </form>
    </div>
  )
}
