<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useJobStore } from '../stores/jobs'
import JobCard from '../components/job/JobCard.vue'
import EmptyState from '../components/common/EmptyState.vue'

const jobStore = useJobStore()
const activeTab = ref('')
const offset = ref(0)
const limit = 20
const loadError = ref('')

const tabs = [
  { value: '', label: '全部' },
  { value: 'processing', label: '处理中' },
  { value: 'done', label: '完成' },
  { value: 'failed', label: '失败' },
]

onMounted(() => load())

watch(activeTab, () => {
  offset.value = 0
  load()
})

async function load() {
  loadError.value = ''
  try {
    await jobStore.fetchList({ status: activeTab.value || undefined, limit, offset: offset.value })
  } catch (e: any) {
    loadError.value = e?.message || '加载失败'
  }
}

async function loadMore() {
  offset.value += limit
  try {
    await jobStore.fetchList({ status: activeTab.value || undefined, limit, offset: offset.value, append: true })
  } catch (e: any) {
    loadError.value = e?.message || '加载失败'
  }
}
</script>

<template>
  <div class="space-y-4">
    <h2 class="text-xl font-bold">任务列表</h2>

    <!-- Tab filter -->
    <div class="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
      <button
        v-for="tab in tabs"
        :key="tab.value"
        @click="activeTab = tab.value"
        class="px-3 py-1.5 text-sm rounded-md transition-colors"
        :class="activeTab === tab.value ? 'bg-white shadow-sm font-medium text-gray-800' : 'text-gray-600 hover:text-gray-800'"
      >
        {{ tab.label }}
      </button>
    </div>

    <div v-if="jobStore.loading && jobStore.list.length === 0" class="text-sm text-gray-400 py-8 text-center">加载中...</div>
    <div v-else-if="loadError && jobStore.list.length === 0" class="bg-white border border-gray-200 rounded-xl p-8 flex flex-col items-center text-center">
      <p class="text-sm text-gray-600">{{ loadError }}</p>
      <button @click="load" class="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors">
        重新加载
      </button>
    </div>
    <div v-else-if="jobStore.list.length === 0">
      <EmptyState />
    </div>
    <div v-else class="space-y-2">
      <JobCard v-for="job in jobStore.list" :key="job.job_id" :job="job" />
    </div>

    <div v-if="jobStore.list.length > 0 && jobStore.list.length < jobStore.total" class="text-center pt-2">
      <button @click="loadMore" class="px-4 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
        加载更多
      </button>
    </div>
  </div>
</template>
