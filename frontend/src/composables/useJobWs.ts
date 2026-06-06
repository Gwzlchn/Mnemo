import { ref, watch, onUnmounted, type Ref } from 'vue'
import type { StepInfo, WsEvent } from '../types'

export function useJobWs(jobId: Ref<string>) {
  const steps = ref<StepInfo[]>([])
  const jobStatus = ref('processing')
  const connected = ref(false)
  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let retryDelay = 1000

  function connect() {
    if (!jobId.value) return
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    ws = new WebSocket(`${protocol}//${location.host}/api/ws/jobs/${jobId.value}`)

    ws.onopen = () => {
      connected.value = true
      retryDelay = 1000
    }

    ws.onmessage = (e) => {
      const event: WsEvent = JSON.parse(e.data)
      handleEvent(event)
    }

    ws.onclose = () => {
      connected.value = false
      if (jobStatus.value === 'processing' || jobStatus.value === 'pending') {
        reconnectTimer = setTimeout(connect, retryDelay)
        retryDelay = Math.min(retryDelay * 2, 30000)
      }
    }

    ws.onerror = () => ws?.close()
  }

  function handleEvent(event: WsEvent) {
    const step = steps.value.find(s => s.name === event.step)

    switch (event.event) {
      case 'step_ready':
        if (step) step.status = 'ready'
        break
      case 'step_start':
        if (step) step.status = 'running'
        break
      case 'step_progress':
        if (step) {
          step.status = 'running'
          step.meta = { ...step.meta, pct: event.pct, current: event.current, total: event.total }
        }
        break
      case 'step_done':
        if (step) {
          step.status = 'done'
          step.duration_sec = event.duration_sec ?? null
          if (event.meta) step.meta = { ...step.meta, ...event.meta }
        }
        break
      case 'step_failed':
        if (step) {
          step.status = 'failed'
          step.error = event.error ?? null
        }
        break
      case 'step_skipped':
        if (step) {
          step.status = 'skipped'
          step.meta = { ...step.meta, reason: event.reason }
        }
        break
      case 'job_done':
        jobStatus.value = 'done'
        break
      case 'job_failed':
        jobStatus.value = 'failed'
        break
    }
  }

  function setInitialSteps(initialSteps: StepInfo[]) {
    steps.value = initialSteps
  }

  function disconnect() {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    ws?.close()
    ws = null
  }

  watch(jobId, (newId, oldId) => {
    if (oldId) disconnect()
    if (newId) connect()
  }, { immediate: true })

  onUnmounted(disconnect)

  return { steps, jobStatus, connected, setInitialSteps }
}
