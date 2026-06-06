import { ref, onUnmounted } from 'vue'
import type { SystemStatus } from '../types'

const MAX_RETRIES = 10

const systemStatus = ref<SystemStatus | null>(null)
const connected = ref(false)
let ws: WebSocket | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let retryDelay = 1000
let retryCount = 0
let started = false
let refCount = 0

function connect() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return

  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  ws = new WebSocket(`${protocol}//${location.host}/api/ws/global`)

  ws.onopen = () => {
    connected.value = true
    retryDelay = 1000
    retryCount = 0
  }

  ws.onmessage = (e) => {
    systemStatus.value = JSON.parse(e.data)
  }

  ws.onclose = () => {
    connected.value = false
    if (retryCount < MAX_RETRIES && refCount > 0) {
      reconnectTimer = setTimeout(connect, retryDelay)
      retryDelay = Math.min(retryDelay * 2, 30000)
      retryCount++
    }
  }

  ws.onerror = () => ws?.close()
}

function disconnect() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  ws?.close()
  ws = null
  started = false
}

export function useGlobalWs() {
  if (!started) {
    started = true
    connect()
  }
  refCount++

  onUnmounted(() => {
    refCount--
    if (refCount <= 0) {
      disconnect()
      refCount = 0
    }
  })

  return { systemStatus, connected }
}
