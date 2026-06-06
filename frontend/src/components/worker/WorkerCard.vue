<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Worker } from '../../types'
import StatusBadge from '../common/StatusBadge.vue'
import { useWorkerStore } from '../../stores/workers'
import { Edit3, Trash2, PauseCircle, PlayCircle } from 'lucide-vue-next'

const props = defineProps<{ worker: Worker }>()
const workerStore = useWorkerStore()

const editing = ref(false)
const noteInput = ref(props.worker.admin_note || '')

const statusLight = computed(() => {
  const map: Record<string, string> = {
    idle: 'bg-green-500',
    busy: 'bg-yellow-500',
    draining: 'bg-orange-500',
    offline: 'bg-red-500',
  }
  return map[effectiveStatus.value] || 'bg-gray-400'
})

const effectiveStatus = computed(() => {
  if (props.worker.status === 'idle' || props.worker.status === 'busy' || props.worker.status === 'draining') {
    if (props.worker.last_heartbeat) {
      const elapsed = Date.now() - new Date(props.worker.last_heartbeat).getTime()
      if (elapsed > 30000) return 'offline'
    }
    return props.worker.status
  }
  return props.worker.status
})

const uptimeText = computed(() => {
  if (!props.worker.started_at) return ''
  const sec = (Date.now() - new Date(props.worker.started_at).getTime()) / 1000
  if (sec < 3600) return `${Math.floor(sec / 60)}m`
  return `${Math.floor(sec / 3600)}h${Math.floor((sec % 3600) / 60)}m`
})

const heartbeatText = computed(() => {
  if (!props.worker.last_heartbeat) return '未知'
  const sec = Math.floor((Date.now() - new Date(props.worker.last_heartbeat).getTime()) / 1000)
  if (sec < 60) return `${sec}s 前`
  return `${Math.floor(sec / 60)}m 前`
})

async function toggleDrain() {
  if (effectiveStatus.value === 'draining') {
    await workerStore.undrain(props.worker.id)
  } else {
    await workerStore.drain(props.worker.id)
  }
}

async function saveNote() {
  await workerStore.updateNote(props.worker.id, noteInput.value)
  editing.value = false
}

async function remove() {
  if (confirm(`确定移除 ${props.worker.id} 的记录？`)) {
    await workerStore.remove(props.worker.id)
  }
}
</script>

<template>
  <div class="bg-white border border-gray-200 rounded-xl p-4">
    <div class="flex items-start gap-3">
      <span class="w-3 h-3 rounded-full mt-1.5 flex-shrink-0" :class="statusLight" />
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 flex-wrap">
          <span class="font-mono text-sm font-medium">{{ worker.id }}</span>
          <StatusBadge :status="effectiveStatus" />
          <span class="px-1.5 py-0.5 bg-gray-100 rounded text-xs text-gray-600 uppercase">{{ worker.type }}</span>
        </div>
        <div class="text-xs text-gray-500 mt-1 flex flex-wrap gap-x-3 gap-y-0.5">
          <span v-if="worker.hostname">{{ worker.hostname }}</span>
          <span>完成 {{ worker.tasks_completed }}</span>
          <span>失败 {{ worker.tasks_failed }}</span>
          <span v-if="uptimeText">运行 {{ uptimeText }}</span>
          <span>心跳 {{ heartbeatText }}</span>
        </div>
        <div v-if="worker.current_step" class="text-xs text-blue-600 mt-1">
          {{ worker.current_step }} ({{ worker.current_job }})
        </div>
        <div v-if="worker.admin_note && !editing" class="text-xs text-gray-500 mt-1 italic">
          {{ worker.admin_note }}
        </div>

        <!-- Edit note -->
        <div v-if="editing" class="mt-2 flex gap-2">
          <input v-model="noteInput" class="flex-1 px-2 py-1 border border-gray-300 rounded text-sm" placeholder="备注" />
          <button @click="saveNote" class="px-2 py-1 bg-blue-600 text-white text-xs rounded">保存</button>
          <button @click="editing = false" class="px-2 py-1 text-gray-500 text-xs">取消</button>
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div class="flex gap-2 mt-3 pt-3 border-t border-gray-100">
      <button
        @click="toggleDrain"
        class="flex items-center gap-1 px-2 py-1 text-xs rounded hover:bg-gray-50 transition-colors"
        :class="effectiveStatus === 'draining' ? 'text-green-600' : 'text-orange-600'"
      >
        <component :is="effectiveStatus === 'draining' ? PlayCircle : PauseCircle" :size="14" />
        {{ effectiveStatus === 'draining' ? '恢复' : '排空' }}
      </button>
      <button @click="editing = true" class="flex items-center gap-1 px-2 py-1 text-xs text-gray-600 rounded hover:bg-gray-50 transition-colors">
        <Edit3 :size="14" />
        备注
      </button>
      <button v-if="effectiveStatus === 'offline'" @click="remove" class="flex items-center gap-1 px-2 py-1 text-xs text-red-600 rounded hover:bg-red-50 transition-colors">
        <Trash2 :size="14" />
        移除
      </button>
    </div>
  </div>
</template>
