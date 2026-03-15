import React, { useState, useEffect } from 'react'
import AuthScreen from './components/AuthScreen'
import ChatThread from './components/ChatThread'
import WorkspacePanel from './components/WorkspacePanel'

interface UserInfo {
  logged_in: boolean
  email?: string
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    height: '100vh',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    background: '#1a1a2e',
    color: '#e0e0e0',
  },
  chatPane: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    borderRight: '1px solid #333',
    minWidth: 0,
  },
  workspacePane: {
    width: 360,
    display: 'flex',
    flexDirection: 'column',
    background: '#16213e',
  },
  header: {
    padding: '12px 20px',
    background: '#0f3460',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    fontSize: 14,
  },
  title: {
    fontSize: 18,
    fontWeight: 700,
    color: '#e94560',
  },
  email: {
    fontSize: 13,
    color: '#999',
  },
}

export default function App() {
  const [user, setUser] = useState<UserInfo | null>(null)
  const [sessionId, setSessionId] = useState<string>('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/auth/me')
      .then(r => r.json())
      .then(data => {
        setUser(data)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  const handleAuth = (email: string) => {
    setUser({ logged_in: true, email })
    // Create a new chat session
    fetch('/api/chat/new', { method: 'POST' })
      .then(r => r.json())
      .then(data => setSessionId(data.session_id))
  }

  const handleNewChat = () => {
    fetch('/api/chat/new', { method: 'POST' })
      .then(r => r.json())
      .then(data => setSessionId(data.session_id))
  }

  useEffect(() => {
    if (user?.logged_in && !sessionId) {
      handleNewChat()
    }
  }, [user])

  if (loading) return null
  if (!user?.logged_in) return <AuthScreen onAuth={handleAuth} />

  return (
    <div style={styles.container}>
      <div style={styles.chatPane}>
        <div style={styles.header}>
          <span style={styles.title}>PodcastCut</span>
          <div>
            <span style={styles.email}>{user.email}</span>
            <button
              onClick={handleNewChat}
              style={{
                marginLeft: 12,
                padding: '4px 12px',
                background: '#e94560',
                border: 'none',
                borderRadius: 4,
                color: '#fff',
                cursor: 'pointer',
                fontSize: 13,
              }}
            >
              New Chat
            </button>
          </div>
        </div>
        <ChatThread sessionId={sessionId} />
      </div>
      <div style={styles.workspacePane}>
        <WorkspacePanel sessionId={sessionId} />
      </div>
    </div>
  )
}
