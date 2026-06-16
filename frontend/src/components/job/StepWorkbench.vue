<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useApi } from '../../composables/useApi'
import MarkdownViewer from '../notes/MarkdownViewer.vue'
import type { StepInfo } from '../../types'
import { Check, X, Minus, Loader, Clock, ChevronRight, FileText, Image as ImageIcon, Braces } from 'lucide-vue-next'

const props = defineProps<{ jobId: string; steps: StepInfo[] }>()
const api = useApi()

const statusIcon: Record<string, any> = { done: Check, failed: X, skipped: Minus, running: Loader }
const statusColor: Record<string, string> = {
  done: 'bg-green-500 text-white', failed: 'bg-red-500 text-white',
  running: 'bg-blue-500 text-white animate-pulse', skipped: 'bg-gray-300 text-gray-500',
  waiting: 'bg-gray-200 text-gray-400', ready: 'bg-yellow-400 text-white',
}
const statusText: Record<string, string> = {
  done: '完成', failed: '失败', running: '进行中', skipped: '跳过', waiting: '等待', ready: '就绪',
}

// 产出摘要:把 step.meta 渲染成友好「标签：值」。未知键回退原键,内部键跳过。
const META_LABELS: Record<string, string> = {
  frames: '关键帧', events: '时间节', lines: '字幕行', chunks: '分块', mode: '模式',
  kept: '保留帧', scenes: '场景数', count: '数量', danmaku: '弹幕条', sections: '章节',
  figures: '图表', duration: '时长', words: '字数', pages: '页数', provider: '模型',
}
const MODE_LABELS: Record<string, string> = { zh: '加标点', translate: '翻译为中文' }
const META_SKIP = new Set(['pct', 'current', 'total', 'exec_id', 'worker'])

interface AFile { path: string; kind: string }
interface Group { step: string; label: string; files: AFile[] }
const groups = ref<Group[]>([])
const filesByStep = computed<Record<string, AFile[]>>(() => {
  const m: Record<string, AFile[]> = {}
  for (const g of groups.value) m[g.step] = g.files
  return m
})

const sel = ref('')                      // 选中步骤名
const selFile = ref<AFile | null>(null)
const fileContent = ref('')
const fileLoading = ref(false)
const fileErr = ref('')
const logOpen = ref(false)
const logText = ref('')
const logLoading = ref(false)
const logErr = ref('')

const selStep = computed(() => props.steps.find(s => s.name === sel.value) || null)
const selFiles = computed(() => filesByStep.value[sel.value] || [])

const artUrl = (p: string) => `/api/jobs/${props.jobId}/artifact?path=${encodeURIComponent(p)}`
const fname = (p: string) => p.split('/').pop()
const stepLabel = (s: StepInfo) => s.label || s.name

function fmtTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('zh-CN',
    { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' })
}
function fmtDur(sec: number | null): string {
  if (sec == null) return '—'
  return sec < 60 ? `${sec.toFixed(1)}s` : `${Math.floor(sec / 60)}m${Math.floor(sec % 60)}s`
}
function stepPct(s: StepInfo): number | null {
  return s.status === 'running' && s.meta?.pct != null ? s.meta.pct : null
}
function metaRows(s: StepInfo): { k: string; v: string }[] {
  const rows: { k: string; v: string }[] = []
  for (const [k, val] of Object.entries(s.meta || {})) {
    if (META_SKIP.has(k) || val == null || typeof val === 'object') continue
    let v = String(val)
    if (k === 'mode') v = MODE_LABELS[v] || v
    rows.push({ k: META_LABELS[k] || k, v })
  }
  return rows
}

async function loadGroups() {
  try {
    const r = await api.get<{ groups: Group[] }>(`/api/jobs/${props.jobId}/artifacts`)
    groups.value = r.groups || []
  } catch { groups.value = [] }
}

function pickDefault() {
  const s = props.steps
  if (!s.length) return
  const running = s.find(x => x.status === 'running')
  const lastDone = [...s].reverse().find(x => x.status === 'done' || x.status === 'failed')
  selectStep((running || lastDone || s[0]).name)
}

function selectStep(name: string) {
  if (!name) return
  sel.value = name
  selFile.value = null; fileContent.value = ''; fileErr.value = ''
  logOpen.value = false; logText.value = ''; logErr.value = ''
  const f = (filesByStep.value[name] || [])[0]
  if (f) viewFile(f)
}

async function viewFile(f: AFile) {
  selFile.value = f; fileErr.value = ''
  if (f.kind === 'image') { fileContent.value = ''; return }
  fileLoading.value = true
  try {
    const t = await api.getText(artUrl(f.path))
    fileContent.value = f.kind === 'json'
      ? (() => { try { return JSON.stringify(JSON.parse(t), null, 2) } catch { return t } })()
      : t
  } catch (e: any) { fileErr.value = e.message || '加载失败' }
  finally { fileLoading.value = false }
}

async function toggleLog() {
  logOpen.value = !logOpen.value
  if (logOpen.value && !logText.value && !logErr.value) {
    logLoading.value = true
    try { logText.value = await api.getText(`/api/jobs/${props.jobId}/steps/${sel.value}/log`) }
    catch (e: any) { logErr.value = e?.status === 404 ? '该步骤暂无日志' : (e?.message || '日志加载失败') }
    finally { logLoading.value = false }
  }
}

onMounted(async () => { await loadGroups(); pickDefault() })
// steps 可能在 detail 加载后才到;若还没选中则补选默认。
watch(() => props.steps.map(s => s.name).join(','), () => { if (!sel.value) pickDefault() })
</script>

<template>
  <div class="bg-white border border-gray-200 rounded-xl p-4">
    <h3 class="text-sm font-semibold text-gray-700 mb-3">步骤与产物</h3>
    <div class="grid md:grid-cols-[300px_1fr] gap-4">
      <!-- 左:步骤时间线 -->
      <div class="space-y-0 md:border-r md:border-gray-100 md:pr-2 max-h-[72vh] overflow-auto">
        <button
          v-for="(s, idx) in steps" :key="s.name" @click="selectStep(s.name)"
          class="w-full text-left rounded-lg px-2 py-2 flex gap-2.5 transition-colors"
          :class="sel === s.name ? 'bg-blue-50 ring-1 ring-blue-200' : 'hover:bg-gray-50'"
        >
          <div class="flex flex-col items-center">
            <span
              class="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0"
              :class="statusColor[s.status] || statusColor.waiting"
            >
              <component :is="statusIcon[s.status]" v-if="statusIcon[s.status]" :size="13" />
              <span v-else class="text-[10px]">{{ idx + 1 }}</span>
            </span>
            <div v-if="idx < steps.length - 1" class="w-0.5 flex-1 min-h-[0.5rem] my-0.5 bg-gray-200" />
          </div>
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-1.5">
              <span class="text-sm font-medium truncate" :class="s.status === 'waiting' ? 'text-gray-400' : 'text-gray-800'">{{ stepLabel(s) }}</span>
              <span class="text-[10px] px-1 py-0.5 rounded flex-shrink-0" :class="statusColor[s.status] || statusColor.waiting">{{ statusText[s.status] || s.status }}</span>
            </div>
            <div class="text-[11px] text-gray-400 font-mono mt-0.5">{{ s.name }}</div>
            <div v-if="stepPct(s) != null" class="mt-1 w-full bg-gray-200 rounded-full h-1">
              <div class="bg-blue-500 h-full rounded-full transition-all" :style="{ width: `${stepPct(s)}%` }" />
            </div>
            <div v-else-if="s.duration_sec" class="text-[11px] text-gray-400 mt-0.5">耗时 {{ fmtDur(s.duration_sec) }}</div>
          </div>
        </button>
      </div>

      <!-- 右:选中步骤详情 + 产物 -->
      <div class="min-w-0">
        <template v-if="selStep">
          <div class="flex items-center gap-2 flex-wrap">
            <h4 class="text-base font-semibold text-gray-800">{{ stepLabel(selStep) }}</h4>
            <span class="text-xs px-1.5 py-0.5 rounded" :class="statusColor[selStep.status] || statusColor.waiting">{{ statusText[selStep.status] || selStep.status }}</span>
            <span class="text-xs text-gray-400 font-mono">{{ selStep.name }}</span>
          </div>

          <div class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500 mt-2">
            <span><Clock :size="12" class="inline -mt-0.5" /> 开始 {{ fmtTime(selStep.started_at) }}</span>
            <span>结束 {{ fmtTime(selStep.finished_at) }}</span>
            <span>耗时 {{ fmtDur(selStep.duration_sec) }}</span>
          </div>

          <div v-if="stepPct(selStep) != null" class="mt-2 w-full bg-gray-200 rounded-full h-1.5">
            <div class="bg-blue-500 h-full rounded-full" :style="{ width: `${stepPct(selStep)}%` }" />
          </div>

          <p v-if="selStep.error" class="text-xs text-red-600 mt-2 break-all bg-red-50 rounded p-2">✗ {{ selStep.error }}</p>

          <!-- 产出摘要(可读,替代原始 JSON) -->
          <div v-if="metaRows(selStep).length" class="mt-3 flex flex-wrap gap-2">
            <span v-for="r in metaRows(selStep)" :key="r.k" class="text-xs bg-gray-50 border border-gray-100 rounded px-2 py-1 text-gray-600">
              {{ r.k }}：<span class="text-gray-800 font-medium">{{ r.v }}</span>
            </span>
          </div>

          <!-- 产物文件 -->
          <div v-if="selFiles.length" class="mt-4">
            <div class="text-xs text-gray-500 mb-1.5">产物（{{ selFiles.length }}）</div>
            <div class="flex flex-wrap gap-1.5 mb-2 max-h-28 overflow-auto">
              <button
                v-for="f in selFiles" :key="f.path" @click="viewFile(f)"
                class="text-xs px-2 py-1 rounded border flex items-center gap-1"
                :class="selFile?.path === f.path ? 'bg-blue-100 border-blue-200 text-blue-700' : 'border-gray-200 text-gray-600 hover:bg-gray-50'"
              >
                <component :is="f.kind === 'image' ? ImageIcon : f.kind === 'json' ? Braces : FileText" :size="11" />
                <span class="truncate max-w-[12rem]">{{ fname(f.path) }}</span>
              </button>
            </div>
            <div v-if="selFile" class="border border-gray-100 rounded-lg p-3 bg-gray-50/40">
              <img v-if="selFile.kind === 'image'" :src="artUrl(selFile.path)" loading="lazy" class="max-w-full rounded border border-gray-200" />
              <div v-else-if="fileLoading" class="text-xs text-gray-400">加载中…</div>
              <div v-else-if="fileErr" class="text-xs text-red-600">{{ fileErr }}</div>
              <MarkdownViewer v-else-if="selFile.path.endsWith('.md')" :content="fileContent" :job-id="jobId" />
              <pre v-else class="text-xs whitespace-pre-wrap break-all max-h-[55vh] overflow-auto">{{ fileContent }}</pre>
            </div>
          </div>
          <div v-else-if="selStep.status === 'done' || selStep.status === 'skipped'" class="mt-3 text-xs text-gray-400">（此步无可展示的产物文件）</div>

          <!-- 原始日志(默认折叠,排错用) -->
          <div v-if="selStep.status !== 'waiting' && selStep.status !== 'ready'" class="mt-4">
            <button @click="toggleLog" class="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1">
              <ChevronRight :size="12" :class="logOpen ? 'rotate-90' : ''" class="transition-transform" /> 原始日志
            </button>
            <div v-if="logOpen" class="mt-1.5">
              <div v-if="logLoading" class="text-xs text-gray-400">加载中…</div>
              <div v-else-if="logErr" class="text-xs text-gray-400">{{ logErr }}</div>
              <pre v-else class="text-xs bg-gray-900 text-gray-100 rounded-lg p-3 max-h-72 overflow-auto whitespace-pre-wrap break-all">{{ logText }}</pre>
            </div>
          </div>
        </template>
        <div v-else class="text-sm text-gray-400 py-12 text-center">← 选择左侧步骤查看详情与产物</div>
      </div>
    </div>
  </div>
</template>
