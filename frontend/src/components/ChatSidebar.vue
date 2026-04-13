<template>
  <aside class="chat-sidebar">
    <div class="sidebar-header">
      <h2>文档处理助手</h2>
      <button
        class="clear-btn"
        :disabled="props.isLocked"
        @click="$emit('clear-chat')"
      >
        新建对话
      </button>
    </div>

    <div class="sidebar-content">
      <section class="history-section">
        <div
          v-for="group in sessionGroups"
          :key="group.id"
          class="history-group"
        >
          <div class="history-group-title">{{ group.label }}</div>
          <div class="history-group-list">
            <div
              v-for="session in group.sessions"
              :key="session.id"
              class="history-session"
              :class="{
                active: session.id === props.activeSessionId,
                'menu-open': openSessionMenuId === session.id,
              }"
            >
              <button
                type="button"
                class="history-session-main"
                :disabled="props.isLocked"
                @click="$emit('load-session', session.id)"
              >
                <span class="history-session-title" :title="session.title">
                  {{ session.title }}
                </span>
              </button>

              <button
                type="button"
                class="session-more-btn"
                :class="{ visible: openSessionMenuId === session.id }"
                title="更多操作"
                :disabled="props.isLocked"
                @click.stop="toggleSessionMenu(session.id)"
              >
                <svg
                  viewBox="0 0 16 16"
                  class="session-more-icon"
                  aria-hidden="true"
                >
                  <circle cx="3.5" cy="8" r="1.1" fill="currentColor" />
                  <circle cx="8" cy="8" r="1.1" fill="currentColor" />
                  <circle cx="12.5" cy="8" r="1.1" fill="currentColor" />
                </svg>
              </button>

              <Transition name="menu-fade">
                <div
                  v-if="openSessionMenuId === session.id"
                  class="history-session-menu"
                >
                  <button
                    type="button"
                    class="history-session-menu-item"
                    @click.stop="openRenameDialog(session)"
                  >
                    编辑标题
                  </button>
                  <button
                    type="button"
                    class="history-session-menu-item is-danger"
                    @click.stop="deleteSession(session.id)"
                  >
                    删除
                  </button>
                </div>
              </Transition>
            </div>
          </div>
        </div>
      </section>

      <section class="settings-section">
        <div ref="modelSelectorRef" class="selector-group">
          <label id="model-select-label">聊天模型</label>
          <button
            type="button"
            class="selector-trigger"
            :class="{ open: isModelDropdownOpen }"
            :aria-expanded="isModelDropdownOpen"
            aria-haspopup="listbox"
            aria-labelledby="model-select-label"
            :disabled="props.isLocked"
            @click="toggleModelDropdown"
            @keydown.enter.prevent="toggleModelDropdown"
            @keydown.space.prevent="toggleModelDropdown"
            @keydown.esc.prevent="closeAllDropdowns"
          >
            <span class="selector-trigger-text">{{ selectedModel }}</span>
            <span class="selector-trigger-icon" aria-hidden="true">
              <svg viewBox="0 0 16 16" class="selector-trigger-icon-svg">
                <path
                  d="M3.5 6.25L8 10.75L12.5 6.25"
                  fill="none"
                  stroke="currentColor"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                />
              </svg>
            </span>
          </button>

          <Transition name="dropdown">
            <div
              v-if="isModelDropdownOpen"
              class="selector-dropdown"
              role="listbox"
              aria-labelledby="model-select-label"
            >
              <button
                v-for="model in models"
                :key="model"
                type="button"
                class="selector-option"
                :class="{ active: model === selectedModel }"
                :disabled="props.isLocked"
                @click="onSelectModel(model)"
              >
                <span>{{ model }}</span>
                <span
                  v-if="model === selectedModel"
                  class="selector-option-tag"
                >
                  当前
                </span>
              </button>
            </div>
          </Transition>
        </div>

        <div ref="rerankerSelectorRef" class="selector-group">
          <label id="reranker-select-label">重排序模型</label>
          <button
            type="button"
            class="selector-trigger"
            :class="{ open: isRerankerDropdownOpen }"
            :aria-expanded="isRerankerDropdownOpen"
            aria-haspopup="listbox"
            aria-labelledby="reranker-select-label"
            :disabled="props.isLocked"
            @click="toggleRerankerDropdown"
            @keydown.enter.prevent="toggleRerankerDropdown"
            @keydown.space.prevent="toggleRerankerDropdown"
            @keydown.esc.prevent="closeAllDropdowns"
          >
            <span class="selector-trigger-text">{{
              selectedRerankerModel
            }}</span>
            <span class="selector-trigger-icon" aria-hidden="true">
              <svg viewBox="0 0 16 16" class="selector-trigger-icon-svg">
                <path
                  d="M3.5 6.25L8 10.75L12.5 6.25"
                  fill="none"
                  stroke="currentColor"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                />
              </svg>
            </span>
          </button>

          <Transition name="dropdown">
            <div
              v-if="isRerankerDropdownOpen"
              class="selector-dropdown"
              role="listbox"
              aria-labelledby="reranker-select-label"
            >
              <button
                v-for="model in models"
                :key="`reranker-${model}`"
                type="button"
                class="selector-option"
                :class="{ active: model === selectedRerankerModel }"
                :disabled="props.isLocked"
                @click="onSelectRerankerModel(model)"
              >
                <span>{{ model }}</span>
                <span
                  v-if="model === selectedRerankerModel"
                  class="selector-option-tag"
                >
                  当前
                </span>
              </button>
            </div>
          </Transition>
        </div>
      </section>
    </div>

    <Teleport to="body">
      <Transition name="dialog-fade">
        <div
          v-if="renameDialogSession"
          class="dialog-mask"
          @click.self="closeRenameDialog"
        >
          <div class="rename-dialog">
            <div class="rename-dialog-header">
              <h3>修改名称</h3>
              <button
                type="button"
                class="rename-dialog-close"
                @click="closeRenameDialog"
              >
                <svg
                  viewBox="0 0 16 16"
                  class="rename-dialog-close-icon"
                  aria-hidden="true"
                >
                  <path
                    d="M4 4L12 12M12 4L4 12"
                    fill="none"
                    stroke="currentColor"
                    stroke-linecap="round"
                    stroke-width="1.8"
                  />
                </svg>
              </button>
            </div>

            <textarea
              v-model="renameInput"
              class="rename-dialog-input"
              rows="3"
              placeholder="请输入新的对话名称"
            ></textarea>

            <div class="rename-dialog-actions">
              <button
                type="button"
                class="dialog-btn is-secondary"
                @click="closeRenameDialog"
              >
                取消
              </button>
              <button
                type="button"
                class="dialog-btn is-primary"
                :disabled="renameInput.trim().length === 0"
                @click="confirmRename"
              >
                确定
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </aside>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import type { ChatSessionSummary, SessionGroup } from '../types/session';
import { groupSessionsByDate } from '../utils/session-groups';

