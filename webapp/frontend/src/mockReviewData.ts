export interface ReviewWord {
  t: string
  s: number
  e: number
}

export interface ReviewSentence {
  idx: number
  speaker: string
  text: string
  startTime: number
  endTime: number
  timeStr: string
  words: ReviewWord[]
  isAiDeleted: boolean
  deleteType?: string
  blockId?: number
  fineEdit?: {
    type: string
    deleteText: string
    keepText: string
    reason: string
    ds: number
    de: number
    enabled: boolean
    count?: number
  }
}

export interface ReviewBlock {
  id: number
  range: [number, number]
  type: string
  topic?: string
  reason: string
  duration: string
  durationSeconds?: number
  startTime?: number
  enabled?: boolean
}

export interface ReviewFineEdit {
  sentenceIdx: number
  type: string
  reason: string
  deleteText?: string
  keepText?: string
  ds: number
  de: number
  enabled?: boolean
}

export interface ReviewDataPayload {
  audio_url: string
  audio_duration: number
  sentences: ReviewSentence[]
  blocks: ReviewBlock[]
  fineEdits: ReviewFineEdit[]
}

export const mockReviewData: ReviewDataPayload = {
  audio_url: '',
  audio_duration: 111.4,
  sentences: [
    {
      idx: 0,
      speaker: '麦雅',
      text: '哈喽大家好，欢迎来到今天的五点一刻。',
      startTime: 66,
      endTime: 69.2,
      timeStr: '1:06',
      words: [],
      isAiDeleted: false,
    },
    {
      idx: 1,
      speaker: '响歌歌',
      text: '今天我们那个要聊的话题是 burnout。',
      startTime: 69.5,
      endTime: 73.2,
      timeStr: '1:09',
      words: [],
      blockId: 1,
      isAiDeleted: true,
      deleteType: 'off_topic',
    },
    {
      idx: 2,
      speaker: '安安',
      text: '我觉得这个在硅谷真的太普遍了。',
      startTime: 77.5,
      endTime: 80.7,
      timeStr: '1:17',
      words: [],
      isAiDeleted: false,
    },
    {
      idx: 3,
      speaker: '响歌歌',
      text: '我先说一下我自己的经历吧。',
      startTime: 81.5,
      endTime: 84.8,
      timeStr: '1:21',
      words: [],
      isAiDeleted: false,
    },
  ],
  blocks: [
    {
      id: 1,
      range: [1, 1],
      type: 'off_topic',
      topic: 'burnout 题外重复',
      reason: '这一句开场重复且信息密度较低，适合粗剪删除。',
      duration: '0:03',
      durationSeconds: 3.7,
      startTime: 69.5,
      enabled: true,
    },
  ],
  fineEdits: [
    {
      sentenceIdx: 1,
      type: 'stutter',
      reason: '口头停顿与重复词较多，可做精剪。',
      deleteText: '那个',
      keepText: '',
      ds: 70.3,
      de: 71.0,
      enabled: true,
    },
    {
      sentenceIdx: 3,
      type: 'consecutive_filler',
      reason: '句首填充词可以裁掉。',
      deleteText: '我先',
      keepText: '先',
      ds: 81.5,
      de: 82.1,
      enabled: true,
    },
  ],
}
