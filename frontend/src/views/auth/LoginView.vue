<template>
  <div class="login-page">
    <div class="login-card fade-slide-up-target">
      <h1 class="login-title">登录</h1>
      <form class="login-form" @submit.prevent="onSubmit">
        <div class="login-field">
          <label class="login-label">用户名</label>
          <BaseInput
            v-model="username"
            placeholder="请输入用户名"
            autocomplete="username"
          />
        </div>
        <div class="login-field">
          <label class="login-label">密码</label>
          <PasswordInput
            v-model="password"
            placeholder="请输入密码"
            autocomplete="current-password"
          />
        </div>
        <Transition name="fade">
          <div v-if="errorMessage" class="login-error">
            {{ errorMessage }}
          </div>
        </Transition>
        <BaseButton
          type="submit"
          variant="primary"
          block
          :disabled="isLoading"
          class="login-submit"
        >
          {{ isLoading ? '登录中...' : '登录' }}
        </BaseButton>
      </form>
      <div class="login-footer">
        <span>还没有账号？</span>
        <router-link to="/register" class="login-link">去注册</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import BaseButton from '../../components/base/BaseButton.vue';
import BaseInput from '../../components/base/BaseInput.vue';
import PasswordInput from '../../components/base/PasswordInput.vue';
import { useAuthStore } from '../../stores/auth';

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const username = ref('');
const password = ref('');
const isLoading = ref(false);
const errorMessage = ref('');

async function onSubmit() {
  errorMessage.value = '';

  if (!username.value.trim()) {
    errorMessage.value = '请输入用户名';
    return;
  }
  if (!password.value) {
    errorMessage.value = '请输入密码';
    return;
  }

  isLoading.value = true;
  try {
    await authStore.login(username.value.trim(), password.value);
    const redirect = (route.query.redirect as string) || '/';
    router.push(redirect);
  } catch (err: any) {
    const detail =
      err?.response?.data?.detail || err?.message || '登录失败，请重试';
    errorMessage.value = detail;
  } finally {
    isLoading.value = false;
  }
}
</script>

<style scoped src="./styles/login-page.css" />
