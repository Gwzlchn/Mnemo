// 面包屑段:TopBar 渲染 + store.crumbOverride 共用同一形状。
export interface BreadcrumbSeg {
  t: string        // 文案
  to?: string      // 可点跳转目标(末段通常无 to)
}

// 内容类型:与后端 pipeline 一一对应(video/paper/article/audio)。
export type ContentType = 'video' | 'paper' | 'article' | 'audio'

// 内容类型中文徽章:前端各处展示统一引用。
export const CONTENT_TYPE_LABELS: Record<string, string> = {
  video: '视频',
  paper: '论文',
  article: '文章',
  audio: '播客',
}

export interface JobSummary {
  job_id: string
  content_type: ContentType
  status: string
  created_at: string
  title: string | null
  progress_pct: number
  source: string | null
  domain: string
  collection_id: string | null
}

export interface StepInfo {
  name: string
  label: string | null          // 步骤中文名(来自 pipelines.yaml)
  status: string
  started_at: string | null
  finished_at: string | null
  duration_sec: number | null
  meta: Record<string, any>
  error: string | null
}

export interface JobMedia {
  resolution?: string           // 视频:如 "1920x1080"
  width?: number
  height?: number
  duration_sec?: number         // 源视频/音频时长
  file_size_bytes?: number      // 原始文件精确字节(前端转 KB/MB/GB)
  file_size_mb?: number
  has_subtitle?: boolean
  has_danmaku?: boolean
  word_count?: number           // 文章:字数
  video_codec?: string          // 视频编码,如 "h264" / "av1"
  audio_codec?: string          // 音频编码,如 "aac" / "opus"
  fps?: number                  // 帧率
  bitrate_kbps?: number         // 总码率(kbps)
  video_bitrate_kbps?: number   // 视频流码率(kbps)
}

export interface JobDetail extends JobSummary {
  url: string | null
  updated_at: string | null
  published_at: string | null   // 源内容发布时间(「上传于」)
  collection_name: string | null // 由 collection_id join 出,无归属/集合已删则 null
  media: JobMedia               // 源媒体元信息(视频→分辨率/时长/大小、文章→字数),来自 metadata.json/parsed.json
  artifacts: string[]           // 可见产物文件路径
  meta: Record<string, any>
  steps: StepInfo[]
}

export interface JobListResponse {
  total: number
  items: JobSummary[]
}

export type WorkerStatus =
  | 'online-idle'
  | 'online-busy'
  | 'offline'
  | 'paused'
  | 'stale'

export interface Worker {
  id: string
  type: string
  pools: string[]
  tags: string[]
  reject_tags: string[]
  hostname: string | null
  gpu_name: string | null
  gpu_memory_mb: number | null
  concurrency: number
  remote_addr: string | null
  status: WorkerStatus
  current_job: string | null
  current_step: string | null
  tasks_completed: number
  tasks_failed: number
  total_duration_sec: number
  first_seen: string
  started_at: string | null
  last_heartbeat: string | null
  admin_note: string | null
}

export interface WorkerJob {
  job_id: string
  step: string
  status: string
  started_at: string | null
  finished_at: string | null
  duration_sec: number | null
  error: string | null
}

export interface SystemStatus {
  jobs: {
    total: number
    done: number
    processing: number
    failed: number
  }
}

export interface AuthStatus {
  bilibili: { has_cookies: boolean; status: string }
  youtube: { has_cookies: boolean; status: string }
}

// B站扫码登录契约：与后端 /api/bili/* 严格对齐。
export interface BiliStatus {
  logged_in: boolean
  uname: string | null
}

export interface BiliLoginStart {
  qrcode_key: string
  qr_png: string
  url: string
}

export type BiliLoginState = 'waiting' | 'scanned' | 'confirmed' | 'expired'

export interface BiliLoginPoll {
  state: BiliLoginState
  logged_in: boolean
  uname: string | null
}

export interface ProfileSummary {
  domain: string
  role: string
  terminology_count: number
}

export interface ProfileDetail {
  domain: string
  role?: string
  domain_context?: string
  output_style?: Record<string, any>
  terminology?: string[]
  do_not?: string[]
}

// 领域总览卡片（派生聚合）。与后端 GET /api/domains 对齐。
export interface DomainOverview {
  domain: string
  collection_count: number
  job_count: number
  concept_count: number
  subscription_count: number
  last_active_at: string | null
  // 展示元数据(来自 profile,未设则缺省;前端回退按 domain 名派生)
  display_name?: string
  icon?: string
  color?: string
  description?: string
  role?: string
}

// POST /api/domains 请求体(新建知识库)
export interface CreateDomainPayload {
  domain: string
  display_name?: string
  icon?: string
  color?: string
  role?: string
  description?: string
}

// GET /api/jobs/facets —— 后端聚合的分面计数
export interface JobFacets {
  source: Record<string, number>
  domain: Record<string, number>
  status: Record<string, number>
}

// GET /api/domains/{domain}/concept-timeline
export type TimelineGranularity = 'day' | 'week' | 'month'
export interface ConceptTimeline {
  granularity: TimelineGranularity
  buckets: string[]
  totals: Record<string, number>
  concepts: { term: string; buckets: Record<string, number>; total: number }[]
}

// 集合的订阅源（自动追更）。无订阅则为 null。同步/开关端点用集合自身 id。
export interface CollectionSubscription {
  source_type: string        // bilibili_up/fav/collection · youtube_channel · rss · local_dir
  source_id: string          // B站 mid / 频道URL / feed URL / 目录路径 / 收藏夹id ...
  source_label?: string      // 后端派生来源短标签(bilibili/youtube/rss/local);前端=name+徽标
  enabled: boolean           // 自动同步开关 = collection.sync_enabled
  last_synced_at: string | null
}

// 集合：与后端 CollectionResponse 严格对齐。
export interface Collection {
  id: string
  name: string
  domain: string
  description: string
  tags: string[]
  job_count: number
  created_at: string
  subscription: CollectionSubscription | null
}

// 术语出现处（类型化）：概念出现在哪条内容、什么类型、什么位置。
export interface TermOccurrence {
  job_id: string
  content_type: string
  location: string | null
}

// 概念主题：域内被标为主题(is_topic=1)的概念。与后端 GET /api/domains/{domain}/topic-concepts 对齐。
export interface TopicConcept {
  term: string
  definition: string
  occurrence_count: number
  related: string[]
  is_topic: boolean
}

// 术语：与后端 GlossaryTermResponse 严格对齐。
export interface GlossaryTerm {
  domain: string
  term: string
  definition: string
  occurrences: TermOccurrence[]
  related: string[]
  status: string
  is_topic: boolean
  definition_locked: boolean
  created_at: string
}

// GET /api/jobs/{id}/concepts —— 本内容命中的概念(GlossaryTerm + 本 job 命中位置)
export interface JobConcept extends GlossaryTerm {
  job_occurrences: TermOccurrence[]
}

// 搜索结果项：与后端 SearchResultItem 严格对齐。
export interface SearchResultItem {
  job_id: string
  title: string | null
  note_type: string
  snippet: string
  content_type: string
  domain: string
  collection_id: string | null
}

export interface SearchResponse {
  total: number
  items: SearchResultItem[]
}

export interface WsEvent {
  event: string
  step?: string
  worker?: string
  current?: number
  total?: number
  pct?: number
  message?: string
  duration_sec?: number
  meta?: Record<string, any>
  error?: string
  retries?: number
  reason?: string
  progress_pct?: number
}
