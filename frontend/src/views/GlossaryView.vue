<script setup lang="ts">
import { ref, computed, onMounted, inject } from 'vue'
import { useApi } from '../composables/useApi'
import { useGlobalStore } from '../stores/global'
import type { GlossaryTerm } from '../types'
import { BookA, Plus, Check, Trash2, Pencil, X } from 'lucide-vue-next'
import Card from '../components/common/Card.vue'
import LoadingState from '../components/common/LoadingState.vue'
import PrimaryButton from '../components/common/PrimaryButton.vue'
import Modal from '../components/common/Modal.vue'
import ConfirmDialog from '../components/common/ConfirmDialog.vue'

const api = useApi()
const globalStore = useGlobalStore()
const showToast = inject<(m: string, t?: 'success' | 'error' | 'info') => void>('showToast')

const loading = ref(true)
const terms = ref<GlossaryTerm[]>([])
const selectedDomain = ref<string>('')

// 域选项：合并 Profile 列表与现有术语里出现过的 domain，去重排序。
const domains = computed(() => {
  const set = new Set<string>()
  globalStore.profiles.forEach((p) => set.add(p.domain))
  terms.value.forEach((t) => set.add(t.domain))
  return [...set].sort()
})

const suggested = computed(() => terms.value.filter((t) => t.status === 'suggested'))
const accepted = computed(() => terms.value.filter((t) => t.status === 'accepted'))

async function loadTerms() {
  loading.value = true
  try {
    const q = selectedDomain.value ? `?domain=${encodeURIComponent(selectedDomain.value)}` : ''
    terms.value = await api.get<GlossaryTerm[]>(`/api/glossary${q}`)
  } catch (e) {
    showToast?.('加载术语失败', 'error')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await globalStore.fetchProfiles()
  await loadTerms()
})

function onDomainChange() {
  loadTerms()
}

// ── 采纳 / 忽略候选 ──

async function acceptTerm(t: GlossaryTerm) {
  try {
    await api.post(`/api/glossary/${encodeURIComponent(t.domain)}/${encodeURIComponent(t.term)}/accept`)
    showToast?.('已采纳，写入 Profile', 'success')
    await loadTerms()
  } catch (e) {
    showToast?.('采纳失败', 'error')
  }
}

// 待删确认目标：非空即弹 ConfirmDialog（替代原生 confirm）。
const removing = ref<GlossaryTerm | null>(null)

async function deleteTerm(t: GlossaryTerm, ignore = false) {
  try {
    await api.del(`/api/glossary/${encodeURIComponent(t.domain)}/${encodeURIComponent(t.term)}`)
    showToast?.(ignore ? '已忽略' : '已删除', 'success')
    await loadTerms()
  } catch (e) {
    showToast?.('操作失败', 'error')
  }
}

async function confirmRemove() {
  const t = removing.value
  if (!t) return
  removing.value = null
  await deleteTerm(t)
}

// ── 手动新增 ──

const showAdd = ref(false)
const addDomain = ref('')
const addTerm = ref('')
const addDefinition = ref('')
const saving = ref(false)

function openAdd() {
  addDomain.value = selectedDomain.value || domains.value[0] || ''
  addTerm.value = ''
  addDefinition.value = ''
  showAdd.value = true
}

async function submitAdd() {
  const domain = addDomain.value.trim()
  const term = addTerm.value.trim()
  if (!domain || !term) {
    showToast?.('域和术语不能为空', 'error')
    return
  }
  saving.value = true
  try {
    await api.post(`/api/glossary?domain=${encodeURIComponent(domain)}`, {
      term,
      definition: addDefinition.value.trim() || null,
    })
    showToast?.('术语已添加', 'success')
    showAdd.value = false
    if (selectedDomain.value && selectedDomain.value !== domain) {
      selectedDomain.value = domain
    }
    await loadTerms()
  } catch (e) {
    showToast?.('添加失败', 'error')
  } finally {
    saving.value = false
  }
}

// ── 编辑已采纳条目 ──

const editing = ref<GlossaryTerm | null>(null)
const editDefinition = ref('')
const editRelated = ref('')

function openEdit(t: GlossaryTerm) {
  editing.value = t
  editDefinition.value = t.definition
  editRelated.value = t.related.join(', ')
}

