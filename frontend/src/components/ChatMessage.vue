<template>
  <div class="chat-message" :class="`role-${message.role}`">
    <div class="message-header">
      <div class="avatar">
        <span class="avatar-icon">
          {{
            message.role === 'user'
              ? '👤'
              : message.role === 'system'
                ? '🤖'
                : '✨'
          }}
        </span>
      </div>
      <div class="message-info">
        <span class="message-role">{{ messageRole }}</span>
        <span class="message-time">{{ formattedTime }}</span>
      </div>
    </div>
    <div class="message-content" v-html="renderedContent"></div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watchEffect } from 'vue';

const props = defineProps<{
  message: {
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp: Date;
  };
}>();

const renderedContent = ref('');

type RenderMarkdown = (content: string) => string;

let markdownRendererPromise: Promise<RenderMarkdown> | null = null;

const loadMarkdownRenderer = async (): Promise<RenderMarkdown> => {
  if (!markdownRendererPromise) {
    markdownRendererPromise = Promise.all([
      import('markdown-it'),
      import('highlight.js/lib/core'),
      import('highlight.js/lib/languages/javascript'),
      import('highlight.js/lib/languages/typescript'),
      import('highlight.js/lib/languages/json'),
      import('highlight.js/lib/languages/bash'),
      import('highlight.js/lib/languages/python'),
      import('highlight.js/lib/languages/xml'),
      import('highlight.js/lib/languages/css'),
      import('highlight.js/lib/languages/markdown'),
    ]).then(
      ([
        markdownItModule,
        highlightCoreModule,
        javascriptModule,
        typescriptModule,
        jsonModule,
        bashModule,
        pythonModule,
        xmlModule,
        cssModule,
        markdownModule,
      ]) => {
        const MarkdownIt = markdownItModule.default;
        const hljs = highlightCoreModule.default;

        hljs.registerLanguage('javascript', javascriptModule.default);
        hljs.registerLanguage('js', javascriptModule.default);
        hljs.registerLanguage('typescript', typescriptModule.default);
        hljs.registerLanguage('ts', typescriptModule.default);
        hljs.registerLanguage('json', jsonModule.default);
        hljs.registerLanguage('bash', bashModule.default);
        hljs.registerLanguage('shell', bashModule.default);
        hljs.registerLanguage('sh', bashModule.default);
        hljs.registerLanguage('python', pythonModule.default);
        hljs.registerLanguage('py', pythonModule.default);
        hljs.registerLanguage('xml', xmlModule.default);
        hljs.registerLanguage('html', xmlModule.default);
        hljs.registerLanguage('vue', xmlModule.default);
        hljs.registerLanguage('css', cssModule.default);
        hljs.registerLanguage('markdown', markdownModule.default);
        hljs.registerLanguage('md', markdownModule.default);

        const markdown = new MarkdownIt({
          html: false,
          xhtmlOut: false,
          breaks: true,
          linkify: true,
          typographer: true,
          langPrefix: 'language-',
          highlight: (str: string, lang: string): string => {
            if (lang) {
              try {
                return `<pre class="highlight"><code class="hljs ${lang}">${hljs.highlight(str, { language: lang }).value}</code></pre>`;
              } catch (_) {}
            }

            return `<pre class="highlight"><code class="hljs">${markdown.utils.escapeHtml(str)}</code></pre>`;
          },
        });

        return (content: string) => markdown.render(content);
      },
    );
  }

  return markdownRendererPromise;
};

const formattedTime = computed(() => {
  const date = props.message.timestamp;
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  });
});

const messageRoleMap = {
  user: '你',
  assistant: 'AI 助手',
  system: '系统',
};

const messageRole = computed(() => {
  return messageRoleMap[props.message.role] || props.message.role;
});

watchEffect((onCleanup) => {
  let cancelled = false;

  loadMarkdownRenderer()
    .then((renderMarkdown) => {
      if (!cancelled) {
        renderedContent.value = renderMarkdown(props.message.content);
      }
    })
    .catch(() => {
      if (!cancelled) {
        renderedContent.value = props.message.content;
      }
    });

  onCleanup(() => {
    cancelled = true;
  });
});
</script>

<style scoped>
.chat-message {
  display: flex;
  flex-direction: column;
  max-width: 80%;
  margin: 0 auto;
}

.chat-message.role-user {
  align-self: flex-end;
  align-items: flex-end;
}

.chat-message.role-assistant {
  align-self: flex-start;
  align-items: flex-start;
}

.chat-message.role-system {
  align-self: center;
  align-items: center;
  max-width: 60%;
  font-size: 0.85rem;
  color: #666;
  background: #f5f5f5;
  border-radius: 8px;
  padding: 0.5rem 1rem;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
  font-size: 0.75rem;
  color: #666;
}

.avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.message.role-user .avatar {
  background: #007acc;
}

.message.role-assistant .avatar {
  background: #4caf50;
}

.message.role-system .avatar {
  background: #ff9800;
}

.avatar-icon {
  font-size: 14px;
}

.message-info {
  display: flex;
  flex-direction: column;
}

.message-role {
  font-weight: 600;
  font-size: 0.8rem;
}

.message-time {
  font-size: 0.7rem;
}

.message-content {
  padding: 1rem;
  border-radius: 12px;
  line-height: 1.6;
  font-size: 0.95rem;
  max-width: 100%;
  overflow-x: auto;
}

.chat-message.role-user .message-content {
  background: #007acc;
  color: white;
  border-bottom-right-radius: 2px;
}

.chat-message.role-assistant .message-content {
  background: #f0f0f0;
  color: #333;
  border-bottom-left-radius: 2px;
}

.chat-message.role-system .message-content {
  background: transparent;
  color: inherit;
}

.message-content :deep(p) {
  margin: 0 0 0.5rem 0;
}

.message-content :deep(p:last-child) {
  margin: 0;
}

.message-content :deep(ul),
.message-content :deep(ol) {
  margin: 0 0 0.5rem 0;
  padding-left: 1.5rem;
}

.message-content :deep(li) {
  margin-bottom: 0.25rem;
}

.message-content :deep(code) {
  font-family: 'Courier New', monospace;
  font-size: 0.85em;
  background: rgba(0, 0, 0, 0.1);
  padding: 0.2em 0.4em;
  border-radius: 3px;
}

.message-content :deep(pre) {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 1rem;
  border-radius: 6px;
  overflow-x: auto;
  margin: 0.5rem 0;
}

.message-content :deep(pre code) {
  background: transparent;
  padding: 0;
  color: inherit;
}

.message-content :deep(blockquote) {
  border-left: 4px solid #007acc;
  padding-left: 1rem;
  margin: 0.5rem 0;
  color: #555;
  background: #f9f9f9;
  padding: 0.5rem 1rem;
  border-radius: 4px;
}

.message-content :deep(a) {
  color: #007acc;
  text-decoration: none;
}

.message-content :deep(a:hover) {
  text-decoration: underline;
}

.message-content :deep(strong) {
  font-weight: 600;
}

.message-content :deep(em) {
  font-style: italic;
}
</style>
