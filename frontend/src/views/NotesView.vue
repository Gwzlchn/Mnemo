<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useApi } from '../composables/useApi'
import MarkdownViewer from '../components/notes/MarkdownViewer.vue'
import ChapterNav from '../components/notes/ChapterNav.vue'
import { ArrowLeft, BookOpen, FileText } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const api = useApi()

const jobId = computed(() => route.params.jobId as string)
const isMechanical = computed(() => route.name === 'notes-mechanical')

const content = ref('')
const headings = ref<{ id: string; text: string; level: number }[]>([])
const loading = ref(true)
const error = ref('')
const title = ref('')

onMounted(async () => {
  try {
    const endpoint = isMechanical.value
      ? `/api/jobs/${jobId.value}/notes/mechanical`
      : `/api/jobs/${jobId.value}/notes/smart`

    const [text, detail] = await Promise.all([
      api.getText(endpoint),
      api.get<{ title: string }>(`/api/jobs/${jobId.value}`),
    ])
    content.value = text
    title.value = detail.title || jobId.value
  } catch (e: any) {
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
})

function onHeadings(h: { id: string; text: string; level: number }[]) {
  headings.value = h
}

// Mobile chapter dropdown
const showChapters = ref(false)
</script>

<template>
  <div>
    <!-- Top bar -->
    <div class="flex items-center gap-3 mb-4">
      <button @click="router.back()" class="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700">
        <ArrowLeft :size="16" />
      </button>
      <h2 class="text-lg font-bold truncate flex-1">{{ title }}</h2>
      <div class="flex items-center gap-1">
        <router-link
          :to="`/notes/${jobId}`"
          class="px-2 py-1 text-xs rounded-md transition-colors"
          :class="!isMechanical ? 'bg-blue-100 text-blue-700 font-medium' : 'text-gray-500 hover:bg-gray-100'"
        >
          <BookOpen :size="12" class="inline mr-0.5" />
          智能版
        </router-link>
        <router-link
          :to="`/notes/${jobId}/mechanical`"
          class="px-2 py-1 text-xs rounded-md transition-colors"
          :class="isMechanical ? 'bg-blue-100 text-blue-700 font-medium' : 'text-gray-500 hover:bg-gray-100'"
        >
          <FileText :size="12" class="inline mr-0.5" />
          机械版
        </router-link>
      </div>
    </div>

    <!-- Mobile chapter dropdown -->
    <div v-if="headings.length > 0" class="lg:hidden mb-3">
      <button
        @click="showChapters = !showChapters"
        class="w-full px-3 py-2 text-sm text-left bg-white border border-gray-200 rounded-lg flex items-center justify-between"
      >
        <span class="text-gray-600">章节导航 ({{ headings.length }})</span>
        <span class="text-gray-400 text-xs">{{ showChapters ? '收起' : '展开' }}</span>
      </button>
      <div v-if="showChapters" class="mt-1 bg-white border border-gray-200 rounded-lg p-3 max-h-64 overflow-y-auto">
        <ChapterNav :headings="headings" />
      </div>
    </div>

    <div v-if="loading" class="text-sm text-gray-400 py-8 text-center">加载中...</div>
    <div v-else-if="error" class="text-sm text-red-600 py-8 text-center">{{ error }}</div>

    <div v-else class="flex gap-6">
      <!-- Content -->
      <div class="flex-1 min-w-0 bg-white border border-gray-200 rounded-xl p-4 md:p-6">
        <MarkdownViewer :content="content" :job-id="jobId" @headings="onHeadings" />
      </div>
      <!-- Desktop TOC sidebar -->
      <aside class="hidden lg:block w-56 flex-shrink-0">
        <div class="sticky top-6">
          <ChapterNav :headings="headings" />
        </div>
      </aside>
    </div>
  </div>
</template>
