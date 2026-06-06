import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useApi } from '../composables/useApi'
import type { Worker } from '../types'

export const useWorkerStore = defineStore('workers', () => {
  const api = useApi()
  const workers = ref<Worker[]>([])
  const loading = ref(false)

  async function fetchAll() {
    loading.value = true
    try {
      workers.value = await api.get<Worker[]>('/api/workers')
    } finally {
      loading.value = false
    }
  }

  async function drain(workerId: string) {
    await api.put(`/api/workers/${workerId}`, { status: 'draining' })
    await fetchAll()
  }

  async function undrain(workerId: string) {
    await api.put(`/api/workers/${workerId}`, { status: 'idle' })
    await fetchAll()
  }

  async function updateNote(workerId: string, note: string) {
    await api.put(`/api/workers/${workerId}`, { admin_note: note })
    await fetchAll()
  }

  async function remove(workerId: string) {
    await api.del(`/api/workers/${workerId}`)
    await fetchAll()
  }

  return { workers, loading, fetchAll, drain, undrain, updateNote, remove }
})
