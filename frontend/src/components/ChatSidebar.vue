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
        <div ref="processingModeSelectorRef" class="selector-group">
          <label id="processing-mode-label">文档处理方式</label>
          <button
            type="button"
            class="selector-trigger"
            :class="{ open: isProcessingModeOpen }"
            :aria-expanded="isProcessingModeOpen"
            aria-haspopup="listbox"
            aria-labelledby="processing-mode-label"
            :disabled="props.isLocked"
            @click="toggleProcessingModeDropdown"
            @keydown.enter.prevent="toggleProcessingModeDropdown"
            @keydown.space.prevent="toggleProcessingModeDropdown"
            @keydown.esc.prevent="closeAllDropdowns"
          >
            <span class="selector-trigger-text">
              {{ selectedProcessingModeLabel }}
            </span>
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
              v-if="isProcessingModeOpen"
              class="selector-dropdown"
              role="listbox"
              aria-labelledby="processing-mode-label"
            >
              <button
                v-for="mode in processingModes"
                :key="mode.id"
                type="button"
                class="selector-option"
                :class="{ active: mode.id === selectedProcessingMode }"
                :disabled="props.isLocked"
                @click="onSelectProcessingMode(mode)"
              >
                <span>{{ mode.displayName }}</span>
                <span
                  v-if="mode.id === selectedProcessingMode"
                  class="selector-option-tag"
                >
                  当前
                </span>
              </button>
            </div>
          </Transition>
        </div>

        <div ref="modelSelectorRef" class="selector-group">
          <label id="model-select-label">选择模型</label>
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
      </section>
    </div>

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
  </aside>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';

interface SkillOption {
  id: string;
  displayName: string;
}

interface ChatSessionSummary {
  id: string;
  title: string;
  updated_at: string;
}

interface SessionGroup {
  id: string;
  label: string;
  sessions: ChatSessionSummary[];
}

const props = defineProps<{
  processingModes: readonly SkillOption[];
  selectedProcessingMode: string;
  models: readonly string[];
  selectedModel: string;
  messagesCount: number;
  sessions: readonly ChatSessionSummary[];
  activeSessionId: string | null;
  isLocked?: boolean;
}>();

const emit = defineEmits<{
  (e: 'select-processing-mode', mode: string): void;
  (e: 'select-model', model: string): void;
  (e: 'clear-chat'): void;
  (e: 'load-session', sessionId: string): void;
  (e: 'rename-session', payload: { sessionId: string; title: string }): void;
  (e: 'delete-session', sessionId: string): void;
}>();

const isProcessingModeOpen = ref(false);
const isModelDropdownOpen = ref(false);
const openSessionMenuId = ref<string | null>(null);
const renameDialogSession = ref<ChatSessionSummary | null>(null);
const renameInput = ref('');
const processingModeSelectorRef = ref<HTMLElement | null>(null);
const modelSelectorRef = ref<HTMLElement | null>(null);

const selectedProcessingModeLabel = computed(() => {
  const selectedOption = props.processingModes.find((mode) => {
    return mode.id === props.selectedProcessingMode;
  });
  return selectedOption?.displayName ?? props.selectedProcessingMode;
});

const sessionGroups = computed<SessionGroup[]>(() => {
  const now = Date.now();
  const recentThreshold = now - 30 * 24 * 60 * 60 * 1000;
  const groups: SessionGroup[] = [];
  const recentSessions: ChatSessionSummary[] = [];
  const olderGroups = new Map<string, SessionGroup>();

  for (const session of props.sessions) {
    const updatedAt = new Date(session.updated_at).getTime();
    if (!Number.isFinite(updatedAt) || updatedAt >= recentThreshold) {
      recentSessions.push(session);
      continue;
    }

    const date = new Date(updatedAt);
    const groupId = `${date.getFullYear()}-${date.getMonth() + 1}`;
    const existingGroup = olderGroups.get(groupId);
    if (existingGroup) {
      existingGroup.sessions.push(session);
      continue;
    }

    olderGroups.set(groupId, {
      id: groupId,
      label: `${date.getFullYear()}年${date.getMonth() + 1}月`,
      sessions: [session],
    });
  }

  if (recentSessions.length > 0) {
    groups.push({
      id: 'recent',
      label: '最近',
      sessions: recentSessions,
    });
  }

  return groups.concat(Array.from(olderGroups.values()));
});

const closeAllDropdowns = () => {
  isProcessingModeOpen.value = false;
  isModelDropdownOpen.value = false;
};

const closeSessionMenu = () => {
  openSessionMenuId.value = null;
};

const closeRenameDialog = () => {
  renameDialogSession.value = null;
  renameInput.value = '';
};

const toggleProcessingModeDropdown = () => {
  if (props.isLocked) {
    return;
  }
  isProcessingModeOpen.value = !isProcessingModeOpen.value;
  if (isProcessingModeOpen.value) {
    isModelDropdownOpen.value = false;
    closeSessionMenu();
  }
};

