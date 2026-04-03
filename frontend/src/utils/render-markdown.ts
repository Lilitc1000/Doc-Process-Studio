import type { LanguageFn } from 'highlight.js';

type RenderMarkdown = (content: string) => string;
type HighlightLanguageModule = {
  default: LanguageFn;
};
type RenderCacheRole = 'user' | 'assistant' | 'system';
type RenderCacheKey = `${string}::${string}::${RenderCacheRole}::${string}`;
type RenderCacheRecord = {
  key: RenderCacheKey;
  html: string;
};
type RenderCacheItem = {
  cacheScopeId: string;
  messageId: string;
  content: string;
  role: RenderCacheRole;
};

const highlightLanguageEntries = [
  {
    aliases: ['javascript', 'js'],
    load: () => import('highlight.js/lib/languages/javascript'),
  },
  {
    aliases: ['typescript', 'ts'],
    load: () => import('highlight.js/lib/languages/typescript'),
  },
  {
    aliases: ['json'],
    load: () => import('highlight.js/lib/languages/json'),
  },
  {
    aliases: ['bash', 'shell', 'sh'],
    load: () => import('highlight.js/lib/languages/bash'),
  },
  {
    aliases: ['python', 'py'],
    load: () => import('highlight.js/lib/languages/python'),
  },
  {
    aliases: ['xml', 'html', 'vue'],
    load: () => import('highlight.js/lib/languages/xml'),
  },
  {
    aliases: ['css'],
    load: () => import('highlight.js/lib/languages/css'),
  },
  {
    aliases: ['markdown', 'md'],
    load: () => import('highlight.js/lib/languages/markdown'),
  },
] satisfies Array<{
  aliases: string[];
  load: () => Promise<HighlightLanguageModule>;
}>;

let markdownRendererPromise: Promise<RenderMarkdown> | null = null;
const renderedMessageCache = new Map<RenderCacheKey, string>();
const RENDER_CACHE_STORAGE_KEY = 'chat-render-cache';
const RENDER_CACHE_MAX_ENTRIES = 300;
let persistentCacheLoaded = false;

const markdownFeaturePatterns = [
  /```/,
  /`[^`\n]+`/,
  /^\s{0,3}#{1,6}\s/m,
  /^\s*[-*+]\s/m,
  /^\s*\d+\.\s/m,
  /^\s*>\s/m,
  /\[[^\]]+\]\([^)]+\)/,
  /\|.*\|/,
  /\*\*[^*]+\*\*/,
  /__[^_]+__/,
];

export const shouldUseMarkdownRendering = (
  content: string,
  role: 'user' | 'assistant' | 'system',
) => {
  if (!content.trim()) {
    return false;
  }

  if (role === 'assistant' || role === 'system') {
    return true;
  }

  return markdownFeaturePatterns.some((pattern) => {
    return pattern.test(content);
  });
};

export const renderPlainText = (content: string) => {
  return content
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
    .replaceAll('\n', '<br>');
};

const canUseSessionStorage = () => {
  return (
    typeof window !== 'undefined' &&
    typeof window.sessionStorage !== 'undefined'
  );
};

const hashRenderContent = (content: string) => {
  let hash = 5381;

  for (let index = 0; index < content.length; index += 1) {
    hash = (hash * 33) ^ content.charCodeAt(index);
  }

  return (hash >>> 0).toString(36);
};

const loadPersistentRenderCache = () => {
  if (persistentCacheLoaded || !canUseSessionStorage()) {
    return;
  }

  persistentCacheLoaded = true;

  try {
    const rawCache = window.sessionStorage.getItem(RENDER_CACHE_STORAGE_KEY);
    if (!rawCache) {
      return;
    }

    const parsedCache = JSON.parse(rawCache) as RenderCacheRecord[];
    for (const entry of parsedCache) {
      renderedMessageCache.set(entry.key, entry.html);
    }
  } catch {
    // 忽略 sessionStorage 解析失败，避免影响正常渲染。
  }
};

const persistRenderCache = () => {
  if (!canUseSessionStorage()) {
    return;
  }

  try {
    const entries = Array.from(renderedMessageCache.entries())
      .slice(-RENDER_CACHE_MAX_ENTRIES)
      .map(([key, html]) => ({
        key,
        html,
      })) satisfies RenderCacheRecord[];

    window.sessionStorage.setItem(
      RENDER_CACHE_STORAGE_KEY,
      JSON.stringify(entries),
    );
  } catch {
    // 忽略持久化失败，避免影响正常渲染。
  }
};

const trimRenderCache = () => {
  while (renderedMessageCache.size > RENDER_CACHE_MAX_ENTRIES) {
    const oldestKey = renderedMessageCache.keys().next().value;
    if (!oldestKey) {
      break;
    }
    renderedMessageCache.delete(oldestKey);
  }
};

