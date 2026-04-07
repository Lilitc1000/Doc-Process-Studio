import { onBeforeUnmount, ref } from 'vue';

export const useCopyToast = () => {
  const copyToastTitle = ref('复制成功');
  const copyToastMessage = ref('复制成功');
  const isCopyToastVisible = ref(false);
  let copyToastTimer: ReturnType<typeof setTimeout> | null = null;

  const showCopyToast = (
    message: string,
    options?: {
      title?: string;
    },
  ) => {
    copyToastTitle.value = options?.title?.trim() || '复制成功';
    copyToastMessage.value = message;
    isCopyToastVisible.value = true;

    if (copyToastTimer) {
      clearTimeout(copyToastTimer);
    }

    copyToastTimer = setTimeout(() => {
      isCopyToastVisible.value = false;
    }, 1600);
  };

  onBeforeUnmount(() => {
    if (copyToastTimer) {
      clearTimeout(copyToastTimer);
    }
  });

  return {
    copyToastTitle,
    copyToastMessage,
    isCopyToastVisible,
    showCopyToast,
  };
};
