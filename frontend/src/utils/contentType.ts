// 内容类型(content_type)与笔记类型(note_type)的展示映射 —— 前端单一事实源。
// 此前 typeIcon / typePillClass / NOTE_TYPE_* 在 6+ 视图各写一份且回退值已漂移
// (t-video vs t-article),这里统一,各处 import。
import type { Component } from 'vue'
import { Play, FileText, Newspaper, Headphones } from 'lucide-vue-next'
import { CONTENT_TYPE_LABELS } from '../types'

export { CONTENT_TYPE_LABELS }

const CONTENT_TYPE_ICONS: Record<string, Component> = {
  video: Play, paper: FileText, article: Newspaper, audio: Headphones,
}
const CONTENT_TYPE_PILLS: Record<string, string> = {
  video: 't-video', paper: 't-paper', article: 't-article', audio: 't-audio',
}

// 统一回退:未知/缺省类型按「文章」呈现(消除此前 t-video / t-article 回退分歧)。
export function contentTypeIcon(t: string | null | undefined): Component {
  return CONTENT_TYPE_ICONS[t ?? ''] ?? Newspaper
}
export function contentTypePill(t: string | null | undefined): string {
  return CONTENT_TYPE_PILLS[t ?? ''] ?? 't-article'
}
export function contentTypeLabel(t: string | null | undefined): string {
  return CONTENT_TYPE_LABELS[t ?? ''] ?? (t ?? '')
}

// 笔记类型(note_type)徽章文案,与后端取值对齐(smart|mechanical|transcript)。
export const NOTE_TYPE_LABELS: Record<string, string> = {
  smart: '智能笔记',
  mechanical: '机械稿',
  transcript: '逐字稿',
}
export function noteTypeLabel(t: string | null | undefined): string {
  return NOTE_TYPE_LABELS[t ?? ''] ?? (t ?? '')
}