const createRenderCacheKey = (
  cacheScopeId: string,
  messageId: string,
  content: string,
  role: RenderCacheRole,
): RenderCacheKey => {
  return `${cacheScopeId}::${messageId}::${role}::${hashRenderContent(content)}`;
};

export const getCachedRenderedContent = (
  cacheScopeId: string,
  messageId: string,
  content: string,
  role: RenderCacheRole,
) => {
  loadPersistentRenderCache();

  return (
    renderedMessageCache.get(
      createRenderCacheKey(cacheScopeId, messageId, content, role),
    ) ?? null
  );
};

export const setCachedRenderedContent = (
  cacheScopeId: string,
  messageId: string,
  content: string,
  role: RenderCacheRole,
  renderedHtml: string,
) => {
  loadPersistentRenderCache();

  const cacheKey = createRenderCacheKey(cacheScopeId, messageId, content, role);
  renderedMessageCache.set(cacheKey, renderedHtml);
  trimRenderCache();
  persistRenderCache();
};

const loadMarkdownRenderer = async (): Promise<RenderMarkdown> => {
  if (!markdownRendererPromise) {
    markdownRendererPromise = Promise.all([
      import('markdown-it'),
      import('highlight.js/lib/core'),
      Promise.all(
        highlightLanguageEntries.map(async (entry) => {
          const languageModule = await entry.load();
          return {
            aliases: entry.aliases,
            language: languageModule.default,
          };
        }),
      ),
    ]).then(([markdownItModule, highlightCoreModule, languageEntries]) => {
      const MarkdownIt = markdownItModule.default;
      const hljs = highlightCoreModule.default;

      for (const entry of languageEntries) {
        const [primaryAlias, ...secondaryAliases] = entry.aliases;
        hljs.registerLanguage(primaryAlias, entry.language);
        if (secondaryAliases.length > 0) {
          hljs.registerAliases(secondaryAliases, {
            languageName: primaryAlias,
          });
        }
      }

      const markdown = new MarkdownIt({
        html: true,
        xhtmlOut: false,
        breaks: true,
        linkify: true,
        typographer: true,
        langPrefix: 'language-',
        highlight: (str: string, lang: string): string => {
          if (lang && hljs.getLanguage(lang)) {
            try {
              return `<pre class="highlight"><code class="hljs ${lang}">${hljs.highlight(str, { language: lang }).value}</code></pre>`;
            } catch {
              // 当语言名无效时，回退到普通转义文本。
            }
          }

          return `<pre class="highlight"><code class="hljs">${markdown.utils.escapeHtml(str)}</code></pre>`;
        },
      });

      return (content: string) => markdown.render(content);
    });
  }

  return markdownRendererPromise;
};

export const renderMarkdown = async (content: string) => {
  const renderer = await loadMarkdownRenderer();
  return renderer(content);
};

const scheduleBackgroundTask = (task: () => void) => {
  if (typeof window === 'undefined') {
    task();
    return;
  }

  const idleCallback = window.requestIdleCallback;
  if (typeof idleCallback === 'function') {
    idleCallback(() => {
      task();
    });
    return;
  }

  window.setTimeout(task, 0);
};

export const prewarmRenderedContentCache = (items: RenderCacheItem[]) => {
  const uniqueItems = items.filter((item, index, source) => {
    return (
      source.findIndex((candidate) => {
        return (
          candidate.cacheScopeId === item.cacheScopeId &&
          candidate.messageId === item.messageId &&
          candidate.content === item.content &&
          candidate.role === item.role
        );
      }) === index
    );
  });

  scheduleBackgroundTask(() => {
    for (const item of uniqueItems) {
      if (!item.content.trim()) {
        continue;
      }

      const cachedContent = getCachedRenderedContent(
        item.cacheScopeId,
        item.messageId,
        item.content,
        item.role,
      );
      if (cachedContent) {
        continue;
      }

      if (!shouldUseMarkdownRendering(item.content, item.role)) {
        setCachedRenderedContent(
          item.cacheScopeId,
          item.messageId,
          item.content,
          item.role,
          renderPlainText(item.content),
        );
        continue;
      }

      void renderMarkdown(item.content)
        .then((renderedHtml) => {
          setCachedRenderedContent(
            item.cacheScopeId,
            item.messageId,
            item.content,
            item.role,
            renderedHtml,
          );
        })
        .catch(() => {
          setCachedRenderedContent(
            item.cacheScopeId,
            item.messageId,
            item.content,
            item.role,
            renderPlainText(item.content),
          );
        });
    }
  });
};
