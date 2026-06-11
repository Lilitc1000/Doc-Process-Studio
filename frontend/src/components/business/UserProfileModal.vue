<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
        <div class="modal-container">
          <div class="modal-left">
            <user-avatar
              :username="userInfo?.username ?? ''"
              :color="editAvatarColor ?? userInfo?.avatarColor ?? '#4f46e5'"
              size="lg"
              class="modal-avatar"
            />
            <div class="modal-info">
              <div class="modal-info-name">{{ userInfo?.username }}</div>
              <div class="modal-info-id">{{ userInfo?.userId }}</div>
              <div class="modal-info-date">
                {{ formatDate(userInfo?.createdAt, '') }}
              </div>
            </div>
          </div>
          <div class="modal-right">
            <div class="modal-tabs">
              <base-button
                type="button"
                class="modal-tab"
                :variant="activeTab === 'profile' ? 'secondary' : 'ghost'"
                size="sm"
                @click="activeTab = 'profile'"
              >
                基本信息
              </base-button>
              <base-button
                type="button"
                class="modal-tab"
                :variant="activeTab === 'password' ? 'secondary' : 'ghost'"
                size="sm"
                @click="activeTab = 'password'"
              >
                修改密码
              </base-button>
            </div>

            <Transition name="fade" mode="out-in">
              <div
                v-if="activeTab === 'profile'"
                key="profile"
                class="modal-tab-content"
              >
                <template v-if="!isEditing">
                  <div class="modal-field">
                    <label class="modal-field-label">用户名</label>
                    <div class="modal-field-value">
                      {{ userInfo?.username }}
                    </div>
                  </div>
                  <div class="modal-field">
                    <label class="modal-field-label">头像颜色</label>
                    <div class="modal-color-preview">
                      <span
                        class="modal-color-dot"
                        :style="{ backgroundColor: userInfo?.avatarColor }"
                      />
                    </div>
                  </div>
                  <div class="modal-actions">
                    <base-button variant="primary" @click="startEditing">
                      编辑
                    </base-button>
                  </div>
                </template>
                <template v-else>
                  <div class="modal-field">
                    <label class="modal-field-label">用户名</label>
                    <base-input v-model="editUsername" />
                  </div>
                  <div class="modal-field">
                    <label class="modal-field-label">头像颜色</label>
                    <div class="modal-color-picker">
                      <base-button
                        v-for="color in AVATAR_COLORS"
                        :key="color"
                        type="button"
                        class="modal-color-dot modal-color-dot-clickable"
                        :class="{ selected: editAvatarColor === color }"
                        variant="ghost"
                        size="sm"
                        :style="{ backgroundColor: color }"
                        @click="editAvatarColor = color"
                      />
                    </div>
                  </div>
                  <Transition name="fade">
                    <div v-if="errorMessage" class="modal-error">
                      {{ errorMessage }}
                    </div>
                  </Transition>
                  <div class="modal-actions">
                    <base-button
                      variant="primary"
                      :disabled="isSaving"
                      @click="saveProfile"
                    >
                      {{ isSaving ? '保存中...' : '保存' }}
                    </base-button>
                    <base-button variant="secondary" @click="cancelEditing">
                      取消
                    </base-button>
                  </div>
                </template>
              </div>

              <div v-else key="password" class="modal-tab-content">
                <div class="modal-field">
                  <label class="modal-field-label">当前密码</label>
                  <password-input v-model="currentPassword" />
                </div>
                <div class="modal-field">
                  <label class="modal-field-label">新密码</label>
                  <password-input v-model="newPassword" />
                </div>
                <div class="modal-field">
                  <label class="modal-field-label">确认新密码</label>
                  <password-input v-model="confirmPassword" />
                </div>
                <Transition name="fade">
                  <div v-if="passwordError" class="modal-error">
                    {{ passwordError }}
                  </div>
                </Transition>
                <div class="modal-actions">
                  <base-button
                    variant="primary"
                    :disabled="isChangingPassword"
                    @click="savePassword"
                  >
                    {{ isChangingPassword ? '保存中...' : '保存' }}
                  </base-button>
                  <base-button variant="secondary" @click="$emit('close')">
                    取消
                  </base-button>
                </div>
              </div>
            </Transition>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import BaseButton from '../base/BaseButton.vue';
