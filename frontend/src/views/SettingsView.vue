<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useApi } from '../composables/useApi'
import { useGlobalStore } from '../stores/global'
import BilibiliQrLogin from '../components/auth/BilibiliQrLogin.vue'
import CookieUpload from '../components/auth/CookieUpload.vue'
import StatusBadge from '../components/common/StatusBadge.vue'
import type { AuthStatus } from '../types'
import { Shield, Globe, BookOpen } from 'lucide-vue-next'

const api = useApi()
const globalStore = useGlobalStore()

const authStatus = ref<AuthStatus | null>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const [auth] = await Promise.all([
      api.get<AuthStatus>('/api/auth/status'),
      globalStore.fetchProfiles(),
    ])
    authStatus.value = auth
  } finally {
    loading.value = false
  }
})

async function refreshAuth() {
  authStatus.value = await api.get<AuthStatus>('/api/auth/status')
}
</script>

<template>
  <div class="space-y-6">
    <h2 class="text-xl font-bold">设置</h2>

    <div v-if="loading" class="text-sm text-gray-400 py-8 text-center">加载中...</div>

    <template v-else>
      <!-- Platform Auth -->
      <section class="bg-white border border-gray-200 rounded-xl p-4 space-y-4">
        <h3 class="text-sm font-semibold text-gray-700 flex items-center gap-2">
          <Shield :size="16" />
          平台认证
        </h3>

        <!-- Bilibili -->
        <div class="space-y-2">
          <div class="flex items-center gap-2">
            <span class="text-sm font-medium">B站</span>
            <StatusBadge v-if="authStatus" :status="authStatus.bilibili.has_cookies ? 'done' : 'failed'" />
            <span v-if="authStatus" class="text-xs text-gray-500">
              {{ authStatus.bilibili.has_cookies ? '已登录 (1080P 可用)' : '未登录' }}
            </span>
          </div>
          <BilibiliQrLogin @success="refreshAuth" />
        </div>

        <hr class="border-gray-100" />

        <!-- YouTube -->
        <div class="space-y-2">
          <div class="flex items-center gap-2">
            <span class="text-sm font-medium">YouTube</span>
            <StatusBadge v-if="authStatus" :status="authStatus.youtube.has_cookies ? 'done' : 'failed'" />
            <span v-if="authStatus" class="text-xs text-gray-500">
              {{ authStatus.youtube.has_cookies ? '已配置' : '未配置' }}
            </span>
          </div>
          <CookieUpload platform="youtube" @success="refreshAuth" />
        </div>
      </section>

      <!-- Profiles -->
      <section class="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
        <h3 class="text-sm font-semibold text-gray-700 flex items-center gap-2">
          <BookOpen :size="16" />
          领域 Profile
        </h3>
        <div v-if="globalStore.profiles.length === 0" class="text-sm text-gray-400">暂无 Profile</div>
        <div v-else class="space-y-2">
          <div v-for="p in globalStore.profiles" :key="p.domain" class="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
            <div>
              <span class="text-sm font-medium">{{ p.domain }}</span>
              <span v-if="p.role" class="text-xs text-gray-500 ml-2">{{ p.role }}</span>
            </div>
            <span class="text-xs text-gray-400">{{ p.terminology_count }} 个术语</span>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>
