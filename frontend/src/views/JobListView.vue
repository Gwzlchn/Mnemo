<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useJobStore } from '../stores/jobs'
import JobCard from '../components/job/JobCard.vue'
import EmptyState from '../components/common/EmptyState.vue'

const jobStore = useJobStore()
const activeTab = ref('')
const offset = ref(0)
const limit = 20

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
  await jobStore.fetchList({ status: activeTab.value || undefined, limit, offset: offset.value })
}

function loadMore() {
  offset.value += limit
  jobStore.fetchList({ status: activeTab.value || undefined, limit, offset: offset.value, append: true })
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