import BaseInput from '../base/BaseInput.vue';
import PasswordInput from '../base/PasswordInput.vue';
import UserAvatar from './UserAvatar.vue';
import { AVATAR_COLORS } from '../../utils/common/avatar-colors';
import { useUserProfile } from '../../composables/business/useUserProfile';
import type { UserInfoResponse } from '../../types/auth/auth';
import { formatDate } from '../../utils/common/date';

const props = defineProps<{
  visible: boolean;
  userInfo: UserInfoResponse | null;
}>();

defineEmits<{
  (e: 'close'): void;
}>();

const {
  isSaving,
  isChangingPassword,
  errorMessage,
  passwordError,
  saveProfile: doSaveProfile,
  savePassword: doSavePassword,
} = useUserProfile();

const activeTab = ref<'profile' | 'password'>('profile');
const isEditing = ref(false);

const editUsername = ref('');
const editAvatarColor = ref('');
const currentPassword = ref('');
const newPassword = ref('');
const confirmPassword = ref('');

watch(
  () => props.visible,
  (val) => {
    if (val) {
      activeTab.value = 'profile';
      isEditing.value = false;
      errorMessage.value = '';
      passwordError.value = '';
      currentPassword.value = '';
      newPassword.value = '';
      confirmPassword.value = '';
    }
  },
);

function startEditing() {
  editUsername.value = props.userInfo?.username ?? '';
  editAvatarColor.value = props.userInfo?.avatarColor ?? '#4f46e5';
  isEditing.value = true;
  errorMessage.value = '';
}

function cancelEditing() {
  isEditing.value = false;
  errorMessage.value = '';
}

async function saveProfile() {
  const success = await doSaveProfile(
    editUsername.value,
    editAvatarColor.value,
  );
  if (success) {
    isEditing.value = false;
  }
}

async function savePassword() {
  const success = await doSavePassword(
    currentPassword.value,
    newPassword.value,
    confirmPassword.value,
  );
  if (success) {
    currentPassword.value = '';
    newPassword.value = '';
    confirmPassword.value = '';
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: var(--z-modal);
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(4px);
}

.modal-container {
  display: flex;
  gap: var(--space-2xl);
  background: rgba(255, 255, 255, 0.98);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--space-2xl);
  min-width: 520px;
  max-width: 600px;
  box-shadow: var(--shadow-modal), var(--shadow-inset);
}

.modal-left {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-lg);
  min-width: 140px;
}

.modal-avatar {
  margin-bottom: var(--space-xs);
}

.modal-info {
  text-align: center;
}

.modal-info-name {
  font-size: var(--text-base);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
}

.modal-info-id {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  margin-top: var(--space-2xs);
}

.modal-info-date {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin-top: var(--space-2xs);
}

.modal-right {
  flex: 1;
  min-width: 0;
}

.modal-tabs {
  display: flex;
  gap: var(--space-xs);
  margin-bottom: var(--space-lg);
  border-bottom: 1px solid var(--color-border);
  padding-bottom: var(--space-sm);
}

.modal-tab {
  padding: var(--space-xs) var(--space-md);
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition:
    background var(--transition-base),
    color var(--transition-base);
}

.modal-tab:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.modal-tab.active {
  background: var(--color-primary-light);
  color: var(--color-primary);
  font-weight: var(--font-semibold);
}

.modal-tab-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.modal-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.modal-field-label {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-secondary);
}

.modal-field-value {
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  padding: var(--space-sm) 0;
}

.modal-color-preview {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-xs) 0;
}

.modal-color-picker {
  display: flex;
  gap: var(--space-sm);
  padding: var(--space-xs) 0;
}

.modal-color-dot {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: inline-block;
}

.modal-color-dot-clickable {
  cursor: pointer;
  border: 2px solid transparent;
  transition:
    border-color var(--transition-base),
    transform var(--transition-base);
}

.modal-color-dot-clickable:hover {
  transform: scale(1.15);
}

.modal-color-dot-clickable.selected {
  border-color: var(--color-text-primary);
  transform: scale(1.15);
}

.modal-actions {
  display: flex;
  gap: var(--space-sm);
  margin-top: var(--space-sm);
}

.modal-error {
  font-size: var(--text-xs);
  color: var(--color-danger);
  background: var(--color-danger-light);
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-sm);
}
</style>
