import { onBeforeUnmount, ref } from 'vue';

export const useCopyToast = () => {
  const copyToastMessage = ref('复制成功');
  const isCopyToastVisible = ref(false);
  let copyToastTimer: ReturnType<typeof setTimeout> | null = null;

  const showCopyToast = (message: string) => {
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
    copyToastMessage,
    isCopyToastVisible,
    showCopyToast,
  };
};