const toggleModelDropdown = () => {
  if (props.isLocked) {
    return;
  }
  isModelDropdownOpen.value = !isModelDropdownOpen.value;
  if (isModelDropdownOpen.value) {
    isProcessingModeOpen.value = false;
    closeSessionMenu();
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

const onSelectProcessingMode = (mode: SkillOption) => {
  if (props.isLocked) {
    return;
  }
  emit('select-processing-mode', mode.id);
  closeAllDropdowns();
};

const onSelectModel = (model: string) => {
  if (props.isLocked) {
    return;
  }
  emit('select-model', model);
  closeAllDropdowns();
};

const handleClickOutside = (event: MouseEvent) => {
  const target = event.target as HTMLElement | null;

  if (
    target &&
    !processingModeSelectorRef.value?.contains(target) &&
    !modelSelectorRef.value?.contains(target)
  ) {
    closeAllDropdowns();
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

<style scoped>
.chat-sidebar {
  width: 300px;
  background: linear-gradient(
    180deg,
    rgba(248, 250, 252, 0.98),
    rgba(255, 255, 255, 0.94)
  );
  color: #0f172a;
  display: flex;
  flex-direction: column;
  min-height: 0;
  border-right: 1px solid #e2e8f0;
  backdrop-filter: blur(14px);
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.8rem;
  padding: 1.25rem 1.15rem 0.95rem;
  border-bottom: 1px solid #e2e8f0;
}

.sidebar-header h2 {
  margin: 0;
  font-size: 1.02rem;
  font-weight: 700;
  color: #0f172a;
}

.sidebar-content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 1rem 0.95rem 1.1rem;
}

.history-section,
.settings-section {
  display: flex;
  flex-direction: column;
}

.settings-section {
  margin-top: 1.2rem;
  margin-inline: -0.95rem;
  padding-top: 1.2rem;
  padding-inline: 0.95rem;
  border-top: 1px solid #e2e8f0;
}

.history-group-title {
  margin-bottom: 0.7rem;
  font-size: 0.78rem;
  font-weight: 700;
  color: #64748b;
  letter-spacing: 0.04em;
}

.history-group + .history-group {
  margin-top: 1.1rem;
}

.history-group-list {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.history-session {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.35rem;
  min-width: 0;
  padding: 0.16rem;
  border-radius: 16px;
  transition:
    background-color 0.22s ease,
    box-shadow 0.22s ease,
    transform 0.22s ease;
}

.history-session.active {
  background: linear-gradient(
    135deg,
    rgba(219, 234, 254, 0.88),
    rgba(239, 246, 255, 0.96)
  );
  box-shadow:
    inset 0 0 0 1px rgba(59, 130, 246, 0.2),
    0 12px 24px rgba(37, 99, 235, 0.12);
  transform: translateX(2px);
}

.history-session-main {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  padding: 0.72rem 0.8rem;
  border: none;
  border-radius: 12px;
  background: transparent;
  color: #0f172a;
  cursor: pointer;
  text-align: left;
  transition:
    background-color 0.2s ease,
    color 0.2s ease;
}

.history-session-main:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.76);
}

.history-session-main:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.history-session.active .history-session-main {
  background: transparent;
  color: #0f3c9d;
}

.history-session-title {
  display: block;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.86rem;
  font-weight: 500;
  transition:
    color 0.2s ease,
    font-weight 0.2s ease;
}

.history-session.active .history-session-title {
  color: #0f3c9d;
  font-weight: 700;
}

.session-more-btn {
  width: 2rem;
  height: 2rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: none;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  color: #64748b;
  cursor: pointer;
  opacity: 0;
  box-shadow: 0 8px 16px rgba(15, 23, 42, 0.08);
  transition:
    opacity 0.18s ease,
    background-color 0.18s ease,
    color 0.18s ease;
}

.history-session:hover .session-more-btn,
.history-session.menu-open .session-more-btn,
.session-more-btn.visible {
  opacity: 1;
}

.history-session.active .session-more-btn {
  background: rgba(255, 255, 255, 0.96);
  color: #2563eb;
}

.session-more-btn:hover:not(:disabled) {
  background: #eff6ff;
  color: #2563eb;
}

.session-more-btn:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.session-more-icon {
  width: 0.95rem;
  height: 0.95rem;
}

.history-session-menu {
  position: absolute;
  top: calc(100% + 0.2rem);
  right: 0.1rem;
  z-index: 30;
  min-width: 8.2rem;
  padding: 0.35rem;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.14);
}

.history-session-menu-item {
  width: 100%;
  display: flex;
  align-items: center;
  padding: 0.72rem 0.82rem;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: #1e293b;
  cursor: pointer;
  font-size: 0.86rem;
  text-align: left;
}

.history-session-menu-item:hover {
  background: #f8fafc;
}

.history-session-menu-item.is-danger {
  color: #b42318;
}

.selector-group {
  position: relative;
  margin-bottom: 1.2rem;
}

.selector-group:last-child {
  margin-bottom: 0;
}

.selector-group label {
  display: block;
  margin-bottom: 0.55rem;
  font-size: 0.78rem;
  font-weight: 600;
  color: #64748b;
  letter-spacing: 0.02em;
}

.selector-trigger {
  width: 100%;
  min-height: 44px;
  padding: 0.78rem 0.95rem;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.94);
  color: #0f172a;
  font-size: 0.9rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  box-shadow:
    0 10px 24px rgba(15, 23, 42, 0.05),
    inset 0 1px 0 rgba(255, 255, 255, 0.92);
  transition:
    border-color 0.2s ease,
    background 0.2s ease,
    box-shadow 0.2s ease;
}

