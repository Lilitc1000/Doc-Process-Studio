<template>
  <section class="settings-page">
    <div class="settings-body">
      <div class="settings-content">
        <section class="settings-section">
          <h3 class="settings-section-title">个人设置</h3>
          <p class="settings-section-desc">
            这些设置只影响你自己的账号，保存在服务端。
          </p>

          <div class="selector-group">
            <label id="settings-model-label" class="selector-label"
              >生成模型</label
            >
            <base-dropdown
              :model-value="appStore.selectedModel"
              :options="modelOptions"
              label-id="settings-model-label"
              @update:model-value="onSelectModel"
            />
          </div>

          <div class="selector-group">
            <label id="settings-reranker-label" class="selector-label"
              >重排序模型</label
            >
            <base-dropdown
              :model-value="appStore.selectedRerankerModel"
              :options="modelOptions"
              label-id="settings-reranker-label"
              @update:model-value="onSelectRerankerModel"
            />
          </div>

          <p v-if="preferenceHint" class="settings-hint">
            {{ preferenceHint }}
          </p>
        </section>

        <section v-if="isGlobalAdmin" class="settings-section">
          <h3 class="settings-section-title">RAGFlow 知识库</h3>
          <p class="settings-section-desc">
            全系统共享的连接信息与密钥。密钥加密后存入数据库，保存后立即生效，无需重启服务。
          </p>

          <div class="selector-group">
            <label id="settings-base-url-label" class="selector-label"
              >Base URL</label
            >
            <base-input
              v-model="baseUrlDraft"
              :class="{ invalid: !!baseUrlError }"
              placeholder="http://ragflow.example.com:10108"
              aria-labelledby="settings-base-url-label"
            />
            <p v-if="baseUrlError" class="field-error">{{ baseUrlError }}</p>
            <p v-else-if="baseUrlSourceHint" class="field-hint">
              {{ baseUrlSourceHint }}
            </p>
          </div>

          <div class="selector-group">
            <label id="settings-api-key-label" class="selector-label"
              >API 密钥</label
            >

            <div v-if="!keyEditing" class="secret-readonly">
              <span class="secret-mask" data-testid="secret-mask">{{
                credential.maskedApiKey
              }}</span>
              <span
                class="secret-badge"
                :class="{ 'secret-badge--ok': credential.configured }"
                >{{ credential.configured ? '已配置' : '未配置' }}</span
              >
              <base-button size="sm" @click="startEditKey">修改</base-button>
            </div>

            <div v-else class="secret-editing">
              <password-input
                v-model="apiKeyDraft"
                placeholder="粘贴新的 API Key"
                aria-labelledby="settings-api-key-label"
              />
              <base-button size="sm" @click="cancelEditKey">取消</base-button>
            </div>

            <p class="field-hint">
              <template v-if="keyEditing">
                明文只用于本次输入；服务端加密保存，之后不再回显，只会显示掩码。
              </template>
              <template v-else-if="credential.updatedAt">
                最后更新：{{ formatTime(credential.updatedAt) }}
              </template>
              <template v-else> 清空输入框不会清除已保存的密钥。 </template>
            </p>
          </div>

          <div class="selector-group selector-group--inline">
            <label id="settings-enabled-label" class="selector-label"
              >启用 RAGFlow</label
            >
            <base-switch
              v-model="enabledDraft"
              aria-labelledby="settings-enabled-label"
            />
          </div>

          <div class="selector-group">
            <div class="dataset-picker-head">
              <label id="settings-datasets-label" class="selector-label"
                >报告检索使用的知识库</label
              >
              <base-button
                size="sm"
                :disabled="datasetsLoading"
                @click="loadDatasets"
              >
                {{ datasetsLoading ? '读取中…' : '刷新列表' }}
              </base-button>
            </div>

            <p class="field-hint">
              从当前 RAGFlow 连接中选择；勾选的知识库会参与事故报告的检索增强。
              更换 Base URL 或密钥后，请保存再刷新列表。
            </p>

            <p v-if="datasetsError" class="field-error">{{ datasetsError }}</p>
            <p v-else-if="datasetsLoading" class="field-hint">
              正在读取知识库列表…
            </p>
            <p v-else-if="!datasetOptions.length" class="field-hint">
              当前连接下没有可访问的知识库。
            </p>

            <ul v-else class="dataset-list">
              <li
                v-for="ds in datasetOptions"
                :key="ds.id"
                class="dataset-item"
              >
                <label class="dataset-item-label">
                  <input
                    type="checkbox"
                    :checked="selectedDatasetIds.includes(ds.id)"
                    @change="toggleDataset(ds.id)"
                  />
                  <span class="dataset-item-name">{{ ds.name }}</span>
                  <span class="dataset-item-meta">
                    {{ ds.documentCount }} 文档 · {{ ds.chunkCount }} 片段
                  </span>
                </label>
              </li>
            </ul>

            <p v-if="missingDatasetIds.length" class="field-error">
              以下已保存的知识库在当前连接中不存在，请取消勾选或改选：
              {{ missingDatasetIds.join('、') }}
            </p>
          </div>

          <div class="settings-grid-two">
            <div class="selector-group">
              <label id="settings-threshold-label" class="selector-label"
                >相似度阈值</label
              >
              <base-input
                v-model="thresholdDraft"
                :class="{ invalid: !!thresholdError }"
                inputmode="decimal"
                aria-labelledby="settings-threshold-label"
              />
              <p v-if="thresholdError" class="field-error">
                {{ thresholdError }}
              </p>
              <p v-else class="field-hint">0.0 ~ 1.0，越高越严格</p>
            </div>

            <div class="selector-group">
              <label id="settings-topk-label" class="selector-label"
                >检索条数 topK</label
              >
              <base-input
                v-model="topKDraft"
                :class="{ invalid: !!topKError }"
                inputmode="numeric"
                aria-labelledby="settings-topk-label"
              />
              <p v-if="topKError" class="field-error">{{ topKError }}</p>
              <p v-else class="field-hint">1 ~ 20，单次注入的素材块上限</p>
            </div>
          </div>

          <p v-if="fallbackHint" class="settings-hint settings-hint--warn">
            {{ fallbackHint }}
          </p>

          <div class="settings-actions">
            <base-button
              variant="primary"
              :disabled="
                saving || !!baseUrlError || !!thresholdError || !!topKError
              "
              @click="onSave"
            >
              {{ saving ? '保存中…' : '保存' }}
            </base-button>
            <base-button :disabled="testing || saving" @click="onTest">
              {{ testing ? '测试中…' : '测试连接' }}
            </base-button>
            <base-button
              v-if="credential.configured"
              variant="danger"
              :disabled="saving"
              @click="confirmClearVisible = true"
            >
              清除密钥
            </base-button>
          </div>

          <p
            v-if="actionMessage"
            class="settings-hint"
            :class="{
              'settings-hint--warn': actionMessageKind === 'warn',
              'settings-hint--error': actionMessageKind === 'error',
            }"
          >
            {{ actionMessage }}
          </p>
        </section>

        <section v-else class="settings-section settings-section--muted">
          <h3 class="settings-section-title">RAGFlow 知识库</h3>
          <p class="settings-section-desc">
            连接信息与密钥是全系统共享的，只有管理员可以查看和修改。
          </p>
        </section>
      </div>
    </div>

    <base-confirm-dialog
      v-model="confirmClearVisible"
      title="清除 API 密钥"
      message="清除后，如果环境变量里也没有兜底密钥，知识库检索与报告参考将不可用。确定要清除吗？"
      confirm-text="清除"
      confirm-variant="danger"
      @confirm="onClearKey"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useAppStore } from '@shared/stores/app';