const props = defineProps<{
  models: readonly string[];
  selectedModel: string;
  selectedRerankerModel: string;
  sessions: readonly ChatSessionSummary[];
  activeSessionId: string | null;
  isLocked?: boolean;
}>();

const emit = defineEmits<{
  (e: 'select-model', model: string): void;
  (e: 'select-reranker-model', model: string): void;
  (e: 'clear-chat'): void;
  (e: 'load-session', sessionId: string): void;
  (e: 'rename-session', payload: { sessionId: string; title: string }): void;
  (e: 'delete-session', sessionId: string): void;
}>();

const isModelDropdownOpen = ref(false);
const isRerankerDropdownOpen = ref(false);
const openSessionMenuId = ref<string | null>(null);
const renameDialogSession = ref<ChatSessionSummary | null>(null);
const renameInput = ref('');
const modelSelectorRef = ref<HTMLElement | null>(null);
const rerankerSelectorRef = ref<HTMLElement | null>(null);

const sessionGroups = computed<SessionGroup[]>(() => {
  return groupSessionsByDate(props.sessions);
});

const closeAllDropdowns = () => {
  isModelDropdownOpen.value = false;
  isRerankerDropdownOpen.value = false;
};

const closeSessionMenu = () => {
  openSessionMenuId.value = null;
};

const closeRenameDialog = () => {
  renameDialogSession.value = null;
  renameInput.value = '';
};

const toggleModelDropdown = () => {
  if (props.isLocked) {
    return;
  }
  isModelDropdownOpen.value = !isModelDropdownOpen.value;
  if (isModelDropdownOpen.value) {
    closeSessionMenu();
  }
};

const toggleRerankerDropdown = () => {
  if (props.isLocked) {
    return;
  }
  isRerankerDropdownOpen.value = !isRerankerDropdownOpen.value;
  if (isRerankerDropdownOpen.value) {
    closeSessionMenu();
    isModelDropdownOpen.value = false;
  }
};

const toggleSessionMenu = (sessionId: string) => {
  if (props.isLocked) {
    return;
  }
  openSessionMenuId.value =
    openSessionMenuId.value === sessionId ? null : sessionId;
  closeAllDropdowns();
};

const openRenameDialog = (session: ChatSessionSummary) => {
  renameDialogSession.value = session;
  renameInput.value = session.title;
  closeSessionMenu();
};

const confirmRename = () => {
  if (!renameDialogSession.value || renameInput.value.trim().length === 0) {
    return;
  }

  emit('rename-session', {
    sessionId: renameDialogSession.value.id,
    title: renameInput.value.trim(),
  });
  closeRenameDialog();
};

const deleteSession = (sessionId: string) => {
  emit('delete-session', sessionId);
  closeSessionMenu();
};

const onSelectModel = (model: string) => {
  if (props.isLocked) {
    return;
  }
  emit('select-model', model);
  closeAllDropdowns();
};

const onSelectRerankerModel = (model: string) => {
  if (props.isLocked) {
    return;
  }
  emit('select-reranker-model', model);
  closeAllDropdowns();
};

const handleClickOutside = (event: MouseEvent) => {
  const target = event.target as HTMLElement | null;

  if (target && !modelSelectorRef.value?.contains(target)) {
    isModelDropdownOpen.value = false;
  }

  if (target && !rerankerSelectorRef.value?.contains(target)) {
    isRerankerDropdownOpen.value = false;
  }

  if (
    target &&
    !target.closest('.history-session-menu') &&
    !target.closest('.session-more-btn')
  ) {
    closeSessionMenu();
  }
};

const handleWindowBlur = () => {
  closeAllDropdowns();
  closeSessionMenu();
};

onMounted(() => {
  document.addEventListener('click', handleClickOutside);
  window.addEventListener('blur', handleWindowBlur);
});

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside);
  window.removeEventListener('blur', handleWindowBlur);
});

watch(
  () => props.isLocked,
  (isLocked) => {
    if (isLocked) {
      closeAllDropdowns();
      closeSessionMenu();
    }
  },
);

watch(
  () => props.activeSessionId,
  () => {
    closeSessionMenu();
  },
);
</script>

<style scoped src="../styles/components/chat-sidebar.css"></style>
