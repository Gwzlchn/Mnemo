import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useApi } from '../composables/useApi'
import type { ProfileSummary } from '../types'

export const useGlobalStore = defineStore('global', () => {
  const api = useApi()
  const profiles = ref<ProfileSummary[]>([])
  const styleTags = ref<string[]>([])

  async function fetchProfiles() {
    profiles.value = await api.get<ProfileSummary[]>('/api/profiles')
  }

  async function fetchStyleTags() {
    try {
      styleTags.value = await api.get<string[]>('/api/config/styles')
    } catch {
      styleTags.value = ['animated', 'lecture', 'code-tutorial', 'talk', 'case-study', 'math-visual']
    }
  }

  return { profiles, styleTags, fetchProfiles, fetchStyleTags }
})
