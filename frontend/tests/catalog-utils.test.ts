import { describe, expect, it } from 'vitest';
import { extractModelNames, normalizeSkillCatalog } from '../src/utils/catalog';

describe('catalog utils', () => {
  it('提取并去重远端模型名称', () => {
    const modelNames = extractModelNames({
      models: [
        { name: ' qwen3:8b ' },
        { model: 'deepseek-r1:14b' },
        { id: 'qwen3:8b' },
        { name: '' },
      ],
    });

    expect(modelNames).toEqual(['qwen3:8b', 'deepseek-r1:14b']);
  });

  it('规范化 skill 列表并回退默认 skill', () => {
    const catalog = normalizeSkillCatalog(
      {
        skills: [
          {
            id: 'document-assistant',
            display_name: '文档助手',
            short_description: '通用文档处理',
          },
          {
            id: 'resume-review',
            displayName: '简历筛选',
          },
          {
            id: '',
            display_name: '无效 skill',
          },
        ],
      },
      'document-assistant',
    );

    expect(catalog.skills).toEqual([
      {
        id: 'document-assistant',
        displayName: '文档助手',
        shortDescription: '通用文档处理',
      },
      {
        id: 'resume-review',
        displayName: '简历筛选',
        shortDescription: '',
      },
    ]);
    expect(catalog.defaultSkillId).toBe('document-assistant');
  });
});