.selector-trigger:hover {
  background: #f8fbff;
  border-color: #cbd5e1;
}

.selector-trigger:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.selector-trigger.open {
  border-color: #93c5fd;
  background: #f8fbff;
  box-shadow: 0 16px 36px rgba(59, 130, 246, 0.12);
}

.selector-trigger-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.selector-trigger-icon {
  width: 2rem;
  height: 2rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-radius: 999px;
  color: #475569;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  transition:
    transform 0.22s ease,
    background 0.22s ease,
    border-color 0.22s ease;
}

.selector-trigger-icon-svg {
  width: 0.95rem;
  height: 0.95rem;
  display: block;
}

.selector-trigger.open .selector-trigger-icon {
  transform: rotate(180deg);
  background: #eff6ff;
  border-color: #bfdbfe;
}

.selector-dropdown {
  position: absolute;
  top: calc(100% + 0.5rem);
  left: 0;
  right: 0;
  z-index: 20;
  padding: 0.45rem;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(12px);
  box-shadow:
    0 20px 40px rgba(15, 23, 42, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.selector-option {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.8rem 0.9rem;
  border: none;
  border-radius: 12px;
  background: transparent;
  color: #1e293b;
  font-size: 0.9rem;
  text-align: left;
  cursor: pointer;
  transition:
    background 0.18s ease,
    color 0.18s ease,
    transform 0.18s ease;
}

.selector-option:hover {
  background: #f8fafc;
  transform: translateX(2px);
}

.selector-option.active {
  background: #eff6ff;
  color: #1d4ed8;
}

.selector-option-tag {
  padding: 0.18rem 0.45rem;
  border-radius: 999px;
  background: #dbeafe;
  color: #2563eb;
  font-size: 0.72rem;
  flex-shrink: 0;
}

.clear-btn {
  padding: 0.72rem 0.95rem;
  background: linear-gradient(135deg, #eff6ff, #dbeafe);
  color: #1d4ed8;
  border: 1px solid rgba(59, 130, 246, 0.22);
  border-radius: 14px;
  cursor: pointer;
  font-size: 0.88rem;
  font-weight: 600;
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    background-color 0.2s ease;
}

.clear-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 14px 28px rgba(37, 99, 235, 0.12);
}

.clear-btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.dialog-mask {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  background: rgba(15, 23, 42, 0.18);
  backdrop-filter: blur(4px);
}

.rename-dialog {
  width: min(100%, 28rem);
  padding: 1.1rem;
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 28px 60px rgba(15, 23, 42, 0.18);
}

.rename-dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.95rem;
}

.rename-dialog-header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: #0f172a;
}

.rename-dialog-close {
  width: 2rem;
  height: 2rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 999px;
  background: #f8fafc;
  color: #64748b;
  cursor: pointer;
}

.rename-dialog-close-icon {
  width: 0.95rem;
  height: 0.95rem;
}

.rename-dialog-input {
  width: 100%;
  min-height: 6rem;
  padding: 0.9rem 1rem;
  border: 1px solid #dbe3ee;
  border-radius: 16px;
  resize: none;
  font: inherit;
  line-height: 1.5;
  color: #0f172a;
  background: #fff;
}

.rename-dialog-input:focus {
  outline: none;
  border-color: #93c5fd;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.12);
}

.rename-dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.65rem;
  margin-top: 1rem;
}

.dialog-btn {
  min-width: 5rem;
  padding: 0.68rem 1rem;
  border-radius: 12px;
  border: none;
  cursor: pointer;
  font-size: 0.88rem;
  font-weight: 600;
}

.dialog-btn.is-secondary {
  background: #eef2f7;
  color: #334155;
}

.dialog-btn.is-primary {
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  color: white;
}

.dialog-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.dropdown-enter-active,
.dropdown-leave-active,
.menu-fade-enter-active,
.menu-fade-leave-active,
.dialog-fade-enter-active,
.dialog-fade-leave-active {
  transition:
    opacity 0.18s ease,
    transform 0.18s ease;
}

.dropdown-enter-from,
.dropdown-leave-to,
.menu-fade-enter-from,
.menu-fade-leave-to,
.dialog-fade-enter-from,
.dialog-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
