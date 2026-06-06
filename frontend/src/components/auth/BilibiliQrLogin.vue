<script setup lang="ts">
import { ref, onUnmounted } from 'vue'
import { useApi } from '../../composables/useApi'
import QRCode from 'qrcode'
import { QrCode, RefreshCw, CheckCircle, Loader } from 'lucide-vue-next'

const api = useApi()
const emit = defineEmits<{ success: [] }>()

const qrcodeDataUrl = ref('')
const qrcodeKey = ref('')
const status = ref<'idle' | 'loading' | 'waiting' | 'scanned' | 'success' | 'expired' | 'error'>('idle')
const message = ref('')
let pollTimer: ReturnType<typeof setInterval> | null = null

async function generate() {
  status.value = 'loading'
  try {
    const data = await api.post<{ qrcode_url: string; qrcode_key: string }>('/api/auth/bilibili/qrcode')
    qrcodeDataUrl.value = await QRCode.toDataURL(data.qrcode_url, { width: 180, margin: 1 })
    qrcodeKey.value = data.qrcode_key
    status.value = 'waiting'
    message.value = '请用 B 站 App 扫码'
    startPolling()
  } catch (e: any) {
    status.value = 'error'
    message.value = e.message || '生成二维码失败'
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    try {
      const data = await api.get<{ status: string; message: string }>(`/api/auth/bilibili/poll?key=${qrcodeKey.value}`)
      message.value = data.message
      if (data.status === 'success') {
        status.value = 'success'
        stopPolling()
        emit('success')
      } else if (data.status === 'expired') {
        status.value = 'expired'
        stopPolling()
      } else if (data.status === 'scanned') {
        status.value = 'scanned'
      }
    } catch {
      // continue polling
    }
  }, 3000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

onUnmounted(stopPolling)
</script>

<template>
  <div class="space-y-3">
    <div v-if="status === 'idle'">
      <button @click="generate" class="flex items-center gap-1.5 px-4 py-2 bg-pink-500 text-white rounded-lg text-sm font-medium hover:bg-pink-600 transition-colors">
        <QrCode :size="16" />
        扫码登录
      </button>
    </div>

    <div v-else-if="status === 'loading'" class="flex items-center gap-2 text-sm text-gray-500">
      <Loader :size="16" class="animate-spin" />
      生成二维码...
    </div>

    <div v-else-if="status === 'waiting' || status === 'scanned'" class="space-y-3">
      <div class="w-48 h-48 bg-white border border-gray-200 rounded-lg flex items-center justify-center">
        <img :src="qrcodeDataUrl" alt="QR" class="w-44 h-44" />
      </div>
      <p class="text-sm" :class="status === 'scanned' ? 'text-blue-600' : 'text-gray-600'">{{ message }}</p>
    </div>

    <div v-else-if="status === 'success'" class="flex items-center gap-2 text-sm text-green-600">
      <CheckCircle :size="16" />
      {{ message }}
    </div>

    <div v-else-if="status === 'expired'" class="space-y-2">
      <p class="text-sm text-orange-600">{{ message }}</p>
      <button @click="generate" class="flex items-center gap-1.5 px-3 py-1.5 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
        <RefreshCw :size="14" />
        重新生成
      </button>
    </div>

    <div v-else-if="status === 'error'" class="space-y-2">
      <p class="text-sm text-red-600">{{ message }}</p>
      <button @click="generate" class="text-sm text-blue-600 hover:underline">重试</button>
    </div>
  </div>
</template>
