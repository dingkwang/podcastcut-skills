import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  type ReviewDataPayload,
  type ReviewSentence,
  type ReviewBlock,
  type ReviewFineEdit,
} from '../mockReviewData'

interface Props {
  sessionId: string
}

const speakerColors: Record<string, string> = {
  麦雅: '#2563eb',
  响歌歌: '#16a34a',
  安安: '#ea580c',
  dingkang: '#2563eb',
  interviewer: '#ea580c',
}

const styles: Record<string, React.CSSProperties> = {
  shell: {
    flex: 1,
    minHeight: 0,
    display: 'flex',
    flexDirection: 'column',
  },
  header: {
    padding: '18px 24px',
    borderBottom: '1px solid #efe2d2',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 16,
    background: 'rgba(255,255,255,0.72)',
  },
  title: {
    fontSize: 18,
    fontWeight: 700,
    color: '#2f241a',
  },
  subtitle: {
    fontSize: 13,
    color: '#8b6f5a',
    marginTop: 4,
  },
  badge: {
    padding: '7px 12px',
    borderRadius: 999,
    fontSize: 12,
    fontWeight: 700,
    background: '#fff1e6',
    color: '#c46b17',
    border: '1px solid #ffd7b5',
  },
  refreshBtn: {
    border: '1px solid #f1d9be',
    borderRadius: 12,
    padding: '10px 12px',
    fontSize: 13,
    fontWeight: 700,
    cursor: 'pointer',
    background: '#fffaf4',
    color: '#9a5c10',
  },
  body: {
    flex: 1,
    minHeight: 0,
    display: 'grid',
    gridTemplateColumns: '280px 1fr',
  },
  side: {
    borderRight: '1px solid #f0e3d4',
    padding: 20,
    overflowY: 'auto',
    background: 'rgba(255,255,255,0.56)',
  },
  main: {
    minHeight: 0,
    overflowY: 'auto',
    padding: '20px 24px 28px',
  },
  panel: {
    borderRadius: 20,
    border: '1px solid #efdfcc',
    background: 'rgba(255,255,255,0.76)',
    padding: 16,
    marginBottom: 16,
    boxShadow: '0 12px 30px rgba(131,94,59,0.06)',
  },
  panelTitle: {
    fontSize: 13,
    fontWeight: 700,
    color: '#7c5c44',
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
    marginBottom: 12,
  },
  audioCard: {
    borderRadius: 18,
    padding: 18,
    background: 'linear-gradient(135deg, #fff7f0, #fff)',
    border: '1px solid #f5dfc9',
  },
  audioMeta: {
    fontSize: 13,
    color: '#7c5c44',
    marginBottom: 10,
  },
  sentenceCard: {
    borderRadius: 18,
    border: '1px solid #ecdcc8',
    background: 'rgba(255,255,255,0.82)',
    padding: 16,
    marginBottom: 14,
  },
  sentenceDeletedCard: {
    background: '#fff4ea',
    borderColor: '#f3c997',
  },
  sentenceMeta: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    marginBottom: 10,
  },
  controlRow: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 8,
    marginTop: 12,
  },
  controlBtn: {
    border: '1px solid #efd5b6',
    borderRadius: 999,
    padding: '7px 10px',
    fontSize: 12,
    fontWeight: 700,
    cursor: 'pointer',
    background: '#fffaf4',
    color: '#8b6f5a',
  },
  activeControlBtn: {
    background: '#ea580c',
    borderColor: '#ea580c',
    color: '#fff',
  },
  speakerChip: {
    fontSize: 12,
    fontWeight: 700,
    padding: '4px 10px',
    borderRadius: 999,
    color: '#fff',
  },
  timeChip: {
    fontSize: 12,
    color: '#8b6f5a',
    background: '#f8efe4',
    padding: '4px 9px',
    borderRadius: 999,
  },
  deleteChip: {
    fontSize: 11,
    color: '#b45309',
    background: '#fff0d8',
    padding: '4px 8px',
    borderRadius: 999,
    fontWeight: 700,
  },
  sentenceText: {
    fontSize: 16,
    lineHeight: 1.7,
    color: '#2f241a',
  },
  fineEditBox: {
    marginTop: 12,
    padding: '10px 12px',
    borderRadius: 14,
    background: '#fff6ea',
    color: '#9a5c10',
    fontSize: 13,
    border: '1px solid #ffe2bc',
  },
  empty: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    color: '#8b6f5a',
    fontSize: 15,
    textAlign: 'center',
    padding: 40,
  },
}

