<script setup lang="ts">
import { ref } from 'vue'
import { setToken } from '../../composables/useApi'
import { KeyRound } from 'lucide-vue-next'

const token = ref('')
const error = ref('')
const checking = ref(false)

async function login() {
  if (!token.value.trim()) return
  error.value = ''
  checking.value = true
  try {
    const resp = await fetch('/api/health', {
      headers: { Authorization: `Bearer ${token.value.trim()}` },
    })
    if (resp.ok) {
      setToken(token.value.trim())
    } else {
      error.value = 'Token 无效'
    }
  } catch {
    error.value = '无法连接服务器'
  } finally {
    checking.value = false
  }
}
</script>

<template>
  <div class="fixed inset-0 z-50 bg-gray-900/50 flex items-center justify-center p-4">
    <div class="bg-white rounded-xl shadow-xl w-full max-w-sm p-6">
      <div class="flex items-center gap-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center">
          <KeyRound :size="20" class="text-blue-600" />
        </div>
        <div>
          <h2 class="text-lg font-bold">登录</h2>
          <p class="text-sm text-gray-500">输入 API Token</p>
        </div>
      </div>

      <form @submit.prevent="login">
        <input
          v-model="token"
          type="password"
          placeholder="API Token"
          class="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          autofocus
        />
        <p v-if="error" class="mt-2 text-sm text-red-600">{{ error }}</p>
        <button
          type="submit"
          :disabled="checking || !token.trim()"
          class="mt-4 w-full py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {{ checking ? '验证中...' : '登录' }}
        </button>
      </form>
    </div>
  </div>
</template>
