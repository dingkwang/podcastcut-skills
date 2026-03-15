import React, { useState, useEffect, useRef } from 'react'

interface WorkspaceFile {
  name: string
  size: number
  modified: number
  type: string
}

interface Props {
  sessionId: string
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
  },
  header: {
    padding: '12px 16px',
    borderBottom: '1px solid #333',
    fontSize: 14,
    fontWeight: 600,
    color: '#e94560',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  fileList: {
    flex: 1,
    overflow: 'auto',
    padding: '8px 0',
  },
  fileItem: {
    padding: '8px 16px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    cursor: 'pointer',
    fontSize: 13,
    borderBottom: '1px solid #1a2a4a',
  },
  fileName: {
    flex: 1,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap' as const,
  },
  fileSize: {
    color: '#666',
    fontSize: 12,
    marginLeft: 8,
    flexShrink: 0,
  },
  fileIcon: {
    marginRight: 8,
    fontSize: 16,
  },
  preview: {
    borderTop: '1px solid #333',
    padding: 16,
    maxHeight: 300,
    overflow: 'auto',
  },
  audioPlayer: {
    width: '100%',
    marginTop: 8,
  },
  downloadBtn: {
    padding: '4px 10px',
    background: '#0f3460',
    border: '1px solid #333',
    borderRadius: 4,
    color: '#e0e0e0',
    cursor: 'pointer',
    fontSize: 12,
    flexShrink: 0,
  },
  empty: {
    padding: 24,
    textAlign: 'center' as const,
    color: '#555',
    fontSize: 13,
  },
  refreshBtn: {
    background: 'none',
    border: 'none',
    color: '#999',
    cursor: 'pointer',
    fontSize: 16,
  },
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`
}

function getFileIcon(type: string): string {
  const audioTypes = ['mp3', 'wav', 'm4a', 'ogg', 'flac']
  const jsonTypes = ['json']
  const textTypes = ['txt', 'md']
  if (audioTypes.includes(type)) return '🎵'
  if (jsonTypes.includes(type)) return '📋'
  if (textTypes.includes(type)) return '📄'
  return '📁'
}

export default function WorkspacePanel({ sessionId }: Props) {
  const [files, setFiles] = useState<WorkspaceFile[]>([])
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [previewContent, setPreviewContent] = useState<string | null>(null)
  const intervalRef = useRef<number | null>(null)

  const fetchFiles = () => {
    if (!sessionId) return
    fetch(`/api/workspace/${sessionId}`)
      .then(r => r.json())
      .then(data => {
        if (Array.isArray(data)) setFiles(data)
      })
      .catch(() => {})
  }

  useEffect(() => {
    fetchFiles()
    // Poll for new files every 5 seconds
    intervalRef.current = window.setInterval(fetchFiles, 5000)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [sessionId])

  const handleFileClick = async (file: WorkspaceFile) => {
    setSelectedFile(file.name)
    setPreviewContent(null)

    // For text/JSON files, fetch and preview
    if (['json', 'txt', 'md'].includes(file.type)) {
      const resp = await fetch(`/api/workspace/${sessionId}/${file.name}`)
      const text = await resp.text()
      setPreviewContent(text.slice(0, 5000))
    }
  }

  const handleDownload = (fileName: string) => {
    window.open(`/api/workspace/${sessionId}/${fileName}`, '_blank')
  }

  const isAudio = (type: string) => ['mp3', 'wav', 'm4a', 'ogg', 'flac'].includes(type)

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span>Workspace</span>
        <button style={styles.refreshBtn} onClick={fetchFiles} title="Refresh">
          🔄
        </button>
      </div>

      <div style={styles.fileList}>
        {files.length === 0 ? (
          <div style={styles.empty}>No files yet. Upload an audio file to start.</div>
        ) : (
          files.map(file => (
            <div
              key={file.name}
              style={{
                ...styles.fileItem,
                background: selectedFile === file.name ? '#1a2a4a' : 'transparent',
              }}
              onClick={() => handleFileClick(file)}
            >
              <span style={styles.fileIcon}>{getFileIcon(file.type)}</span>
              <span style={styles.fileName}>{file.name}</span>
              <span style={styles.fileSize}>{formatSize(file.size)}</span>
              <button
                style={styles.downloadBtn}
                onClick={e => { e.stopPropagation(); handleDownload(file.name) }}
              >
                ⬇
              </button>
            </div>
          ))
        )}
      </div>

      {selectedFile && (
        <div style={styles.preview}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, color: '#e94560' }}>
            {selectedFile}
          </div>

          {isAudio(files.find(f => f.name === selectedFile)?.type || '') && (
            <audio
              controls
              style={styles.audioPlayer}
              src={`/api/workspace/${sessionId}/${selectedFile}`}
            />
          )}

          {previewContent && (
            <pre style={{
              fontSize: 12,
              background: '#0a1628',
              padding: 12,
              borderRadius: 6,
              overflow: 'auto',
              maxHeight: 200,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-all',
            }}>
              {previewContent}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}