import { useCatalogLoader } from '@shared/composables/useCatalogLoader';
import BaseButton from '@shared/ui/BaseButton.vue';
import BaseConfirmDialog from '@shared/ui/BaseConfirmDialog.vue';
import BaseDropdown from '@shared/ui/BaseDropdown.vue';
import BaseInput from '@shared/ui/BaseInput.vue';
import BaseSwitch from '@shared/ui/BaseSwitch.vue';
import PasswordInput from '@shared/ui/PasswordInput.vue';
import { useAuthStore } from '@modules/auth';
import { fetchRagflowDatasets } from '../api/settings';
import { useUserSettingsStore } from '../store/user-settings';
import type {
  ModelPreferences,
  RagflowDatasetSummary,
} from '../types/settings';

const appStore = useAppStore();
const authStore = useAuthStore();
const settingsStore = useUserSettingsStore();
const { loadAvailableModels } = useCatalogLoader();

/**
 * 全局管理员判定。
 *
 * ⚠️ 不要用「事故报告」模块的 `useIncidentReportStore().isAdmin` ——
 * 那个是**模块级**角色（`incident_report_user_roles`），与"能否修改全系统共享设置"
 * 无关。用错会把"给某人分配报告审核人"顺带变成"能改全局密钥"。
 */
const isGlobalAdmin = computed(() => authStore.isGlobalAdmin);