async function submitEdit() {
  if (!editing.value) return
  const t = editing.value
  const related = editRelated.value.split(',').map((s) => s.trim()).filter(Boolean)
  saving.value = true
  try {
    await api.put(`/api/glossary/${encodeURIComponent(t.domain)}/${encodeURIComponent(t.term)}`, {
      term: t.term,
      definition: editDefinition.value.trim() || null,
      related,
    })
    showToast?.('已保存', 'success')
    editing.value = null
    await loadTerms()
  } catch (e) {
    showToast?.('保存失败', 'error')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between gap-3">
      <h1 class="text-xl font-bold text-gray-800 flex items-center gap-2">
        <BookA :size="20" />
        术语
      </h1>
      <div class="flex items-center gap-2">
        <select
          v-model="selectedDomain"
          @change="onDomainChange"
          class="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
        >
          <option value="">全部域</option>
          <option v-for="d in domains" :key="d" :value="d">{{ d }}</option>
        </select>
        <button
          @click="openAdd"
          class="flex items-center gap-1 px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
        >
          <Plus :size="16" />
          新增
        </button>
      </div>
    </div>

    <LoadingState v-if="loading" />

    <template v-else>
      <!-- 待审建议（来自 review 采集） -->
      <Card v-if="suggested.length > 0" padding="p-4 space-y-3">
        <h2 class="text-sm font-semibold text-gray-700">
          待审建议
          <span class="text-xs text-gray-500 font-normal">（{{ suggested.length }}，来自评审）</span>
        </h2>
        <div class="space-y-2">
          <div
            v-for="t in suggested"
            :key="`${t.domain}/${t.term}`"
            class="flex items-center gap-3 py-2 px-3 bg-amber-50 rounded-lg"
          >
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <span class="text-sm font-medium text-gray-800 break-all">{{ t.term }}</span>
                <span class="text-xs text-gray-500">{{ t.domain }}</span>
              </div>
              <div class="text-xs text-gray-500 mt-0.5">出现于 {{ t.occurrences.length }} 篇内容</div>
            </div>
            <button
              @click="acceptTerm(t)"
              class="flex items-center gap-1 px-2.5 py-1 bg-green-50 text-green-700 text-xs rounded-md hover:bg-green-100"
            >
              <Check :size="14" />
              采纳
            </button>
            <button
              @click="deleteTerm(t, true)"
              class="flex items-center gap-1 px-2.5 py-1 text-gray-500 text-xs rounded-md hover:bg-gray-100"
            >
              <X :size="14" />
              忽略
            </button>
          </div>
        </div>
      </Card>

      <!-- 已采纳（可编辑/删除） -->
      <Card padding="p-4 space-y-3">
        <h2 class="text-sm font-semibold text-gray-700">
          已采纳
          <span class="text-xs text-gray-500 font-normal">（{{ accepted.length }}）</span>
        </h2>
        <div v-if="accepted.length === 0" class="text-sm text-gray-500 py-4 text-center">暂无已采纳术语</div>
        <div v-else class="space-y-1.5">
          <div
            v-for="t in accepted"
            :key="`${t.domain}/${t.term}`"
            class="flex items-start gap-3 py-2 px-3 border-b border-gray-50 last:border-0"
          >
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <span class="text-sm font-medium text-gray-800 break-all">{{ t.term }}</span>
                <span class="text-xs text-gray-500">{{ t.domain }}</span>
              </div>
              <div v-if="t.definition" class="text-xs text-gray-600 mt-0.5 break-all">{{ t.definition }}</div>
              <div v-if="t.related.length > 0" class="text-xs text-gray-500 mt-0.5">
                关联：{{ t.related.join('、') }}
              </div>
            </div>
            <button @click="openEdit(t)" class="p-1 text-gray-500 hover:text-blue-600">
              <Pencil :size="15" />
            </button>
            <button @click="removing = t" class="p-1 text-gray-500 hover:text-red-500">
              <Trash2 :size="15" />
            </button>
          </div>
        </div>
      </Card>
    </template>

    <!-- 新增弹窗 -->
    <Modal :open="showAdd" title="新增术语" @close="showAdd = false">
      <div class="space-y-4">
        <div>
          <label class="block text-xs font-medium text-gray-500 mb-1">域（domain）</label>
          <input
            v-model="addDomain"
            type="text"
            list="glossary-domains"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
            placeholder="如：ml"
          />
          <datalist id="glossary-domains">
            <option v-for="d in domains" :key="d" :value="d" />
          </datalist>
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-500 mb-1">术语</label>
          <input
            v-model="addTerm"
            type="text"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
            placeholder="如：梯度下降"
          />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-500 mb-1">定义（可选）</label>
          <textarea
            v-model="addDefinition"
            rows="2"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
            placeholder="一句话解释"
          />
        </div>
      </div>
      <template #footer>
        <button @click="showAdd = false" class="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">取消</button>
        <PrimaryButton :loading="saving" @click="submitAdd">{{ saving ? '保存中...' : '添加' }}</PrimaryButton>
      </template>
    </Modal>

    <!-- 编辑弹窗 -->
    <Modal :open="!!editing" :title="editing ? `编辑 · ${editing.term}` : '编辑'" @close="editing = null">
      <div class="space-y-4">
        <div>
          <label class="block text-xs font-medium text-gray-500 mb-1">定义</label>
          <textarea
            v-model="editDefinition"
            rows="2"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
          />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-500 mb-1">关联术语（逗号分隔）</label>
          <input
            v-model="editRelated"
            type="text"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
            placeholder="如：反向传播, 学习率"
          />
        </div>
      </div>
      <template #footer>
        <button @click="editing = null" class="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">取消</button>
        <PrimaryButton :loading="saving" @click="submitEdit">{{ saving ? '保存中...' : '保存' }}</PrimaryButton>
      </template>
    </Modal>

    <!-- 删除确认 -->
    <ConfirmDialog
      v-if="removing"
      title="删除术语"
      :message="`删除术语「${removing.term}」？`"
      confirm-text="删除"
      :danger="true"
      @confirm="confirmRemove"
      @cancel="removing = null"
    />
  </div>
</template>
