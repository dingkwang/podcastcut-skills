import React, { useCallback, useEffect, useState } from 'react'
import AuthScreen from './components/AuthScreen'
import ChatThread from './components/ChatThread'
import SessionSidebar from './components/SessionSidebar'
import ReviewCanvasMVP from './components/ReviewCanvasMVP'

interface UserInfo {
  logged_in: boolean
  email?: string
}

interface ChatSessionItem {
  session_id: string
  message_count: number
  preview: string
}

const styles: Record<string, React.CSSProperties> = {
  appShell: {
    display: 'flex',
    height: '100vh',
    background: 'linear-gradient(180deg, #f8f4ee 0%, #f4efe6 100%)',
    color: '#1f2937',
    fontFamily: '"SF Pro Display", "Segoe UI", sans-serif',
  },
  chatColumn: {
    width: 430,
    minWidth: 360,
    borderRight: '1px solid #eadfce',
    background: 'rgba(255,255,255,0.82)',
    display: 'flex',
    flexDirection: 'column',
    backdropFilter: 'blur(18px)',
  },
  chatHeader: {
    padding: '22px 26px 18px',
    borderBottom: '1px solid #f0e5d6',
    background: 'rgba(255,255,255,0.76)',
  },
  workflowPanel: {
    margin: '18px 22px 0',
    padding: '14px 16px 12px',
    borderRadius: 18,
    border: '1px solid #f1dfcb',
    background: 'linear-gradient(180deg, #fff9f3, #fffefb)',
    boxShadow: '0 10px 22px rgba(124,92,68,0.06)',
  },
  workflowTitle: {
    fontSize: 12,
    fontWeight: 700,
    color: '#7c5c44',
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
  },
  workflowHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
    marginBottom: 10,
  },
  workflowIntro: {
    fontSize: 12,
    color: '#8b6f5a',
    lineHeight: 1.6,
    marginBottom: 10,
  },
  workflowToggle: {
    border: '1px solid #efd9bf',
    background: '#fffdf9',
    color: '#9a6c3b',
    borderRadius: 999,
    padding: '6px 10px',
    fontSize: 11,
    fontWeight: 700,
    cursor: 'pointer',
  },
  workflowList: {
    margin: 0,
    paddingLeft: 18,
    color: '#3c2d20',
    fontSize: 12,
    lineHeight: 1.75,
  },
  brandRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 14,
  },
  brandIcon: {
    width: 42,
    height: 42,
    borderRadius: 14,
    background: 'linear-gradient(135deg, #ff7a18, #ff9f43)',
    color: '#fff',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 18,
    boxShadow: '0 10px 25px rgba(255,122,24,0.22)',
  },
  brandTitle: {
    fontSize: 21,
    fontWeight: 700,
    letterSpacing: '-0.02em',
  },
  brandSubtitle: {
    fontSize: 12,
    color: '#8b6f5a',
    marginTop: 3,
  },
  reviewColumn: {
    flex: 1,
    minWidth: 0,
    display: 'flex',
    flexDirection: 'column',
    background:
      'radial-gradient(circle at top right, rgba(255,170,120,0.18), transparent 32%), linear-gradient(180deg, #fffdf9 0%, #faf5ed 100%)',
  },
}

export default function App() {
  const [user, setUser] = useState<UserInfo | null>(null)
  const [sessionId, setSessionId] = useState('')
  const [sessions, setSessions] = useState<ChatSessionItem[]>([])
  const [loading, setLoading] = useState(true)
  const [workflowOpen, setWorkflowOpen] = useState(true)

  const loadSessions = useCallback(() => {
    fetch('/api/chat/sessions')
      .then(r => r.json())
      .then((items: ChatSessionItem[]) => {
        setSessions(items)
        if (!sessionId && items.length > 0) {
          setSessionId(items[0].session_id)
        }
      })
      .catch(() => {})
  }, [sessionId])

  useEffect(() => {
    fetch('/api/auth/me')
      .then(r => r.json())
      .then(data => {
        setUser(data)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  const createNewChat = useCallback(() => {
    fetch('/api/chat/new', { method: 'POST' })
      .then(r => r.json())
      .then(data => {
        setSessionId(data.session_id)
        loadSessions()
      })
  }, [loadSessions])

  const handleAuth = (email: string) => {
    setUser({ logged_in: true, email })
    createNewChat()
  }

  useEffect(() => {
    if (!user?.logged_in) return
    loadSessions()
    const timer = window.setInterval(loadSessions, 5000)
    return () => window.clearInterval(timer)
  }, [user, loadSessions])

  if (loading) return null
  if (!user?.logged_in) return <AuthScreen onAuth={handleAuth} />

  return (
    <div style={styles.appShell}>
      <SessionSidebar
        sessions={sessions}
        activeSessionId={sessionId}
        userEmail={user.email || ''}
        onSelect={setSessionId}
        onNewChat={createNewChat}
      />

      <div style={styles.chatColumn}>
        <div style={styles.chatHeader}>
          <div style={styles.brandRow}>
            <div style={styles.brandIcon}>🎙</div>
            <div>
              <div style={styles.brandTitle}>PodcastCut</div>
              <div style={styles.brandSubtitle}>AI 播客剪辑助手</div>
            </div>
          </div>
        </div>
        <ChatThread sessionId={sessionId} />
      </div>

      <div style={styles.reviewColumn}>
        <div style={styles.workflowPanel}>
          <div style={styles.workflowHeader}>
            <div style={styles.workflowTitle}>正常工作流</div>
            <button style={styles.workflowToggle} onClick={() => setWorkflowOpen(open => !open)}>
              {workflowOpen ? '隐藏' : '展开'}
            </button>
          </div>
          {workflowOpen && (
            <>
              <div style={styles.workflowIntro}>
                推荐按这条顺序走，这样 Claude、审查稿和剪辑成品会更稳定对齐。
              </div>
              <ol style={styles.workflowList}>
                <li>新建会话并上传播客音频。</li>
                <li>告诉 Claude 你要“分析并生成审查稿”。</li>
                <li>等待它在当前工作区写出 <code>review_data.json</code>。</li>
                <li>点“刷新审查稿”，确认句子、删除块和精剪项都显示出来。</li>
                <li>在画布里手动标记删除或启用精剪，再点“确认剪辑”。</li>
              </ol>
            </>
          )}
        </div>
        <ReviewCanvasMVP sessionId={sessionId} />
      </div>
    </div>
  )
}