const modelOptions = computed(() =>
  appStore.availableModels.map((model) => ({ label: model, value: model })),
);

const baseUrlDraft = ref('');
const enabledDraft = ref(false);
const apiKeyDraft = ref('');
const thresholdDraft = ref('0.55');
const topKDraft = ref('3');

/** 当前连接下可访问的知识库（列表随连接变化，不在前端缓存超时） */
const datasetOptions = ref<RagflowDatasetSummary[]>([]);
const datasetsLoading = ref(false);
const datasetsError = ref('');
/** 勾选中的 dataset id */
const selectedDatasetIds = ref<string[]>([]);
const keyEditing = ref(false);
const confirmClearVisible = ref(false);
/** 草稿是否已用服务端值初始化过（只做一次，避免覆盖用户编辑） */
const draftsInitialized = ref(false);

const preferenceHint = ref('');
const actionMessage = ref('');
const actionMessageKind = ref<'info' | 'warn' | 'error'>('info');

const saving = computed(() => settingsStore.saving);
const testing = computed(() => settingsStore.testing);
const credential = computed(
  () =>
    settingsStore.ragflow?.credential ?? {
      configured: false,
      maskedApiKey: '••••••••',
      hint: null,
      source: 'none' as const,
      updatedAt: null,
    },
);

