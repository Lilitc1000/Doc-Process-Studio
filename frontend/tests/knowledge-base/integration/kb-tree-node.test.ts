import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import KbTreeNode from '@modules/knowledge-base/views/KbTreeNode.vue';
import type { KBTreeNodeDocument } from '@modules/knowledge-base';

function makeDoc(
  overrides: Partial<KBTreeNodeDocument> = {},
): KBTreeNodeDocument {
  return {
    type: 'document',
    id: 'doc-001',
    name: 'report.pdf',
    fileType: 'pdf',
    fileSize: 1024,
    chunkCount: 5,
    isIndexed: false,
    parseStatus: 'UNSTART',
    uploadedAt: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('KbTreeNode 解析状态徽章', () => {
  it('未索引文档显示「未索引」徽章并支持点击', async () => {
    const wrapper = mount(KbTreeNode, {
      props: {
        node: makeDoc({ parseStatus: 'UNSTART' }),
        projectId: 'proj-001',
      },
    });

    const badge = wrapper.find('.kb-tree-badge');
    expect(badge.exists()).toBe(true);
    expect(badge.text()).toBe('未索引');
    expect(badge.classes()).toContain('kb-tree-badge--pending');

    await badge.trigger('click');
    expect(wrapper.emitted('showParseDetail')).toBeTruthy();
    expect(wrapper.emitted('showParseDetail')![0]).toEqual(['doc-001']);
  });

  it('解析中文档显示「解析中」徽章', () => {
    const wrapper = mount(KbTreeNode, {
      props: {
        node: makeDoc({ parseStatus: 'RUNNING' }),
        projectId: 'proj-001',
      },
    });

    const badge = wrapper.find('.kb-tree-badge');
    expect(badge.exists()).toBe(true);
    expect(badge.text()).toBe('解析中');
    expect(badge.classes()).toContain('kb-tree-badge--pending');
  });

  it('解析失败文档显示「解析失败」徽章并使用 fail 样式', () => {
    const wrapper = mount(KbTreeNode, {
      props: {
        node: makeDoc({ parseStatus: 'FAIL', isIndexed: false }),
        projectId: 'proj-001',
      },
    });

    const badge = wrapper.find('.kb-tree-badge');
    expect(badge.exists()).toBe(true);
    expect(badge.text()).toBe('解析失败');
    expect(badge.classes()).toContain('kb-tree-badge--fail');
  });

  it('解析成功文档常驻显示「解析成功」绿色徽章', () => {
    const wrapper = mount(KbTreeNode, {
      props: {
        node: makeDoc({ parseStatus: 'DONE', isIndexed: true }),
        projectId: 'proj-001',
      },
    });

    const badge = wrapper.find('.kb-tree-badge');
    expect(badge.exists()).toBe(true);
    expect(badge.text()).toBe('解析成功');
    expect(badge.classes()).toContain('kb-tree-badge--done');
  });

  it('文件夹节点不渲染文档徽章', () => {
    const wrapper = mount(KbTreeNode, {
      props: {
        node: {
          type: 'folder',
          id: 'folder-001',
          name: 'Root',
          children: [],
        },
        projectId: 'proj-001',
      },
    });

    expect(wrapper.find('.kb-tree-badge').exists()).toBe(false);
  });
});
