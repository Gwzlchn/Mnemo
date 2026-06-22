// 订阅来源元数据(前端单一事实源)。与后端 source_type / source_label 对齐:
// 后端 SOURCE_LABELS: bilibili_up/fav/collection→bilibili, youtube_channel→youtube,
// rss→rss, local_dir→local。这里按「具体 source_type」给图标/输入提示,按 source_label 给徽标配色。
import type { Component } from 'vue'
import {
  Rss, Youtube, FolderInput, Folder, Star, ListVideo,
} from 'lucide-vue-next'

type Icon = Component

export interface SourceTypeMeta {
  type: string          // source_type(后端枚举)
  label: string         // 选择器里的人类名
  group: string         // 派生 source_label(徽标/配色键)
  icon: Icon            // 列表/卡片图标
  idLabel: string       // source_id 输入框的字段名
  placeholder: string   // 输入占位
  hint: string          // 输入说明
}

// 新建订阅时可选的来源(顺序即选择器顺序)。
export const SOURCE_TYPES: SourceTypeMeta[] = [
  { type: 'bilibili_up', label: 'B站 UP 主', group: 'bilibili', icon: Rss,
    idLabel: 'UP 主页 / mid', placeholder: '如 247209804 或 space.bilibili.com/247209804',
    hint: 'B站 UP 主空间 ID（mid）或其主页链接，自动追更该 UP 的全部投稿。' },
  { type: 'bilibili_fav', label: 'B站 收藏夹', group: 'bilibili', icon: Star,
    idLabel: '收藏夹 ID / 链接', placeholder: '收藏夹 media_id 或收藏夹链接',
    hint: '订阅某个收藏夹，追更其中新增的视频。' },
  { type: 'bilibili_collection', label: 'B站 合集 / 系列', group: 'bilibili', icon: ListVideo,
    idLabel: '合集链接', placeholder: '合集/系列链接，或 mid:season|series:sid',
    hint: '订阅 UP 的某个合集或视频系列。' },
  { type: 'youtube_channel', label: 'YouTube 频道', group: 'youtube', icon: Youtube,
    idLabel: '频道链接', placeholder: 'https://www.youtube.com/@handle 或 /channel/UC...',
    hint: '频道主页链接（@handle、/channel/UC…、/c/…），追更频道全部上传。' },
  { type: 'rss', label: 'RSS / Atom（含公众号）', group: 'rss', icon: Rss,
    idLabel: 'Feed 地址', placeholder: 'https://example.com/feed.xml',
    hint: '通用 RSS/Atom 源。微信公众号请填 RSSHub / wechat2rss 等桥生成的 feed 地址；播客、博客、arXiv 同理。' },
  { type: 'local_dir', label: '本地目录', group: 'local', icon: FolderInput,
    idLabel: '目录路径', placeholder: '/data/inbox',
    hint: '容器内可见的目录路径（默认 /data/inbox）。扫描其中文件，按扩展名判类型自动入库。' },
]

const BY_TYPE: Record<string, SourceTypeMeta> = Object.fromEntries(
  SOURCE_TYPES.map((s) => [s.type, s]),
)

// 徽标文案 + 图标 + badge 配色类(按 source_label 分组)。
const GROUP_BADGE: Record<string, { text: string; icon: Icon; cls: string }> = {
  bilibili: { text: 'bilibili', icon: Rss, cls: 'b-info' },
  youtube: { text: 'youtube', icon: Youtube, cls: 'b-bad' },
  rss: { text: 'rss', icon: Rss, cls: 'b-warn' },
  local: { text: 'local', icon: Folder, cls: 'b-mut' },
}

// 给订阅集合取来源标签(优先后端 source_label,回退按 source_type 派生)。
export function sourceLabelOf(sub: { source_type: string; source_label?: string } | null | undefined): string {
  if (!sub) return ''
  if (sub.source_label) return sub.source_label
  return BY_TYPE[sub.source_type]?.group ?? sub.source_type
}

export function sourceBadge(label: string) {
  return GROUP_BADGE[label] ?? { text: label, icon: Rss, cls: 'b-mut' }
}

export function sourceMeta(type: string): SourceTypeMeta | undefined {
  return BY_TYPE[type]
}

// 订阅源主页/原始链接(详情页「打开来源」)。尽力而为,拿不到返回 null。
export function sourceHomeUrl(sub: { source_type: string; source_id: string }): string | null {
  const { source_type: t, source_id: id } = sub
  if (!id) return null
  if (t === 'bilibili_up') return /^\d+$/.test(id) ? `https://space.bilibili.com/${id}` : id
  if (t === 'youtube_channel' || t === 'rss') return /^https?:\/\//.test(id) ? id : null
  if (t === 'bilibili_fav' || t === 'bilibili_collection') return /^https?:\/\//.test(id) ? id : null
  return null  // local_dir 无链接
}
