<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
        <div class="modal-container">
          <div class="modal-left">
            <UserAvatar
              :username="userInfo?.username ?? ''"
              :color="editAvatarColor ?? userInfo?.avatarColor ?? '#4f46e5'"
              size="lg"
              class="modal-avatar"
            />
            <div class="modal-info">
              <div class="modal-info-name">{{ userInfo?.username }}</div>
              <div class="modal-info-id">{{ userInfo?.userId }}</div>
              <div class="modal-info-date">
                {{ formatDate(userInfo?.createdAt) }}
              </div>
            </div>
          </div>
          <div class="modal-right">
            <div class="modal-tabs">
              <button
                type="button"
                class="modal-tab"
                :class="{ active: activeTab === 'profile' }"
                @click="activeTab = 'profile'"
              >
                基本信息
              </button>
              <button
                type="button"
                class="modal-tab"
                :class="{ active: activeTab === 'password' }"
                @click="activeTab = 'password'"
              >
                修改密码
              </button>
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
                    <BaseButton variant="primary" @click="startEditing">
                      编辑
                    </BaseButton>
                  </div>
                </template>
                <template v-else>
                  <div class="modal-field">
                    <label class="modal-field-label">用户名</label>
                    <BaseInput v-model="editUsername" />
                  </div>
                  <div class="modal-field">
                    <label class="modal-field-label">头像颜色</label>
                    <div class="modal-color-picker">
                      <button
                        v-for="color in AVATAR_COLORS"
                        :key="color"
                        type="button"
                        class="modal-color-dot modal-color-dot-clickable"
                        :class="{ selected: editAvatarColor === color }"
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
                    <BaseButton
                      variant="primary"
                      :disabled="isSaving"
                      @click="saveProfile"
                    >
                      {{ isSaving ? '保存中...' : '保存' }}
                    </BaseButton>
                    <BaseButton variant="secondary" @click="cancelEditing">
                      取消
                    </BaseButton>
                  </div>
                </template>
              </div>

              <div v-else key="password" class="modal-tab-content">
                <div class="modal-field">
                  <label class="modal-field-label">当前密码</label>
                  <PasswordInput v-model="currentPassword" />
                </div>
                <div class="modal-field">
                  <label class="modal-field-label">新密码</label>
                  <PasswordInput v-model="newPassword" />
                </div>
                <div class="modal-field">
                  <label class="modal-field-label">确认新密码</label>
                  <PasswordInput v-model="confirmPassword" />
                </div>
                <Transition name="fade">
                  <div v-if="passwordError" class="modal-error">
                    {{ passwordError }}
                  </div>
                </Transition>
                <div class="modal-actions">
                  <BaseButton
                    variant="primary"
                    :disabled="isChangingPassword"
                    @click="savePassword"
                  >
                    {{ isChangingPassword ? '保存中...' : '保存' }}
                  </BaseButton>
                  <BaseButton variant="secondary" @click="$emit('close')">
                    取消
                  </BaseButton>
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
import { useAuthStore } from '../../stores/auth';
import { updateProfile, changePassword } from '../../api/auth';
import type { UserInfoResponse } from '../../types/auth/auth';

const props = defineProps<{
  visible: boolean;
  userInfo: UserInfoResponse | null;
}>();

defineEmits<{
  (e: 'close'): void;
}>();

const authStore = useAuthStore();

const activeTab = ref<'profile' | 'password'>('profile');
const isEditing = ref(false);
const isSaving = ref(false);
const isChangingPassword = ref(false);
const errorMessage = ref('');
const passwordError = ref('');

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
  if (editUsername.value.length < 3 || editUsername.value.length > 20) {
    errorMessage.value = '用户名长度需为 3-20 个字符';
    return;
  }
  isSaving.value = true;
  errorMessage.value = '';
  try {
    await updateProfile({
      username: editUsername.value,
      avatarColor: editAvatarColor.value,
    });
    await authStore.fetchUserInfo();
    isEditing.value = false;
  } catch (err: any) {
    const detail =
      err?.response?.data?.detail || err?.message || '保存失败，请重试';
    errorMessage.value = detail;
  } finally {
    isSaving.value = false;
  }
}

async function savePassword() {
  if (newPassword.value.length < 6) {
    passwordError.value = '新密码至少 6 个字符';
    return;
  }
  if (newPassword.value !== confirmPassword.value) {
    passwordError.value = '两次输入的密码不一致';
    return;
  }
  isChangingPassword.value = true;
  passwordError.value = '';
  try {
    await changePassword({
      currentPassword: currentPassword.value,
      newPassword: newPassword.value,
    });
    currentPassword.value = '';
    newPassword.value = '';
    confirmPassword.value = '';
    passwordError.value = '';
  } catch (err: any) {
    const detail =
      err?.response?.data?.detail || err?.message || '修改密码失败';
    passwordError.value = detail;
  } finally {
    isChangingPassword.value = false;
  }
}

function formatDate(dateStr?: string) {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    });
  } catch {
    return dateStr;
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(4px);
}

.modal-container {
  display: flex;
  gap: 2rem;
  background: rgba(255, 255, 255, 0.98);
  border-radius: 20px;
  padding: 2rem;
  min-width: 520px;
  max-width: 600px;
  box-shadow:
    0 20px 40px rgba(15, 23, 42, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
}

.modal-left {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  min-width: 140px;
}

.modal-avatar {
  margin-bottom: 0.25rem;
}

.modal-info {
  text-align: center;
}

.modal-info-name {
  font-size: 1rem;
  font-weight: 700;
  color: #0f172a;
}

.modal-info-id {
  font-size: 0.75rem;
  color: #64748b;
  margin-top: 0.15rem;
}

.modal-info-date {
  font-size: 0.72rem;
  color: #94a3b8;
  margin-top: 0.15rem;
}

.modal-right {
  flex: 1;
  min-width: 0;
}

.modal-tabs {
  display: flex;
  gap: 0.25rem;
  margin-bottom: 1rem;
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 0.5rem;
}

.modal-tab {
  padding: 0.35rem 0.75rem;
  border: none;
  border-radius: 8px;
  background: transparent;
  font-size: 0.82rem;
  color: #64748b;
  cursor: pointer;
  transition:
    background 0.18s ease,
    color 0.18s ease;
}

.modal-tab:hover {
  background: #f8fafc;
  color: #334155;
}

.modal-tab.active {
  background: #eff6ff;
  color: #2563eb;
  font-weight: 600;
}

.modal-tab-content {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.modal-field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.modal-field-label {
  font-size: 0.78rem;
  font-weight: 600;
  color: #475569;
}

.modal-field-value {
  font-size: 0.88rem;
  color: #0f172a;
  padding: 0.4rem 0;
}

.modal-color-preview {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0;
}

.modal-color-picker {
  display: flex;
  gap: 0.5rem;
  padding: 0.25rem 0;
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
    border-color 0.18s ease,
    transform 0.18s ease;
}

.modal-color-dot-clickable:hover {
  transform: scale(1.15);
}

.modal-color-dot-clickable.selected {
  border-color: #0f172a;
  transform: scale(1.15);
}

.modal-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.modal-error {
  font-size: 0.8rem;
  color: #ef4444;
  background: #fef2f2;
  padding: 0.4rem 0.65rem;
  border-radius: 8px;
}
</style>
