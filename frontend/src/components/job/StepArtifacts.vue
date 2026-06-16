<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useApi } from '../../composables/useApi'
import MarkdownViewer from '../notes/MarkdownViewer.vue'
import { ChevronDown, ChevronRight, FileText, Image as ImageIcon, Braces } from 'lucide-vue-next'

const props = defineProps<{ jobId: string }>()
const api = useApi()

interface AFile { path: string; kind: string }
interface Group { step: string; label: string; files: AFile[] }

const groups = ref<Group[]>([])
const loading = ref(true)
const collapsed = ref<Record<string, boolean>>({})
const sel = ref<AFile | null>(null)
const content = ref('')
const viewerLoading = ref(false)
const viewerErr = ref('')

function artUrl(p: string) {
  return `/api/jobs/${props.jobId}/artifact?path=${encodeURIComponent(p)}`
}
const fname = (p: string) => p.split('/').pop()

async function load() {
  loading.value = true
  try {
    const r = await api.get<{ groups: Group[] }>(`/api/jobs/${props.jobId}/artifacts`)
    groups.value = r.groups
  } catch {
    groups.value = []
  } finally {
    loading.value = false
  }
}

async function view(f: AFile) {
  sel.value = f
  viewerErr.value = ''
  if (f.kind === 'image') { content.value = ''; return }
  viewerLoading.value = true
  try {
    const t = await api.getText(artUrl(f.path))
    content.value = f.kind === 'json'
      ? (() => { try { return JSON.stringify(JSON.parse(t), null, 2) } catch { return t } })()
      : t
  } catch (e: any) {
    viewerErr.value = e.message || '加载失败'
  } finally {
    viewerLoading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="bg-white border border-gray-200 rounded-xl p-4">
    <h3 class="text-sm font-semibold text-gray-700 mb-3">分步产物</h3>
    <div v-if="loading" class="text-sm text-gray-400 py-4">加载中…</div>
    <div v-else-if="!groups.length" class="text-sm text-gray-400 py-4">暂无产物</div>
    <div v-else class="grid md:grid-cols-[240px_1fr] gap-4">
      <!-- 左:按步骤列产物 -->
      <div class="space-y-0.5 max-h-[65vh] overflow-auto">
        <div v-for="g in groups" :key="g.step">
          <button
            @click="collapsed[g.step] = !collapsed[g.step]"
            class="w-full flex items-center gap-1 px-1.5 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 rounded"
          >
            <component :is="collapsed[g.step] ? ChevronRight : ChevronDown" :size="13" />
            <span>{{ g.label }}</span>
            <span class="text-gray-400 font-normal">({{ g.files.length }})</span>
          </button>
          <div v-show="!collapsed[g.step]" class="pl-4 space-y-0.5">
            <button
              v-for="f in g.files"
              :key="f.path"
              @click="view(f)"
              class="w-full text-left px-2 py-1 text-xs rounded flex items-center gap-1.5"
              :class="sel?.path === f.path ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:bg-gray-50'"
            >
              <component
                :is="f.kind === 'image' ? ImageIcon : f.kind === 'json' ? Braces : FileText"
                :size="12" class="flex-shrink-0"
              />
              <span class="truncate">{{ fname(f.path) }}</span>
            </button>
          </div>
        </div>
      </div>

      <!-- 右:查看器 -->
      <div class="min-w-0 md:border-l md:border-gray-100 md:pl-4">
        <div v-if="!sel" class="text-sm text-gray-400 py-12 text-center">← 选左侧文件查看</div>
        <template v-else>
          <div class="text-xs text-gray-400 mb-2 font-mono break-all">{{ sel.path }}</div>
          <img v-if="sel.kind === 'image'" :src="artUrl(sel.path)" loading="lazy"
               class="max-w-full rounded border border-gray-200" />
          <div v-else-if="viewerLoading" class="text-sm text-gray-400">加载中…</div>
          <div v-else-if="viewerErr" class="text-sm text-red-600">{{ viewerErr }}</div>
          <MarkdownViewer v-else-if="sel.path.endsWith('.md')" :content="content" :job-id="jobId" />
          <pre v-else class="text-xs bg-gray-50 rounded p-3 overflow-auto max-h-[65vh] whitespace-pre-wrap break-all">{{ content }}</pre>
        </template>
      </div>
    </div>
  </div>
</template>
