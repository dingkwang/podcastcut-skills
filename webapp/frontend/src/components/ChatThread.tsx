import React, { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'

interface Message {
  id: string
  role: 'user' | 'assistant' | 'tool' | 'system'
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
    background: 'transparent',
  },
  messages: {
    flex: 1,
    overflow: 'auto',
    padding: '22px 22px 14px',
  },
  userMsg: {
    background: 'linear-gradient(180deg, #fff0e2, #ffe7d3)',
    border: '1px solid #ffc996',
    padding: '12px 16px',
    borderRadius: '20px 20px 6px 20px',
    marginBottom: 14,
    maxWidth: '80%',
    alignSelf: 'flex-end',
    marginLeft: 'auto',
    fontSize: 14,
    lineHeight: 1.6,
    color: '#3c2d20',
    boxShadow: '0 14px 30px rgba(255,152,87,0.12)',
  },
  assistantMsg: {
    background: '#ffffff',
    border: '1px solid #efe2d2',
    padding: '14px 16px',
    borderRadius: '18px 18px 18px 6px',
    marginBottom: 14,
    maxWidth: '85%',
    fontSize: 14,
    lineHeight: 1.6,
    color: '#2f241a',
    boxShadow: '0 12px 28px rgba(124,92,68,0.06)',
  },
  toolMsg: {
    background: '#fff7ee',
    border: '1px solid #f4dcc0',
    padding: '8px 12px',
    borderRadius: 14,
    marginBottom: 8,
    fontSize: 12,
    color: '#9a6c3b',
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  composer: {
    padding: '16px 20px 18px',
    borderTop: '1px solid #eadfce',
    display: 'flex',
    gap: 8,
    background: 'rgba(255,255,255,0.8)',
  },
  input: {
    flex: 1,
    padding: '14px 16px',
    background: '#fffdfa',
    border: '1px solid #f1d9be',
    borderRadius: 20,
    color: '#3c2d20',
    fontSize: 14,
    outline: 'none',
    boxShadow: 'inset 0 1px 2px rgba(81,55,33,0.03)',
  },
  sendBtn: {
    padding: '12px 18px',
    background: 'linear-gradient(135deg, #ff9a4d, #ffb16a)',
    border: 'none',
    borderRadius: 18,
    color: '#fff',
    fontSize: 13,
    fontWeight: 600,
    cursor: 'pointer',
    boxShadow: '0 10px 24px rgba(255,154,77,0.24)',
  },
  uploadBtn: {
    width: 48,
    height: 48,
    background: '#fff7ee',
    border: '1px solid #f0d6ba',
    borderRadius: 18,
    color: '#c98032',
    cursor: 'pointer',
    fontSize: 18,
  },
  spinner: {
    display: 'inline-block',
    width: 12,
    height: 12,
    border: '2px solid #f5cfaa',
    borderTop: '2px solid #ff9a4d',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
}

export default function ChatThread({ sessionId }: Props) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [skills, setSkills] = useState<string[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const mergeAssistantText = (currentText: string, incomingText: string) => {
    if (!currentText) return incomingText
    if (!incomingText) return currentText

    // claude-agent-sdk 有时会发“当前完整快照”，有时像增量。
    // 这里优先去重，避免把同一段回答反复拼接。
    if (incomingText === currentText) return currentText
    if (incomingText.startsWith(currentText)) return incomingText
    if (currentText.startsWith(incomingText)) return currentText

    const maxOverlap = Math.min(currentText.length, incomingText.length)
    for (let overlap = maxOverlap; overlap > 0; overlap -= 1) {
      if (currentText.endsWith(incomingText.slice(0, overlap))) {
        return currentText + incomingText.slice(overlap)
      }
    }

    return currentText + incomingText
  }

  const dedupeHistory = (history: Array<{ role: 'user' | 'assistant'; content: string }>) => {
    const cleaned: Message[] = []
    for (const [index, item] of history.entries()) {
      const last = cleaned[cleaned.length - 1]
      if (last && last.role === item.role && last.content === item.content) {
        continue
      }
      cleaned.push({
        id: `history-${index}`,
        role: item.role,
        content: item.content,
      })
    }
    return cleaned
  }

  const replaceMessage = (id: string, next: Message) => {
    setMessages(prev => prev.map(msg => (msg.id === id ? next : msg)))
  }

  useEffect(() => {
    setMessages([])
    setSkills([])
    if (!sessionId) return
    fetch(`/api/chat/${sessionId}/history`)
      .then(r => r.json())
      .then((history: Array<{ role: 'user' | 'assistant'; content: string }>) => {
        if (!Array.isArray(history)) return
        setMessages(dedupeHistory(history))
      })
      .catch(() => {})
  }, [sessionId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !sessionId) return

    const optimisticId = `upload-${Date.now()}`
    setMessages(prev => [
      ...prev,
      {
        id: optimisticId,
        role: 'user',
        content: `Uploading file: ${file.name} (${(file.size / 1024).toFixed(1)}KB)`,
      },
    ])

    const formData = new FormData()
    formData.append('file', file)

    try {
      const resp = await fetch(`/api/upload?session_id=${sessionId}`, {
        method: 'POST',
        body: formData,
      })
      const data = await resp.json()
      if (!resp.ok || !data.ok) {
        throw new Error(data.error || 'Upload failed')
      }

      replaceMessage(optimisticId, {
        id: optimisticId,
        role: 'user',
        content: `Uploaded file: ${data.file_name} (${(data.size / 1024).toFixed(1)}KB)`,
      })
    } catch (error) {
      replaceMessage(optimisticId, {
        id: optimisticId,
        role: 'user',
        content: `Upload failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
      })
    }

    e.target.value = ''
  }

  const sendMessage = async () => {
    if (!input.trim() || !sessionId || streaming) return

    const msg = input.trim()
    setInput('')
    setMessages(prev => [...prev, { id: `user-${Date.now()}`, role: 'user', content: msg }])
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
      const assistantMessageId = `assistant-${Date.now()}`

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        let currentEvent = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim()
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

          if (currentEvent === 'skills_loaded') {
            const loadedSkills = data.skills || []
            setSkills(loadedSkills)
          } else if (data.content !== undefined) {
            // Text event: 优先按“最新完整文本快照”合并，兼容少量纯增量事件
            currentAssistant = mergeAssistantText(currentAssistant, data.content)
            setMessages(prev => {
              const updated = [...prev]
              const lastIdx = updated.length - 1
              if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
                updated[lastIdx] = { ...updated[lastIdx], role: 'assistant', content: currentAssistant }
              } else {
                updated.push({ id: assistantMessageId, role: 'assistant', content: currentAssistant })
              }
              return updated
            })
          } else if (data.description !== undefined) {
            // Tool start event
            setMessages(prev => [...prev, { id: `tool-${Date.now()}`, role: 'tool', content: data.description }])
          } else if (data.message !== undefined) {
            // Error event
            setMessages(prev => [...prev, { id: `error-${Date.now()}`, role: 'assistant', content: `Error: ${data.message}` }])
          }
          currentEvent = ''
        }
      }
    } catch (err) {
      setMessages(prev => [...prev, { id: `conn-${Date.now()}`, role: 'assistant', content: `Connection error: ${err}` }])
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
        {skills.length > 0 && (
          <div style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 6,
            padding: '8px 12px',
            marginBottom: 12,
            background: '#fff8f0',
            borderRadius: 14,
            alignItems: 'center',
            border: '1px solid #f1dfc7',
          }}>
            <span style={{ fontSize: 11, color: '#96704a', marginRight: 4 }}>Skills:</span>
            {skills.map((skill, i) => (
              <span key={i} style={{
                fontSize: 11,
                padding: '2px 8px',
                background: '#fff',
                borderRadius: 10,
                color: '#9a6c3b',
                border: '1px solid #f1dfc7',
              }}>{skill}</span>
            ))}
          </div>
        )}

        {messages.length === 0 && (
          <div style={{ textAlign: 'center', color: '#8b6f5a', marginTop: 72, padding: '0 24px' }}>
            <div style={{ fontSize: 32, marginBottom: 14 }}>🎙️</div>
            <div style={{ fontSize: 15, fontWeight: 600, color: '#3b2d1f' }}>上传音频并开始对话</div>
            <div style={{ fontSize: 12, marginTop: 10, color: '#8b6f5a', lineHeight: 1.7 }}>
              这版先对齐 PodcastCut 的聊天体验。
              <br />
              后续 Claude 会在当前 workspace 中产出固定的 <code>review_data.json</code>。
            </div>
          </div>
        )}

        {messages.map((msg, i) => {
          if (msg.role === 'tool') {
            return (
              <div key={msg.id || String(i)} style={styles.toolMsg}>
                <div style={styles.spinner} />
                {msg.content}
              </div>
            )
          }
          if (msg.role === 'user') {
            return <div key={msg.id || String(i)} style={styles.userMsg}>{msg.content}</div>
          }
          return (
            <div key={msg.id || String(i)} style={styles.assistantMsg}>
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
          ⤴
        </button>
        <input
          style={styles.input}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入消息，或先上传音频..."
          disabled={streaming}
        />
        <button
          style={{ ...styles.sendBtn, opacity: streaming ? 0.5 : 1 }}
          onClick={sendMessage}
          disabled={streaming}
        >
          发送
        </button>
      </div>
    </div>
  )
}
