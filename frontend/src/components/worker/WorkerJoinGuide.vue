<script setup lang="ts">
import { ref, computed, inject } from 'vue'
import { Copy, Check } from 'lucide-vue-next'

const workerType = ref('cpu')
const copied = ref(false)
const showToast = inject<(msg: string, type: 'success' | 'error' | 'info') => void>('showToast')

const types = ['cpu', 'gpu', 'ai', 'download']

const command = computed(() => {
  return `docker run -d \\
  -e REDIS_URL=redis://<HOST>:6379/0 \\
  -e DATA_DIR=/data \\
  -v /path/to/data:/data \\
  worker:latest python -m worker.main --type ${workerType.value}`
})

async function copy() {
  try {
    await navigator.clipboard.writeText(command.value)
    copied.value = true
    showToast?.('已复制', 'success')
    setTimeout(() => { copied.value = false }, 2000)
  } catch {
    showToast?.('复制失败', 'error')
  }
}
</script>

<template>
  <div class="bg-white border border-gray-200 rounded-xl p-4">
    <h4 class="text-sm font-semibold text-gray-700 mb-3">接入新 Worker</h4>
    <p class="text-xs text-gray-500 mb-3">复制以下命令到目标机器执行：</p>

    <div class="bg-gray-900 text-green-400 rounded-lg p-3 text-xs font-mono whitespace-pre-wrap break-all">{{ command }}</div>

    <div class="flex items-center gap-3 mt-3">
      <label class="text-xs text-gray-600">类型：</label>
      <select v-model="workerType" class="px-2 py-1 border border-gray-300 rounded text-sm bg-white">
        <option v-for="t in types" :key="t" :value="t">{{ t.toUpperCase() }}</option>
      </select>
      <div class="flex-1" />
      <button @click="copy" class="flex items-center gap-1 px-3 py-1.5 bg-blue-600 text-white text-xs rounded-lg hover:bg-blue-700 transition-colors">
        <component :is="copied ? Check : Copy" :size="14" />
        {{ copied ? '已复制' : '复制命令' }}
      </button>
    </div>
  </div>
</template>
