<script setup lang="ts">
import { ref, onMounted, inject } from 'vue'
import { useRouter } from 'vue-router'
import { useApi } from '../composables/useApi'
import { Rss, RefreshCw, Plus, Trash2, Library } from 'lucide-vue-next'

const api = useApi()
const router = useRouter()
const showToast = inject<(m: string, t?: string) => void>('showToast', () => {})

interface Sub {
  id: string; source_type: string; source_id: string; name: string
  domain: string; collection_id: string | null; enabled: boolean
  last_synced_at: string | null; created_at: string
}

const subs = ref<Sub[]>([])
const loading = ref(true)
const syncing = ref<Record<string, boolean>>({})

// 新增订阅表单
const mid = ref('')
const name = ref('')
const domain = ref('general')
const adding = ref(false)
const addError = ref('')

async function load() {
  loading.value = true
  try {
    const r = await api.get<{ subscriptions: Sub[] }>('/api/subscriptions')
    subs.value = r.subscriptions
  } catch (e: any) {
    showToast(e.message || '加载失败', 'error')
  } finally {
    loading.value = false
  }
}

async function addSub() {
  const m = mid.value.trim().replace(/\D/g, '')  // 只留数字 mid
  if (!m) { addError.value = '请输入 UP 主 mid(纯数字)'; return }
  adding.value = true; addError.value = ''
  try {
    const r = await api.post<{ sync: any }>('/api/subscriptions', {
      source_id: m, name: name.value.trim() || undefined, domain: domain.value, sync_now: true,
    })
    const s = r.sync
    if (s?.error) showToast(`订阅已建,但首次同步失败:${s.error}`, 'error')
    else showToast(`订阅成功,已入库 ${s?.new ?? 0} 个新视频(共 ${s?.total ?? 0})`, 'success')
    mid.value = ''; name.value = ''
    await load()
  } catch (e: any) {
    addError.value = e.message || '订阅失败'
  } finally {
    adding.value = false
  }
}

async function syncNow(s: Sub) {
  syncing.value[s.id] = true
  try {
    const r = await api.post<{ new: number; total: number }>(`/api/subscriptions/${s.id}/sync`)
    showToast(`同步完成:新增 ${r.new} 个(共 ${r.total})`, 'success')
    await load()
  } catch (e: any) {
    showToast(e.message || '同步失败', 'error')
  } finally {
    syncing.value[s.id] = false
  }
}

async function removeSub(s: Sub) {
  if (!confirm(`删除订阅「${s.name}」?(已入库的视频/集合保留)`)) return
  try {
    await api.del(`/api/subscriptions/${s.id}`)
    await load()
  } catch (e: any) {
    showToast(e.message || '删除失败', 'error')
  }
}

function fmt(t: string | null) {
  if (!t) return '从未'
  return new Date(t).toLocaleString('zh-CN', { hour12: false })
}

onMounted(load)
</script>

<template>
  <div class="space-y-4">
    <h2 class="text-xl font-bold flex items-center gap-2">
      <Rss :size="22" /> 订阅
    </h2>

    <!-- 新增订阅 -->
    <div class="bg-white border border-gray-200 rounded-xl p-4" data-submit-form>
      <div class="text-sm font-medium text-gray-700 mb-2">订阅 B站 UP 主</div>
      <div class="flex flex-col sm:flex-row gap-2">
        <input v-model="mid" placeholder="UP 主 mid(空间页 URL 里的数字)"
               class="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg" @keyup.enter="addSub" />
        <input v-model="name" placeholder="名称(可选)"
               class="sm:w-40 px-3 py-2 text-sm border border-gray-200 rounded-lg" />
        <select v-model="domain" class="px-3 py-2 text-sm border border-gray-200 rounded-lg">
          <option value="general">general</option>
          <option value="deep-learning">deep-learning</option>
          <option value="programming">programming</option>
        </select>
        <button @click="addSub" :disabled="adding"
                class="px-4 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1">
          <Plus :size="16" /> {{ adding ? '同步中…' : '订阅并同步' }}
        </button>
      </div>
      <div v-if="addError" class="text-xs text-red-600 mt-2">{{ addError }}</div>
      <div class="text-xs text-gray-400 mt-2">订阅后会自动拉取该 UP 全部视频走流水线,并定期追更新视频。</div>
    </div>

    <div v-if="loading" class="text-sm text-gray-400 py-8 text-center">加载中...</div>
    <div v-else-if="subs.length === 0" class="text-sm text-gray-400 py-8 text-center">还没有订阅。</div>

    <div v-else class="space-y-2">
      <div v-for="s in subs" :key="s.id"
           class="bg-white border border-gray-200 rounded-xl p-4 flex items-center gap-3">
        <Rss :size="18" class="text-blue-500 flex-shrink-0" />
        <div class="flex-1 min-w-0">
          <div class="font-medium truncate">{{ s.name }}
            <span class="text-xs text-gray-400 ml-1">{{ s.source_type }}:{{ s.source_id }}</span>
          </div>
          <div class="text-xs text-gray-500">上次同步:{{ fmt(s.last_synced_at) }} · {{ s.domain }}</div>
        </div>
        <button v-if="s.collection_id" @click="router.push(`/collections/${s.collection_id}`)"
                class="p-2 text-gray-400 hover:text-blue-600" title="查看集合">
          <Library :size="16" />
        </button>
        <button @click="syncNow(s)" :disabled="syncing[s.id]"
                class="px-2.5 py-1 text-xs rounded-md border border-gray-200 text-gray-600 hover:bg-gray-50 flex items-center gap-1 disabled:opacity-50">
          <RefreshCw :size="13" :class="syncing[s.id] ? 'animate-spin' : ''" />
          {{ syncing[s.id] ? '同步中' : '立即同步' }}
        </button>
        <button @click="removeSub(s)" class="p-2 text-gray-400 hover:text-red-600" title="删除订阅">
          <Trash2 :size="16" />
        </button>
      </div>
    </div>
  </div>
</template>
