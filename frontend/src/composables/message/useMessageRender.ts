import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
  watchEffect,
  type Ref,
} from 'vue';
import type { ChatMessageDisplay } from '../../types/chat';
import {
  getCachedRenderedContent,
  renderMarkdown,
  renderPlainText,
  setCachedRenderedContent,
  shouldUseMarkdownRendering,
} from '../../utils/render-markdown';

interface UseMessageRenderOptions {
  message: Ref<ChatMessageDisplay>;
  cacheScopeId: Ref<string>;
  isEditing: Ref<boolean>;
  showToolbarByDefault: Ref<boolean>;
}

export const useMessageRender = (options: UseMessageRenderOptions) => {
  const renderedContent = ref('');
  const hasEnteredViewport = ref(false);
  const messageContentRef = ref<HTMLElement | null>(null);
  let messageViewportObserver: IntersectionObserver | null = null;

  const normalizedDisplayContent = computed(() => {
    const rawContent = options.message.value.content;
    if (
      options.message.value.role !== 'assistant' ||
      (options.message.value.files?.length ?? 0) === 0
    ) {
      return rawContent;
    }

    const cleanedLines = rawContent.split('\n').filter((line) => {
      const normalizedLine = line.trim();
      if (!normalizedLine) {
        return true;
      }
      if (normalizedLine.includes('file://')) {
        return false;
      }
      return !(
        normalizedLine.includes('复制到浏览器') ||
        normalizedLine.includes('点击下载')
      );
    });

    return cleanedLines.join('\n').trim();
  });

  const shouldRenderMarkdownContent = computed(() => {
    return shouldUseMarkdownRendering(
      normalizedDisplayContent.value,
      options.message.value.role,
    );
  });

  const activateLazyMarkdownRendering = () => {
    hasEnteredViewport.value = true;
    if (messageViewportObserver) {
      messageViewportObserver.disconnect();
      messageViewportObserver = null;
    }
  };

  const ensureViewportObservation = () => {
    if (
      hasEnteredViewport.value ||
      !shouldRenderMarkdownContent.value ||
      options.isEditing.value
    ) {
      return;
    }

    if (
      options.showToolbarByDefault.value ||
      typeof IntersectionObserver === 'undefined' ||
      !messageContentRef.value
    ) {
      activateLazyMarkdownRendering();
      return;
    }

    if (messageViewportObserver) {
      return;
    }

    messageViewportObserver = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          activateLazyMarkdownRendering();
        }
      },
      {
        root: null,
        rootMargin: '280px 0px',
        threshold: 0.01,
      },
    );

    messageViewportObserver.observe(messageContentRef.value);
  };

  watchEffect((onCleanup) => {
    let cancelled = false;
    const displayContent = normalizedDisplayContent.value;
    const currentMessage = options.message.value;
    const currentCacheScopeId = options.cacheScopeId.value;

    if (!shouldRenderMarkdownContent.value || !hasEnteredViewport.value) {
      const plainTextContent = renderPlainText(displayContent);
      renderedContent.value = plainTextContent;

      if (!shouldRenderMarkdownContent.value) {
        setCachedRenderedContent(
          currentCacheScopeId,
          currentMessage.id,
          displayContent,
          currentMessage.role,
          plainTextContent,
        );
      }
      return;
    }

    const cachedRenderedContent = getCachedRenderedContent(
      currentCacheScopeId,
      currentMessage.id,
      displayContent,
      currentMessage.role,
    );

    if (cachedRenderedContent) {
      renderedContent.value = cachedRenderedContent;
      return;
    }

    renderMarkdown(displayContent)
      .then((renderedHtml) => {
        if (!cancelled) {
          renderedContent.value = renderedHtml;
          setCachedRenderedContent(
            currentCacheScopeId,
            currentMessage.id,
            displayContent,
            currentMessage.role,
            renderedHtml,
          );
        }
      })
      .catch(() => {
        if (!cancelled) {
          const fallbackContent = renderPlainText(displayContent);
          renderedContent.value = fallbackContent;
          setCachedRenderedContent(
            currentCacheScopeId,
            currentMessage.id,
            displayContent,
            currentMessage.role,
            fallbackContent,
          );
        }
      });

    onCleanup(() => {
      cancelled = true;
    });
  });

  onMounted(() => {
    ensureViewportObservation();
  });

  watch(
    [
      shouldRenderMarkdownContent,
      options.showToolbarByDefault,
      options.isEditing,
    ],
    async () => {
      await nextTick();
      ensureViewportObservation();
    },
    { immediate: true },
  );

  watch(
    () => options.message.value.content,
    async () => {
      await nextTick();
      ensureViewportObservation();
    },
    { flush: 'post' },
  );

  watch(messageContentRef, () => {
    ensureViewportObservation();
  });

  onBeforeUnmount(() => {
    if (messageViewportObserver) {
      messageViewportObserver.disconnect();
      messageViewportObserver = null;
    }
  });

  return {
    messageContentRef,
    normalizedDisplayContent,
    renderedContent,
  };
};
