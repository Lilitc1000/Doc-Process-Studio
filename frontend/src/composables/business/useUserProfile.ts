import { ref } from 'vue';
import { useAuthStore } from '../../stores/auth';
import { updateProfile, changePassword } from '../../api/auth';

export function useUserProfile() {
  const authStore = useAuthStore();
  const isSaving = ref(false);
  const isChangingPassword = ref(false);
  const errorMessage = ref('');
  const passwordError = ref('');

  const saveProfile = async (username: string, avatarColor: string) => {
    if (username.length < 3 || username.length > 20) {
      errorMessage.value = '用户名长度需为 3-20 个字符';
      return false;
    }
    isSaving.value = true;
    errorMessage.value = '';
    try {
      await updateProfile({ username, avatarColor });
      await authStore.fetchUserInfo();
      return true;
    } catch (err: any) {
      const detail =
        err?.response?.data?.detail || err?.message || '保存失败，请重试';
      errorMessage.value = detail;
      return false;
    } finally {
      isSaving.value = false;
    }
  };

  const savePassword = async (
    currentPasswordVal: string,
    newPasswordVal: string,
    confirmPasswordVal: string,
  ) => {
    if (newPasswordVal.length < 6) {
      passwordError.value = '新密码至少 6 个字符';
      return false;
    }
    if (newPasswordVal !== confirmPasswordVal) {
      passwordError.value = '两次输入的密码不一致';
      return false;
    }
    isChangingPassword.value = true;
    passwordError.value = '';
    try {
      await changePassword({
        currentPassword: currentPasswordVal,
        newPassword: newPasswordVal,
      });
      return true;
    } catch (err: any) {
      const detail =
        err?.response?.data?.detail || err?.message || '修改密码失败';
      passwordError.value = detail;
      return false;
    } finally {
      isChangingPassword.value = false;
    }
  };

  return {
    isSaving,
    isChangingPassword,
    errorMessage,
    passwordError,
    saveProfile,
    savePassword,
  };
}
