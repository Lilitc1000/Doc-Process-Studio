<template>
  <div class="register-page">
    <div class="register-card fade-slide-up-target">
      <h1 class="register-title">注册</h1>
      <form class="register-form" @submit.prevent="onSubmit">
        <div class="register-field">
          <label class="register-label">用户名</label>
          <BaseInput
            v-model="username"
            placeholder="3-20 个字符"
            autocomplete="username"
          />
        </div>
        <div class="register-field">
          <label class="register-label">密码</label>
          <PasswordInput
            v-model="password"
            placeholder="至少 6 个字符"
            autocomplete="new-password"
          />
        </div>
        <div class="register-field">
          <label class="register-label">确认密码</label>
          <PasswordInput
            v-model="confirmPassword"
            placeholder="再次输入密码"
            autocomplete="new-password"
          />
        </div>
        <Transition name="fade">
          <div v-if="errorMessage" class="register-error">
            {{ errorMessage }}
          </div>
        </Transition>
        <BaseButton
          type="submit"
          variant="primary"
          block
          :disabled="isLoading"
          class="register-submit"
        >
          {{ isLoading ? '注册中...' : '注册' }}
        </BaseButton>
      </form>
      <div class="register-footer">
        <span>已有账号？</span>
        <router-link to="/login" class="register-link">去登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import BaseButton from '../../components/base/BaseButton.vue';
import BaseInput from '../../components/base/BaseInput.vue';
import PasswordInput from '../../components/base/PasswordInput.vue';
import { useAuthStore } from '../../stores/auth';

const router = useRouter();
const authStore = useAuthStore();

const username = ref('');
const password = ref('');
const confirmPassword = ref('');
const isLoading = ref(false);
const errorMessage = ref('');

async function onSubmit() {
  errorMessage.value = '';

  const trimmedUsername = username.value.trim();
  if (
    !trimmedUsername ||
    trimmedUsername.length < 3 ||
    trimmedUsername.length > 20
  ) {
    errorMessage.value = '用户名长度需为 3-20 个字符';
    return;
  }
  if (password.value.length < 6) {
    errorMessage.value = '密码至少 6 个字符';
    return;
  }
  if (password.value !== confirmPassword.value) {
    errorMessage.value = '两次输入的密码不一致';
    return;
  }

  isLoading.value = true;
  try {
    await authStore.register(trimmedUsername, password.value);
    router.push('/login');
  } catch (err: any) {
    const detail =
      err?.response?.data?.detail || err?.message || '注册失败，请重试';
    errorMessage.value = detail;
  } finally {
    isLoading.value = false;
  }
}
</script>

<style scoped src="./styles/register-page.css" />
