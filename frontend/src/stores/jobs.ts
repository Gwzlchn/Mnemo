import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useApi } from '../composables/useApi'
import type { JobSummary, JobDetail, JobListResponse } from '../types'

export const useJobStore = defineStore('jobs', () => {
  const api = useApi()
  const list = ref<JobSummary[]>([])
  const total = ref(0)
  const loading = ref(false)

  async function fetchList(params: { status?: string; limit?: number; offset?: number; append?: boolean } = {}) {
    loading.value = true
    try {
      const qs = new URLSearchParams()
      if (params.status) qs.set('status', params.status)
      qs.set('limit', String(params.limit ?? 20))
      qs.set('offset', String(params.offset ?? 0))
      const data = await api.get<JobListResponse>(`/api/jobs?${qs}`)
      if (params.append) {
        list.value.push(...data.items)
      } else {
        list.value = data.items
      }
      total.value = data.total
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(jobId: string): Promise<JobDetail> {
    return api.get<JobDetail>(`/api/jobs/${jobId}`)
  }

  async function createJob(payload: { url?: string; content_type?: string; domain?: string; style_tags?: string[]; collection_id?: string }) {
    return api.post<{ job_id: string }>('/api/jobs', payload)
  }

  async function uploadJob(file: File, domain: string, styleTags: string[]) {
    const form = new FormData()
    form.append('file', file)
    form.append('domain', domain)
    form.append('style_tags', JSON.stringify(styleTags))
    return api.upload<{ job_id: string }>('/api/jobs/upload', form)
  }

  async function retryJob(jobId: string) {
    return api.post(`/api/jobs/${jobId}/retry`)
  }

  async function rerunJob(jobId: string, fromStep: string) {
    return api.post(`/api/jobs/${jobId}/rerun`, { from_step: fromStep })
  }

  async function deleteJob(jobId: string) {
    await api.del(`/api/jobs/${jobId}`)
  }

  return { list, total, loading, fetchList, fetchDetail, createJob, uploadJob, retryJob, rerunJob, deleteJob }
})
