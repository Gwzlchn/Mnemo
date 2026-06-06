<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useJobStore } from '../stores/jobs'
import { useGlobalWs } from '../composables/useGlobalWs'
import { useApi } from '../composables/useApi'
import JobSubmitForm from '../components/job/JobSubmitForm.vue'
import JobCard from '../components/job/JobCard.vue'
import EmptyState from '../components/common/EmptyState.vue'
import { Activity, CheckCircle, Clock, AlertCircle } from 'lucide-vue-next'
import type { JobSummary, JobListResponse } from '../types'

const jobStore = useJobStore()
const api = useApi()
const { systemStatus } = useGlobalWs()

const processingJobs = ref<JobSummary[]>([])
const recentDone = ref<JobSummary[]>([])
const loading = ref(true)
let refreshTimer: ReturnType<typeof setInterval> | null = null

async function loadJobs() {
  try {
    const [procRes, doneRes] = await Promise.all([
      api.get<JobListResponse>('/api/jobs?status=processing&limit=10'),
      api.get<JobListResponse>('/api/jobs?status=done&limit=5'),
    ])
    processingJobs.value = procRes.items || []
    recentDone.value = doneRes.items || []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadJobs()
  refreshTimer = setInterval(loadJobs, 30000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})

const stats = [
  { key: 'total', label: '总任务', icon: Activity, color: 'text-gray-700' },
  { key: 'done', label: '完成', icon: CheckCircle, color: 'text-green-600' },
  { key: 'processing', label: '处理中', icon: Clock, color: 'text-blue-600' },
  { key: 'failed', label: '失败', icon: AlertCircle, color: 'text-red-600' },
]
</script>

<template>
  <div class="space-y-4">
    <JobSubmitForm />

    <!-- Stats -->
    <div v-if="systemStatus" class="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3">
      <div
        v-for="s in stats"
        :key="s.key"
        class="bg-white border border-gray-200 rounded-xl p-3 flex items-center gap-2"
      >
        <component :is="s.icon" :size="18" :class="s.color" />
        <div>
          <div class="text-lg font-bold">{{ (systemStatus.jobs as any)[s.key] ?? 0 }}</div>
          <div class="text-xs text-gray-500">{{ s.label }}</div>
        </div>
      </div>
    </div>

    <!-- Processing -->
    <div>
      <h3 class="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-1.5">
        <Clock :size="14" class="text-blue-600" />
        进行中
      </h3>
      <div v-if="loading" class="text-sm text-gray-400 py-4 text-center">加载中...</div>
      <div v-else-if="processingJobs.length === 0">
        <EmptyState message="没有进行中的任务" />
      </div>
      <div v-else class="space-y-2">
        <JobCard v-for="job in processingJobs" :key="job.job_id" :job="job" />
      </div>
    </div>

    <!-- Recent done -->
    <div>
      <h3 class="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-1.5">
        <CheckCircle :size="14" class="text-green-600" />
        最近完成
      </h3>
      <div v-if="recentDone.length === 0 && !loading">
        <EmptyState message="暂无完成的任务" />
      </div>
      <div v-else class="space-y-2">
        <JobCard v-for="job in recentDone" :key="job.job_id" :job="job" />
      </div>
    </div>
  </div>
</template>
