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

          <p v-if="fallbackHint" class="settings-hint settings-hint--warn">
            {{ fallbackHint }}
          </p>

          <div class="settings-actions">
            <base-button
              variant="primary"
              :disabled="saving || !!baseUrlError"
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
import { useUserSettingsStore } from '../store/user-settings';
import type { ModelPreferences } from '../types/settings';

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
  apiKeyDraft.value = '';
  keyEditing.value = false;
};

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
  if (!ragflow || baseUrlError.value) return;

  const payload: Record<string, unknown> = {};
  const nextBaseUrl = baseUrlDraft.value.trim().replace(/\/+$/, '');
  if (nextBaseUrl !== ragflow.baseUrl) payload.baseUrl = nextBaseUrl;
  if (enabledDraft.value !== ragflow.enabled)
    payload.enabled = enabledDraft.value;
  // 四态语义：只有用户真的输入了新密钥才提交明文；空串等于"不变"
  const newKey = apiKeyDraft.value.trim();
  if (keyEditing.value && newKey) payload.apiKey = newKey;

  if (Object.keys(payload).length === 0) {
    actionMessageKind.value = 'info';
    actionMessage.value = '没有检测到改动。';
    return;
  }

  actionMessage.value = '';
  try {
    await settingsStore.saveRagflow(payload);
    syncDrafts();
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
