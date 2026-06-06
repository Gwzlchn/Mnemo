<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { Home, ListTodo, PlusCircle, HardDrive, Settings } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()

const tabs = [
  { path: '/', label: '首页', icon: Home },
  { path: '/jobs', label: '任务', icon: ListTodo },
  { path: '/', label: '投递', icon: PlusCircle, highlight: true, action: 'submit' },
  { path: '/workers', label: 'Worker', icon: HardDrive },
  { path: '/settings', label: '设置', icon: Settings },
]

function isActive(path: string, idx: number) {
  if (idx === 2) return false
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

function handleTab(tab: typeof tabs[number]) {
  if (tab.action === 'submit') {
    if (route.path !== '/') {
      router.push('/')
    }
    setTimeout(() => {
      document.querySelector('[data-submit-form]')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }, 100)
    return
  }
  router.push(tab.path)
}
</script>

<template>
  <nav class="fixed bottom-0 left-0 right-0 z-40 bg-white border-t border-gray-200 flex justify-around py-1.5 safe-area-pb">
    <a
      v-for="(tab, idx) in tabs"
      :key="idx"
      @click.prevent="handleTab(tab)"
      class="flex flex-col items-center gap-0.5 px-2 py-1 text-xs transition-colors cursor-pointer"
      :class="[
        isActive(tab.path, idx) ? 'text-blue-600' : 'text-gray-500',
        tab.highlight ? 'text-blue-600' : ''
      ]"
    >
      <component :is="tab.icon" :size="20" :stroke-width="tab.highlight ? 2.5 : 1.5" />
      <span>{{ tab.label }}</span>
    </a>
  </nav>
</template>

<style scoped>
.safe-area-pb {
  padding-bottom: max(0.375rem, env(safe-area-inset-bottom));
}
</style>