const baseUrlError = computed(() => {
  const value = baseUrlDraft.value.trim();
  if (!value) return '';
  if (!/^https?:\/\//i.test(value))
    return 'Base URL 必须以 http:// 或 https:// 开头';
  if (!/^https?:\/\/[^/\s]+/i.test(value)) return 'Base URL 缺少主机名';
  return '';
});

const baseUrlSourceHint = computed(() =>
  settingsStore.ragflow?.baseUrlSource === 'env'
    ? '当前值来自环境变量兜底；保存后将改为库内配置。'
    : '',
);

const fallbackHint = computed(() => {
  const ragflow = settingsStore.ragflow;
  if (!ragflow || ragflow.credential.configured) return '';
  if (ragflow.credential.source === 'env') {
    return '当前未配置系统级密钥，正在使用环境变量中的兜底密钥。';
  }
  return '当前尚未配置任何可用密钥，知识库检索与报告参考将不可用。';
});

const formatTime = (iso: string) => {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
};

/** 把服务端保存的模型偏好应用到运行期 store（只在合法选项内采用）。 */
const applyServerPreferences = () => {
  const { models } = settingsStore.preferences;
  const available = appStore.availableModels;
  if (models.selected && available.includes(models.selected)) {
    appStore.selectedModel = models.selected;
  }
  if (models.reranker && available.includes(models.reranker)) {
    appStore.selectedRerankerModel = models.reranker;
  }
};

const syncDrafts = () => {
  const ragflow = settingsStore.ragflow;
  baseUrlDraft.value = ragflow?.baseUrl ?? '';
  enabledDraft.value = ragflow?.enabled ?? false;
  thresholdDraft.value = String(ragflow?.similarityThreshold ?? 0.55);
  topKDraft.value = String(ragflow?.topK ?? 3);
  selectedDatasetIds.value = parseHistoryDatasetIds(
    ragflow?.datasetsJson ?? '',
  );
  apiKeyDraft.value = '';
  keyEditing.value = false;
};

/**
 * 后端存的是 `{"scope": ["id", ...]}`（scope 为多域检索预留）。
 * 当前报告侧只用 `history`，因此 UI 只暴露这一组勾选，避免让管理员面对 scope 概念。
 */
const parseHistoryDatasetIds = (raw: string): string[] => {
  const text = (raw ?? '').trim();
  if (!text) return [];
  try {
    const parsed: unknown = JSON.parse(text);
    if (
      typeof parsed !== 'object' ||
      parsed === null ||
      Array.isArray(parsed)
    ) {
      return [];
    }
    const history = (parsed as Record<string, unknown>).history;
    return Array.isArray(history) ? history.map(String) : [];
  } catch {
    return [];
  }
};

const buildDatasetsJson = (ids: string[]): string =>
  ids.length ? JSON.stringify({ history: ids }) : '';

/** 已保存但当前连接里查不到的 dataset（换连接后最容易出现） */
const missingDatasetIds = computed(() => {
  if (!datasetOptions.value.length) return [];
  const known = new Set(datasetOptions.value.map((ds) => ds.id));
  return selectedDatasetIds.value.filter((id) => !known.has(id));
});

const loadDatasets = async () => {
  datasetsLoading.value = true;
  datasetsError.value = '';
  try {
    const result = await fetchRagflowDatasets();
    datasetOptions.value = result.datasets;
    if (!result.ok) datasetsError.value = result.message;
  } catch {
    datasetOptions.value = [];
    datasetsError.value = '读取知识库列表失败，请检查连接配置或稍后重试。';
  } finally {
    datasetsLoading.value = false;
  }
};

const toggleDataset = (id: string) => {
  const index = selectedDatasetIds.value.indexOf(id);
  if (index >= 0) {
    selectedDatasetIds.value = selectedDatasetIds.value.filter(
      (item) => item !== id,
    );
  } else {
    selectedDatasetIds.value = [...selectedDatasetIds.value, id];
  }
};

const thresholdError = computed(() => {
  const raw = thresholdDraft.value.trim();
  if (!raw) return '不能为空';
  const value = Number(raw);
  if (!Number.isFinite(value) || value < 0 || value > 1)
    return '需为 0.0 ~ 1.0';
  return '';
});

const topKError = computed(() => {
  const raw = topKDraft.value.trim();
  if (!raw) return '不能为空';
  const value = Number(raw);
  if (!Number.isInteger(value) || value < 1 || value > 20) return '需为 1 ~ 20';
  return '';
});

const startEditKey = () => {
  // 刻意不回填掩码：掩码不是密钥，回填会让用户误以为可以直接保存
  apiKeyDraft.value = '';
  keyEditing.value = true;
  actionMessage.value = '';
};

const cancelEditKey = () => {
  apiKeyDraft.value = '';
  keyEditing.value = false;
};

const onSelectModel = async (model: string) => {
  appStore.selectedModel = model;
  const patch: Partial<ModelPreferences> = { selected: model };
  if (!appStore.availableModels.includes(appStore.selectedRerankerModel)) {
    appStore.selectedRerankerModel = model;
    patch.reranker = model;
  }
  await persistPreferences(patch);
};

const onSelectRerankerModel = async (model: string) => {
  appStore.selectedRerankerModel = model;
  await persistPreferences({ reranker: model });
};

const persistPreferences = async (patch: Partial<ModelPreferences>) => {
  preferenceHint.value = '';
  try {
    await settingsStore.saveModelPreferences(patch);
    preferenceHint.value = '已保存到你的账号';
  } catch {
    preferenceHint.value = '保存失败，请稍后重试';
  }
};

const onSave = async () => {
  const ragflow = settingsStore.ragflow;
  if (
    !ragflow ||
    baseUrlError.value ||
    thresholdError.value ||
    topKError.value
  ) {
    return;
  }

  const payload: Record<string, unknown> = {};
  const nextBaseUrl = baseUrlDraft.value.trim().replace(/\/+$/, '');
  if (nextBaseUrl !== ragflow.baseUrl) payload.baseUrl = nextBaseUrl;
  if (enabledDraft.value !== ragflow.enabled)
    payload.enabled = enabledDraft.value;
  // 四态语义：只有用户真的输入了新密钥才提交明文；空串等于"不变"
  const newKey = apiKeyDraft.value.trim();
  if (keyEditing.value && newKey) payload.apiKey = newKey;

  // 检索参数：只在有改动时提交，空串表示撤销库内覆盖
  const nextDatasets = buildDatasetsJson(selectedDatasetIds.value);
  if (nextDatasets !== (ragflow.datasetsJson ?? '').trim())
    payload.datasetsJson = nextDatasets;
  const nextThreshold = Number(thresholdDraft.value);
  if (nextThreshold !== ragflow.similarityThreshold)
    payload.similarityThreshold = nextThreshold;
  const nextTopK = Number(topKDraft.value);
  if (nextTopK !== ragflow.topK) payload.topK = nextTopK;

  if (Object.keys(payload).length === 0) {
    actionMessageKind.value = 'info';
    actionMessage.value = '没有检测到改动。';
    return;
  }

  actionMessage.value = '';
  try {
    await settingsStore.saveRagflow(payload);
    syncDrafts();
    // 连接配置可能刚被改过，列表要跟着换成新连接下的知识库
    if (isGlobalAdmin.value) void loadDatasets();
    actionMessageKind.value = 'info';
    actionMessage.value = '已保存，立即生效。';
  } catch {
    actionMessageKind.value = 'error';
    actionMessage.value =
      '保存失败。请确认 Base URL 与密钥是否正确，或联系系统管理员。';
  }
};

const onTest = async () => {
  actionMessage.value = '';
  try {
    const result = await settingsStore.runConnectionTest();
    actionMessageKind.value = result.ok ? 'info' : 'warn';
    actionMessage.value = result.message;
  } catch {
    actionMessageKind.value = 'error';
    actionMessage.value = '测试连接失败，请检查网络或密钥权限。';
  }
};

const onClearKey = async () => {
  actionMessage.value = '';
  try {
    await settingsStore.removeApiKey();
    syncDrafts();
    actionMessageKind.value = 'info';
    actionMessage.value = '已清除系统级密钥。';
  } catch {
    actionMessageKind.value = 'error';
    actionMessage.value = '清除失败，请稍后重试。';
  }
};

watch(
  // 只在**首次加载成功**时把服务端值灌进草稿区。
  //
  // 不要监听 `settingsStore.ragflow` 本身：`ragflow` 是服务端状态的镜像，任何一次
  // 重新加载都会换掉它的引用，从而把用户此刻正在编辑的 Base URL / 密钥草稿、
  // 以及刚拨动的开关一并重置回去（"我点了它自己变回来"就是这么来的）。
  // 之后的草稿变化只应该由用户操作或保存成功后的显式同步触发。
  () => settingsStore.loaded,
  (isLoaded) => {
    if (isLoaded && !draftsInitialized.value) {
      syncDrafts();
      draftsInitialized.value = true;
      // 只有管理员能读知识库列表（非管理员会拿到 403，静默跳过即可）
      if (isGlobalAdmin.value) void loadDatasets();
    }
  },
  { immediate: true },
);

onMounted(async () => {
  await loadAvailableModels();
  await settingsStore.loadSettings();
  applyServerPreferences();
});
</script>

<style scoped src="./styles/settings-page.css"></style>
