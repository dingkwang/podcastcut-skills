import React, { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'

interface Message {
  role: 'user' | 'assistant' | 'tool'
  content: string
}

interface Props {
  sessionId: string
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    minHeight: 0,
  },
  messages: {
    flex: 1,
    overflow: 'auto',
    padding: '16px 20px',
  },
  userMsg: {
    background: '#0f3460',
    padding: '10px 14px',
    borderRadius: '12px 12px 4px 12px',
    marginBottom: 12,
    maxWidth: '80%',
    alignSelf: 'flex-end',
    marginLeft: 'auto',
    fontSize: 14,
    lineHeight: 1.5,
  },
  assistantMsg: {
    background: '#1e2a47',
    padding: '10px 14px',
    borderRadius: '12px 12px 12px 4px',
    marginBottom: 12,
    maxWidth: '85%',
    fontSize: 14,
    lineHeight: 1.6,
  },
  toolMsg: {
    background: '#1a2940',
    border: '1px solid #2a3a5a',
    padding: '6px 12px',
    borderRadius: 8,
    marginBottom: 8,
    fontSize: 13,
    color: '#8899bb',
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  composer: {
    padding: '12px 20px',
    borderTop: '1px solid #333',
    display: 'flex',
    gap: 8,
    background: '#16213e',
  },
  input: {
    flex: 1,
    padding: '10px 14px',
    background: '#0f3460',
    border: '1px solid #333',
    borderRadius: 8,
    color: '#e0e0e0',
    fontSize: 14,
    outline: 'none',
  },
  sendBtn: {
    padding: '10px 20px',
    background: '#e94560',
    border: 'none',
    borderRadius: 8,
    color: '#fff',
    fontSize: 14,
    fontWeight: 600,
    cursor: 'pointer',
  },
  uploadBtn: {
    padding: '10px 14px',
    background: '#0a2647',
    border: '1px solid #333',
    borderRadius: 8,
    color: '#999',
    cursor: 'pointer',
    fontSize: 14,
  },
  spinner: {
    display: 'inline-block',
    width: 12,
    height: 12,
    border: '2px solid #555',
    borderTop: '2px solid #e94560',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
}

export default function ChatThread({ sessionId }: Props) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    setMessages([])
  }, [sessionId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !sessionId) return

    const formData = new FormData()
    formData.append('file', file)

    const resp = await fetch(`/api/upload?session_id=${sessionId}`, {
      method: 'POST',
      body: formData,
    })
    const data = await resp.json()
    if (data.ok) {
      setMessages(prev => [
        ...prev,
        { role: 'user', content: `Uploaded file: ${data.file_name} (${(data.size / 1024).toFixed(1)}KB)` },
      ])
    }
    e.target.value = ''
  }

  const sendMessage = async () => {
    if (!input.trim() || !sessionId || streaming) return

    const msg = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: msg }])
    setStreaming(true)

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: msg }),
      })

      const reader = response.body?.getReader()
      if (!reader) return

      const decoder = new TextDecoder()
      let buffer = ''
      let currentAssistant = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            const eventType = line.slice(7).trim()
            continue
          }
          if (!line.startsWith('data: ')) continue

          const jsonStr = line.slice(6)
          let data: any
          try {
            data = JSON.parse(jsonStr)
          } catch {
            continue
          }

          // Detect event type from the data structure
          if (data.content !== undefined) {
            // Text event
            currentAssistant += data.content
            setMessages(prev => {
              const updated = [...prev]
              const lastIdx = updated.length - 1
              if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
                updated[lastIdx] = { role: 'assistant', content: currentAssistant }
              } else {
                updated.push({ role: 'assistant', content: currentAssistant })
              }
              return updated
            })
          } else if (data.description !== undefined) {
            // Tool start event
            setMessages(prev => [...prev, { role: 'tool', content: data.description }])
          } else if (data.message !== undefined) {
            // Error event
            setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${data.message}` }])
          }
        }
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Connection error: ${err}` }])
    } finally {
      setStreaming(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div style={styles.container}>
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>

      <div style={styles.messages}>
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', color: '#666', marginTop: 60 }}>
            <div style={{ fontSize: 36, marginBottom: 12 }}>🎙️</div>
            <div style={{ fontSize: 16 }}>Upload an audio file and start chatting</div>
            <div style={{ fontSize: 13, marginTop: 8, color: '#555' }}>
              I can transcribe, correct, clone voices, and produce podcast audio
            </div>
          </div>
        )}

        {messages.map((msg, i) => {
          if (msg.role === 'tool') {
            return (
              <div key={i} style={styles.toolMsg}>
                <div style={styles.spinner} />
                {msg.content}
              </div>
            )
          }
          if (msg.role === 'user') {
            return <div key={i} style={styles.userMsg}>{msg.content}</div>
          }
          return (
            <div key={i} style={styles.assistantMsg}>
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            </div>
          )
        })}

        {streaming && (
          <div style={styles.toolMsg}>
            <div style={styles.spinner} />
            Thinking...
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div style={styles.composer}>
        <input
          type="file"
          ref={fileInputRef}
          style={{ display: 'none' }}
          accept="audio/*"
          onChange={handleUpload}
        />
        <button style={styles.uploadBtn} onClick={() => fileInputRef.current?.click()}>
          📎
        </button>
        <input
          style={styles.input}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message... (upload audio first)"
          disabled={streaming}
        />
        <button
          style={{ ...styles.sendBtn, opacity: streaming ? 0.5 : 1 }}
          onClick={sendMessage}
          disabled={streaming}
        >
          Send
        </button>
      </div>
    </div>
  )
}
