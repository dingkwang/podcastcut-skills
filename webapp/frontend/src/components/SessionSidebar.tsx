import React from 'react'

interface ChatSessionItem {
  session_id: string
  message_count: number
  preview: string
}

interface Props {
  sessions: ChatSessionItem[]
  activeSessionId: string
  userEmail: string
  onSelect: (sessionId: string) => void
  onNewChat: () => void
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    width: 248,
    background: '#111827',
    color: '#f9fafb',
    display: 'flex',
    flexDirection: 'column',
    borderRight: '1px solid rgba(255,255,255,0.06)',
  },
  header: {
    padding: '22px 18px 14px',
    borderBottom: '1px solid rgba(255,255,255,0.07)',
  },
  eyebrow: {
    fontSize: 10,
    letterSpacing: '0.14em',
    textTransform: 'uppercase',
    color: '#9ca3af',
    marginBottom: 10,
  },
  userEmail: {
    fontSize: 12,
    color: '#d1d5db',
    marginBottom: 14,
    wordBreak: 'break-all',
  },
  button: {
    width: '100%',
    border: 'none',
    borderRadius: 14,
    padding: '11px 14px',
    background: 'linear-gradient(135deg, #ff7a18, #ff9f43)',
    color: '#fff',
    fontSize: 13,
    fontWeight: 700,
    cursor: 'pointer',
  },
  list: {
    flex: 1,
    overflowY: 'auto',
    padding: '12px 10px 16px',
  },
  item: {
    borderRadius: 16,
    padding: '12px 12px 11px',
    marginBottom: 8,
    cursor: 'pointer',
    border: '1px solid transparent',
  },
  activeItem: {
    background: 'rgba(255,255,255,0.07)',
    borderColor: 'rgba(255,255,255,0.10)',
  },
  itemTitle: {
    fontSize: 12,
    fontWeight: 600,
    color: '#f3f4f6',
    marginBottom: 5,
  },
  itemPreview: {
    fontSize: 11,
    lineHeight: 1.45,
    color: '#9ca3af',
  },
  itemMeta: {
    fontSize: 10,
    color: '#6b7280',
    marginTop: 6,
  },
  empty: {
    padding: '22px 14px',
    color: '#9ca3af',
    fontSize: 12,
    lineHeight: 1.6,
  },
}

function labelForSession(item: ChatSessionItem, index: number) {
  if (item.preview?.trim()) return item.preview.slice(0, 24)
  return `新会话 ${index + 1}`
}

export default function SessionSidebar({
  sessions,
  activeSessionId,
  userEmail,
  onSelect,
  onNewChat,
}: Props) {
  return (
    <aside style={styles.container}>
      <div style={styles.header}>
        <div style={styles.eyebrow}>Projects</div>
        <div style={styles.userEmail}>{userEmail}</div>
        <button style={styles.button} onClick={onNewChat}>
          新建会话
        </button>
      </div>

      <div style={styles.list}>
        {sessions.length === 0 ? (
          <div style={styles.empty}>
            还没有会话。
            <br />
            先创建一个新会话，然后上传播客音频开始体验。
          </div>
        ) : (
          sessions.map((item, index) => (
            <div
              key={item.session_id}
              style={{
                ...styles.item,
                ...(item.session_id === activeSessionId ? styles.activeItem : {}),
              }}
              onClick={() => onSelect(item.session_id)}
            >
              <div style={styles.itemTitle}>{labelForSession(item, index)}</div>
              <div style={styles.itemPreview}>
                {item.preview || '上传音频后，Claude 会在这里引导你完成播客处理。'}
              </div>
              <div style={styles.itemMeta}>{item.message_count} 条消息</div>
            </div>
          ))
        )}
      </div>
    </aside>
  )
}
