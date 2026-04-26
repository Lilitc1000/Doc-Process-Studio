import { describe, expect, it } from 'vitest';
import {
  shouldUseMarkdownRendering,
  renderPlainText,
  getCachedRenderedContent,
  setCachedRenderedContent,
} from '../../../src/utils/common/render-markdown';

describe('shouldUseMarkdownRendering', () => {
  it('空内容返回 false', () => {
    expect(shouldUseMarkdownRendering('', 'user')).toBe(false);
    expect(shouldUseMarkdownRendering('   ', 'user')).toBe(false);
  });

  it('assistant 角色始终返回 true', () => {
    expect(shouldUseMarkdownRendering('hello', 'assistant')).toBe(true);
    expect(shouldUseMarkdownRendering('简单文本', 'assistant')).toBe(true);
  });

  it('system 角色始终返回 true', () => {
    expect(shouldUseMarkdownRendering('hello', 'system')).toBe(true);
  });

  it('user 角色无 Markdown 特征返回 false', () => {
    expect(shouldUseMarkdownRendering('普通文本消息', 'user')).toBe(false);
  });

  it('user 角色含代码块返回 true', () => {
    expect(shouldUseMarkdownRendering('```js\ncode\n```', 'user')).toBe(true);
  });

  it('user 角色含行内代码返回 true', () => {
    expect(shouldUseMarkdownRendering('使用 `npm install` 安装', 'user')).toBe(
      true,
    );
  });

  it('user 角色含标题返回 true', () => {
    expect(shouldUseMarkdownRendering('# 标题', 'user')).toBe(true);
    expect(shouldUseMarkdownRendering('## 二级标题', 'user')).toBe(true);
  });

  it('user 角色含列表返回 true', () => {
    expect(shouldUseMarkdownRendering('- 列表项', 'user')).toBe(true);
    expect(shouldUseMarkdownRendering('1. 有序列表', 'user')).toBe(true);
  });

  it('user 角色含引用返回 true', () => {
    expect(shouldUseMarkdownRendering('> 引用内容', 'user')).toBe(true);
  });

  it('user 角色含链接返回 true', () => {
    expect(
      shouldUseMarkdownRendering('[链接](https://example.com)', 'user'),
    ).toBe(true);
  });

  it('user 角色含表格返回 true', () => {
    expect(shouldUseMarkdownRendering('| 列1 | 列2 |', 'user')).toBe(true);
  });

  it('user 角色含粗体返回 true', () => {
    expect(shouldUseMarkdownRendering('**粗体文本**', 'user')).toBe(true);
  });

  it('user 角色含下划线粗体返回 true', () => {
    expect(shouldUseMarkdownRendering('__粗体文本__', 'user')).toBe(true);
  });
});

describe('renderPlainText', () => {
  it('转义 HTML 特殊字符', () => {
    expect(renderPlainText('<script>alert("xss")</script>')).toBe(
      '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;',
    );
  });

  it('转义 & 符号', () => {
    expect(renderPlainText('a & b')).toBe('a &amp; b');
  });

  it('转义单引号', () => {
    expect(renderPlainText("it's")).toBe('it&#39;s');
  });

  it('换行符转为 <br>', () => {
    expect(renderPlainText('第一行\n第二行')).toBe('第一行<br>第二行');
  });

  it('空字符串保持不变', () => {
    expect(renderPlainText('')).toBe('');
  });

  it('纯文本保持不变', () => {
    expect(renderPlainText('hello world')).toBe('hello world');
  });

  it('多个换行符正确转换', () => {
    expect(renderPlainText('a\nb\nc')).toBe('a<br>b<br>c');
  });
});

describe('render cache', () => {
  it('setCachedRenderedContent 后 getCachedRenderedContent 返回缓存内容', () => {
    setCachedRenderedContent(
      'scope-1',
      'msg-1',
      'content-1',
      'user',
      '<p>html</p>',
    );
    const cached = getCachedRenderedContent(
      'scope-1',
      'msg-1',
      'content-1',
      'user',
    );
    expect(cached).toBe('<p>html</p>');
  });

  it('未缓存的内容返回 null', () => {
    const cached = getCachedRenderedContent(
      'scope-x',
      'msg-x',
      'content-x',
      'assistant',
    );
    expect(cached).toBeNull();
  });

  it('不同 scope 隔离缓存', () => {
    setCachedRenderedContent('scope-a', 'msg-1', 'content', 'user', '<p>A</p>');
    setCachedRenderedContent('scope-b', 'msg-1', 'content', 'user', '<p>B</p>');
    expect(
      getCachedRenderedContent('scope-a', 'msg-1', 'content', 'user'),
    ).toBe('<p>A</p>');
    expect(
      getCachedRenderedContent('scope-b', 'msg-1', 'content', 'user'),
    ).toBe('<p>B</p>');
  });

  it('不同 role 隔离缓存', () => {
    setCachedRenderedContent(
      'scope-1',
      'msg-1',
      'content',
      'user',
      '<p>user</p>',
    );
    setCachedRenderedContent(
      'scope-1',
      'msg-1',
      'content',
      'assistant',
      '<p>assistant</p>',
    );
    expect(
      getCachedRenderedContent('scope-1', 'msg-1', 'content', 'user'),
    ).toBe('<p>user</p>');
    expect(
      getCachedRenderedContent('scope-1', 'msg-1', 'content', 'assistant'),
    ).toBe('<p>assistant</p>');
  });

  it('内容变更后缓存失效', () => {
    setCachedRenderedContent(
      'scope-1',
      'msg-1',
      'old-content',
      'user',
      '<p>old</p>',
    );
    const cached = getCachedRenderedContent(
      'scope-1',
      'msg-1',
      'new-content',
      'user',
    );
    expect(cached).toBeNull();
  });
});
