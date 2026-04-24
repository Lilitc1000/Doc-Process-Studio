<template>
  <aside class="chat-sidebar">
    <div class="sidebar-header">
      <h2>历史会话</h2>
      <base-button
        v-if="newSessionLabel"
        type="button"
        class="new-session-btn"
        variant="secondary"
        size="sm"
        :disabled="isLocked"
        @click="$emit('new-session')"
      >
        <svg viewBox="0 0 16 16" class="new-session-icon" aria-hidden="true">
          <path
            d="M8 3v10M3 8h10"
            fill="none"
            stroke="currentColor"
            stroke-linecap="round"
            stroke-width="1.8"
          />
        </svg>
        <span>{{ newSessionLabel }}</span>
      </base-button>
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
              <base-button
                type="button"
                class="history-session-main"
                variant="ghost"
                :disabled="props.isLocked"
                @click="$emit('load-session', session.id)"
              >
                <span class="history-session-title" :title="session.title">
                  {{ session.title }}
                </span>
                <span
                  v-if="session.statusLabel"
                  class="history-session-status"
                  :title="session.statusLabel"
                >
                  {{ session.statusLabel }}
                </span>
              </base-button>

              <base-button
                type="button"
                class="session-more-btn"
                variant="ghost"
                size="sm"
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
              </base-button>

              <transition name="menu-fade">
                <div
                  v-if="openSessionMenuId === session.id"
                  class="history-session-menu"
                >
                  <base-button
                    type="button"
                    class="history-session-menu-item"
                    variant="ghost"
                    size="sm"
                    @click.stop="openRenameDialog(session)"
                  >
                    编辑标题
                  </base-button>
                  <base-button
                    type="button"
                    class="history-session-menu-item is-danger"
                    variant="ghost"
                    size="sm"
                    @click.stop="deleteSession(session.id)"
                  >
                    删除
                  </base-button>
                </div>
              </transition>
            </div>
          </div>
        </div>
      </section>
    </div>

    <teleport to="body">
      <transition name="dialog-fade">
        <div
          v-if="renameDialogSession"
          class="dialog-mask"
          @click.self="closeRenameDialog"
        >
          <div class="rename-dialog">
            <div class="rename-dialog-header">
              <h3>修改名称</h3>
              <base-button
                type="button"
                class="rename-dialog-close"
                variant="ghost"
                size="sm"
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
              </base-button>
            </div>

            <base-textarea
              :value="renameInput"
              class="rename-dialog-input"
              rows="3"
              placeholder="请输入新的会话名称"
              @input="onRenameInput"
            ></base-textarea>

            <div class="rename-dialog-actions">
              <base-button
                type="button"
                class="dialog-btn is-secondary"
                variant="secondary"
                @click="closeRenameDialog"
              >
                取消
              </base-button>
              <base-button
                type="button"
                class="dialog-btn is-primary"
                variant="primary"
                :disabled="renameInput.trim().length === 0"
                @click="confirmRename"
              >
                确定
              </base-button>
            </div>
          </div>
        </div>
      </transition>
    </teleport>
  </aside>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import BaseButton from '../base/BaseButton.vue';
import BaseTextarea from '../base/BaseTextarea.vue';
import { groupSessionsByDate } from '../../utils/chat/session-groups';

interface SessionSidebarItem {
  id: string;
  title: string;
  createdAt?: string;
  updatedAt?: string;
  status?: string;
  statusLabel?: string;
  [key: string]: unknown;
}

interface SessionGroup {
  id: string;
  label: string;
  sessions: SessionSidebarItem[];
}

const props = defineProps<{
  sessions: readonly SessionSidebarItem[];
  activeSessionId: string | null;
  isLocked?: boolean;
  newSessionLabel?: string;
  groupByCreatedAt?: boolean;
}>();

const emit = defineEmits<{
  (e: 'load-session', sessionId: string): void;
  (e: 'rename-session', payload: { sessionId: string; title: string }): void;
  (e: 'delete-session', sessionId: string): void;
  (e: 'new-session'): void;
}>();

const openSessionMenuId = ref<string | null>(null);
const renameDialogSession = ref<SessionSidebarItem | null>(null);
const renameInput = ref('');

const sessionGroups = computed<SessionGroup[]>(() => {
  return groupSessionsByDate(props.sessions, {
    dateField: props.groupByCreatedAt ? 'createdAt' : 'updatedAt',
  });
});

const closeSessionMenu = () => {
  openSessionMenuId.value = null;
};

const closeRenameDialog = () => {
  renameDialogSession.value = null;
  renameInput.value = '';
};

const toggleSessionMenu = (sessionId: string) => {
  if (props.isLocked) {
    return;
  }
  openSessionMenuId.value =
    openSessionMenuId.value === sessionId ? null : sessionId;
};

const openRenameDialog = (session: SessionSidebarItem) => {
  renameDialogSession.value = session;
  renameInput.value = session.title;
  closeSessionMenu();
};

const onRenameInput = (event: Event) => {
  renameInput.value = (event.target as HTMLTextAreaElement).value;
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

const handleClickOutside = (event: MouseEvent) => {
  const target = event.target as HTMLElement | null;

  if (
    target &&
    !target.closest('.history-session-menu') &&
    !target.closest('.session-more-btn')
  ) {
    closeSessionMenu();
  }
};

const handleWindowBlur = () => {
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

<style scoped src="../../views/chat/styles/chat-sidebar.css"></style>