function formatDuration(seconds: number) {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

function normalizeReviewData(raw: any): ReviewDataPayload {
  if (!raw) return emptyReviewData
  return {
    audio_url: raw.audio_url || raw.audioUrl || '',
    audio_duration: Number(raw.audio_duration || raw.audioDuration || 0),
    sentences: Array.isArray(raw.sentences) ? raw.sentences : [],
    blocks: Array.isArray(raw.blocks) ? raw.blocks : [],
    fineEdits: Array.isArray(raw.fineEdits)
      ? raw.fineEdits
      : Array.isArray(raw.fine_edits)
        ? raw.fine_edits
        : [],
  }
}

const emptyReviewData: ReviewDataPayload = {
  audio_url: '',
  audio_duration: 0,
  sentences: [],
  blocks: [],
  fineEdits: [],
}

export default function ReviewCanvasMVP({ sessionId }: Props) {
  const [reviewData, setReviewData] = useState<ReviewDataPayload>(emptyReviewData)
  const [sourceLabel, setSourceLabel] = useState('等待审查稿')
  const [cutAudioUrl, setCutAudioUrl] = useState('')
  const [cutSummary, setCutSummary] = useState('')
  const [cutError, setCutError] = useState('')
  const [isCutting, setIsCutting] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)

  const loadReviewData = useCallback(
    async (resetWhenMissing = false) => {
      if (!sessionId) return false

      try {
        const response = await fetch(`/api/workspace/${sessionId}/review_data.json`)
        if (!response.ok) {
          throw new Error('missing review_data.json')
        }

        const data = normalizeReviewData(JSON.parse(await response.text()))
        const blocks = data.blocks.map(block => ({ ...block, enabled: block.enabled !== false }))
        const enabledBlockIds = new Set(blocks.filter(block => block.enabled !== false).map(block => block.id))
        const sentences = data.sentences.map(sentence => ({
          ...sentence,
          isAiDeleted: sentence.blockId != null
            ? enabledBlockIds.has(sentence.blockId) || sentence.isAiDeleted
            : sentence.isAiDeleted,
        }))
        const fineEdits = data.fineEdits.map(edit => ({ ...edit, enabled: edit.enabled !== false }))
        setReviewData({
          ...data,
          sentences,
          blocks,
          fineEdits,
        })
        setSourceLabel('当前会话审查稿')
        return true
      } catch {
        if (resetWhenMissing) {
          setReviewData(emptyReviewData)
          setSourceLabel('等待审查稿')
        }
        return false
      }
    },
    [sessionId],
  )

  useEffect(() => {
    if (!sessionId) return
    setCutAudioUrl('')
    setCutSummary('')
    setCutError('')

    let cancelled = false
    let pollTimer: number | undefined

    const startPolling = async () => {
      const found = await loadReviewData(true)
      if (cancelled || found) return

      pollTimer = window.setInterval(async () => {
        const hasReview = await loadReviewData(false)
        if (hasReview && pollTimer) {
          window.clearInterval(pollTimer)
        }
      }, 3000)
    }

    startPolling()

    return () => {
      cancelled = true
      if (pollTimer) {
        window.clearInterval(pollTimer)
      }
    }
  }, [sessionId, loadReviewData])

  async function handleRefreshReview() {
    if (!sessionId || isRefreshing) return
    setIsRefreshing(true)
    try {
      await loadReviewData(true)
    } finally {
      setIsRefreshing(false)
    }
  }

  const fineBySentence = useMemo(() => {
    const map = new Map<number, ReviewFineEdit[]>()
    for (const edit of reviewData.fineEdits || []) {
      const group = map.get(edit.sentenceIdx) || []
      group.push(edit)
      map.set(edit.sentenceIdx, group)
    }
    return map
  }, [reviewData.fineEdits])

  const blockSummaries = useMemo(() => reviewData.blocks || [], [reviewData.blocks])
  const canCut =
    sourceLabel === '当前会话审查稿' &&
    (reviewData.sentences.some(sentence => sentence.isAiDeleted) ||
      reviewData.fineEdits.some(edit => edit.enabled !== false))

  function toggleSentenceDelete(sentenceIdx: number) {
    setReviewData(prev => ({
      ...prev,
      sentences: prev.sentences.map(sentence =>
        sentence.idx === sentenceIdx
          ? { ...sentence, isAiDeleted: !sentence.isAiDeleted, blockId: undefined }
          : sentence,
      ),
    }))
  }

  function toggleBlock(blockId: number) {
    setReviewData(prev => {
      const blocks = prev.blocks.map(block =>
        block.id === blockId ? { ...block, enabled: !(block.enabled !== false) } : block,
      )
      const enabledBlockIds = new Set(blocks.filter(block => block.enabled !== false).map(block => block.id))
      const sentences = prev.sentences.map(sentence =>
        sentence.blockId === blockId
          ? { ...sentence, isAiDeleted: enabledBlockIds.has(blockId) }
          : sentence,
      )
      return { ...prev, blocks, sentences }
    })
  }

  function toggleFineEdit(targetEdit: ReviewFineEdit) {
    setReviewData(prev => ({
      ...prev,
      fineEdits: prev.fineEdits.map((edit, index) =>
        edit.sentenceIdx === targetEdit.sentenceIdx &&
        edit.ds === targetEdit.ds &&
        edit.de === targetEdit.de &&
        edit.type === targetEdit.type
          ? { ...edit, enabled: !(prev.fineEdits[index].enabled !== false) }
          : edit,
      ),
    }))
  }

  async function handleCut() {
    if (!sessionId || isCutting) return
    setIsCutting(true)
    setCutError('')
    try {
      const resp = await fetch(`/api/review/${sessionId}/cut`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(reviewData),
      })
      const data = await resp.json()
      if (!resp.ok) {
        throw new Error(data.error || '剪辑失败')
      }
      setCutAudioUrl(resolveAudioUrl(sessionId, data.audio_url))
      setCutSummary(
        `已剪出 ${data.segments_count} 段，节省 ${formatDuration(Number(data.saved_duration || 0))}，成品时长 ${formatDuration(Number(data.output_duration || 0))}`
      )
    } catch (error) {
      setCutError(error instanceof Error ? error.message : '剪辑失败')
    } finally {
      setIsCutting(false)
    }
  }

  if (!sessionId) {
    return <div style={styles.empty}>先登录并创建一个会话，我们再展示右侧审查画布。</div>
  }

  return (
    <section style={styles.shell}>
      <div style={styles.header}>
        <div>
          <div style={styles.title}>审查画布</div>
          <div style={styles.subtitle}>用于对齐 PodcastCut 的播客审查体验。后续会直接读取 Claude 生成的 review_data.json。</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button
            onClick={handleRefreshReview}
            disabled={!sessionId || isRefreshing}
            style={{
              ...styles.refreshBtn,
              opacity: !sessionId || isRefreshing ? 0.6 : 1,
              cursor: !sessionId || isRefreshing ? 'not-allowed' : 'pointer',
            }}
          >
            {isRefreshing ? '刷新中...' : '刷新审查稿'}
          </button>
          <div style={styles.badge}>{sourceLabel}</div>
        </div>
      </div>

      <div style={styles.body}>
        <aside style={styles.side}>
          <div style={styles.panel}>
            <div style={styles.panelTitle}>音频预览</div>
            <div style={styles.audioCard}>
              <div style={styles.audioMeta}>总时长 {formatDuration(reviewData.audio_duration || 0)}</div>
              {reviewData.audio_url ? (
                <audio controls style={{ width: '100%' }} src={resolveAudioUrl(sessionId, reviewData.audio_url)} />
              ) : (
                <div style={{ fontSize: 13, color: '#8b6f5a', lineHeight: 1.6 }}>
                  先让 Claude 生成真实审查稿；有了 `audio_url` 以后，这里会显示当前会话的音频播放器。
                </div>
              )}
            </div>
          </div>

          <div style={styles.panel}>
            <div style={styles.panelTitle}>确认剪辑</div>
            <button
              onClick={handleCut}
              disabled={!canCut || isCutting}
              style={{
                width: '100%',
                border: 'none',
                borderRadius: 14,
                padding: '12px 14px',
                fontSize: 14,
                fontWeight: 700,
                cursor: !canCut || isCutting ? 'not-allowed' : 'pointer',
                background: !canCut || isCutting ? '#f4d9bf' : '#ea580c',
                color: '#fff',
                opacity: !canCut || isCutting ? 0.7 : 1,
              }}
            >
              {isCutting ? '剪辑中...' : '确认剪辑'}
            </button>
            <div style={{ fontSize: 12, color: '#8b6f5a', marginTop: 10, lineHeight: 1.6 }}>
              会按你当前在画布里启用的删除句子和精剪项生成成品音频。
            </div>
            {cutSummary && (
              <div style={{ marginTop: 10, fontSize: 13, color: '#7c5c44', lineHeight: 1.6 }}>
                {cutSummary}
              </div>
            )}
            {cutError && (
              <div style={{ marginTop: 10, fontSize: 13, color: '#b45309', lineHeight: 1.6 }}>
                {cutError}
              </div>
            )}
          </div>

          {cutAudioUrl && (
            <div style={styles.panel}>
              <div style={styles.panelTitle}>剪辑成品</div>
              <div style={styles.audioCard}>
                <div style={styles.audioMeta}>试听刚刚生成的成品音频</div>
                <audio controls style={{ width: '100%' }} src={cutAudioUrl} />
                <div style={{ marginTop: 10, fontSize: 12 }}>
                  <a href={cutAudioUrl} target="_blank" rel="noreferrer" style={{ color: '#c46b17', fontWeight: 700 }}>
                    打开成品音频
                  </a>
                </div>
              </div>
            </div>
          )}

          <div style={styles.panel}>
            <div style={styles.panelTitle}>粗剪块</div>
            {blockSummaries.length === 0 ? (
              <div style={{ fontSize: 13, color: '#8b6f5a' }}>当前还没有删除块。等 Claude 把审查结果写进 `blocks` 后，这里会出现可开关的粗剪建议。</div>
            ) : (
              blockSummaries.map((block: ReviewBlock) => (
                <div key={block.id} style={{ marginBottom: 12, fontSize: 13, lineHeight: 1.6, color: '#614836' }}>
                  <div style={{ fontWeight: 700, marginBottom: 4 }}>{block.type}</div>
                  <div>{block.reason}</div>
                  <div style={{ color: '#9a7f67', marginTop: 4 }}>范围 {block.range[0]} - {block.range[1]} · {block.duration}</div>
                  <div style={{ marginTop: 8 }}>
                    <button
                      onClick={() => toggleBlock(block.id)}
                      style={{
                        ...styles.controlBtn,
                        ...((block.enabled !== false) ? styles.activeControlBtn : {}),
                      }}
                    >
                      {block.enabled !== false ? '已启用删除块' : '启用删除块'}
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </aside>

        <main style={styles.main}>
          {reviewData.sentences.length === 0 ? (
            <div style={styles.empty}>
              {sourceLabel === '当前会话审查稿'
                ? '当前 review_data.json 已生成，但里面还没有句子数据。需要 Claude 先把 transcript/审查结果写进 sentences，这里才会显示逐句审查视图。'
                : '当前还没有读取到真实审查稿。请先上传音频，并明确让 Claude 生成 review_data.json。然后再点“刷新审查稿”。'}
            </div>
          ) : (
            reviewData.sentences.map((sentence: ReviewSentence) => {
              const sentenceFineEdits = fineBySentence.get(sentence.idx) || []
              return (
                <article
                  key={sentence.idx}
                  style={{
                    ...styles.sentenceCard,
                    ...(sentence.isAiDeleted ? styles.sentenceDeletedCard : {}),
                  }}
                >
                  <div style={styles.sentenceMeta}>
                    <span
                      style={{
                        ...styles.speakerChip,
                        background: speakerColors[sentence.speaker] || '#6b7280',
                      }}
                    >
                      {sentence.speaker}
                    </span>
                    <span style={styles.timeChip}>{sentence.timeStr}</span>
                    {sentence.isAiDeleted && (
                      <span style={styles.deleteChip}>AI 建议删除</span>
                    )}
                  </div>

                  <div style={styles.sentenceText}>{sentence.text}</div>

                  <div style={styles.controlRow}>
                    <button
                      onClick={() => toggleSentenceDelete(sentence.idx)}
                      style={{
                        ...styles.controlBtn,
                        ...(sentence.isAiDeleted ? styles.activeControlBtn : {}),
                      }}
                    >
                      {sentence.isAiDeleted ? '已标记删除' : '标记删除'}
                    </button>
                    {sentence.isAiDeleted && (
                      <button
                        onClick={() => toggleSentenceDelete(sentence.idx)}
                        style={styles.controlBtn}
                      >
                        恢复保留
                      </button>
                    )}
                  </div>

                  {sentenceFineEdits.length > 0 && (
                    <div style={styles.fineEditBox}>
                      {sentenceFineEdits.map((edit, index) => (
                        <div key={`${edit.sentenceIdx}-${index}`} style={{ marginBottom: 8 }}>
                          <div>
                            {edit.type}：{edit.reason}
                          </div>
                          <button
                            onClick={() => toggleFineEdit(edit)}
                            style={{
                              ...styles.controlBtn,
                              marginTop: 6,
                              ...((edit.enabled !== false) ? styles.activeControlBtn : {}),
                            }}
                          >
                            {edit.enabled !== false ? '已启用精剪' : '启用精剪'}
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </article>
              )
            })
          )}
        </main>
      </div>
    </section>
  )
}

function resolveAudioUrl(sessionId: string, audioUrl: string) {
  if (audioUrl.startsWith('http://') || audioUrl.startsWith('https://')) return audioUrl
  return `/api/workspace/${sessionId}/${audioUrl.replace(/^\/+/, '')}`
}
