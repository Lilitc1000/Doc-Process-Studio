import { describe, expect, it } from 'vitest';
import {
  formatFileSize,
  getFileTypeVisual,
} from '../../../src/utils/common/file';
import {
  FILE_TYPE_VISUALS,
  FILE_EXTENSION_VISUAL_MAP,
  MIME_TYPE_CATEGORY_MAP,
} from '../../../src/utils/common/file-type-visuals';

describe('formatFileSize', () => {
  it('小于 1KB 显示字节', () => {
    expect(formatFileSize(0)).toBe('0 B');
    expect(formatFileSize(512)).toBe('512 B');
    expect(formatFileSize(1023)).toBe('1023 B');
  });

  it('1KB 到 1MB 之间显示 KB', () => {
    expect(formatFileSize(1024)).toBe('1.0 KB');
    expect(formatFileSize(1536)).toBe('1.5 KB');
    expect(formatFileSize(1048575)).toBe('1024.0 KB');
  });

  it('大于等于 1MB 显示 MB', () => {
    expect(formatFileSize(1048576)).toBe('1.0 MB');
    expect(formatFileSize(5242880)).toBe('5.0 MB');
  });

  it('接受 File 对象', () => {
    const file = new File([''], 'test.txt', { type: 'text/plain' });
    Object.defineProperty(file, 'size', { value: 2048 });
    expect(formatFileSize(file)).toBe('2.0 KB');
  });

  it('接受数字参数', () => {
    expect(formatFileSize(500)).toBe('500 B');
  });
});

describe('getFileTypeVisual', () => {
  it('根据 MIME 类型识别 PDF', () => {
    const visual = getFileTypeVisual('report.pdf', 'application/pdf');
    expect(visual.badge).toBe('PDF');
    expect(visual.label).toBe('PDF 文档');
  });

  it('根据 MIME 类型识别 Word', () => {
    const visual = getFileTypeVisual(
      'doc.docx',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    );
    expect(visual.badge).toBe('DOC');
    expect(visual.label).toBe('Word 文档');
  });

  it('根据 MIME 类型识别 Excel', () => {
    const visual = getFileTypeVisual(
      'data.xlsx',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    );
    expect(visual.badge).toBe('XLS');
  });

  it('根据 MIME 类型识别 ZIP', () => {
    const visual = getFileTypeVisual('archive.zip', 'application/zip');
    expect(visual.badge).toBe('ZIP');
  });

  it('根据 MIME 类型识别 JSON', () => {
    const visual = getFileTypeVisual('data.json', 'application/json');
    expect(visual.badge).toBe('JSON');
  });

  it('根据 MIME 类型识别 Markdown', () => {
    const visual = getFileTypeVisual('readme.md', 'text/markdown');
    expect(visual.badge).toBe('MD');
  });

  it('根据 MIME 类型识别纯文本', () => {
    const visual = getFileTypeVisual('notes.txt', 'text/plain');
    expect(visual.badge).toBe('TXT');
  });

  it('根据 MIME 类型前缀识别 image/*', () => {
    const visual = getFileTypeVisual('photo.png', 'image/png');
    expect(visual.badge).toBe('IMG');
  });

  it('根据 MIME 类型前缀识别 audio/*', () => {
    const visual = getFileTypeVisual('song.mp3', 'audio/mpeg');
    expect(visual.badge).toBe('AUD');
  });

  it('根据 MIME 类型前缀识别 video/*', () => {
    const visual = getFileTypeVisual('clip.mp4', 'video/mp4');
    expect(visual.badge).toBe('VID');
  });

  it('根据 MIME 类型前缀识别 text/*', () => {
    const visual = getFileTypeVisual('data.csv', 'text/csv');
    expect(visual.badge).toBe('XLS');
  });

  it('根据扩展名识别文件类型', () => {
    expect(getFileTypeVisual('script.py').badge).toBe('PY');
    expect(getFileTypeVisual('app.java').badge).toBe('JAVA');
    expect(getFileTypeVisual('main.go').badge).toBe('GO');
    expect(getFileTypeVisual('lib.rs').badge).toBe('RS');
    expect(getFileTypeVisual('index.html').badge).toBe('HTML');
    expect(getFileTypeVisual('style.css').badge).toBe('CSS');
    expect(getFileTypeVisual('app.vue').badge).toBe('VUE');
    expect(getFileTypeVisual('config.yaml').badge).toBe('YAML');
    expect(getFileTypeVisual('data.sql').badge).toBe('SQL');
    expect(getFileTypeVisual('run.sh').badge).toBe('SH');
  });

  it('无扩展名返回 file 类型', () => {
    const visual = getFileTypeVisual('README');
    expect(visual.badge).toBe('FILE');
  });

  it('未知扩展名返回 file 类型', () => {
    const visual = getFileTypeVisual('data.xyz');
    expect(visual.badge).toBe('FILE');
  });

  it('MIME 类型优先于扩展名', () => {
    const visual = getFileTypeVisual('data.txt', 'application/pdf');
    expect(visual.badge).toBe('PDF');
  });
});

describe('FILE_TYPE_VISUALS', () => {
  it('每个类别都有 badge、label、color、background、border', () => {
    for (const [, visual] of Object.entries(FILE_TYPE_VISUALS)) {
      expect(visual.badge).toBeTruthy();
      expect(visual.label).toBeTruthy();
      expect(visual.color).toMatch(/^#/);
      expect(visual.background).toBeTruthy();
      expect(visual.border).toBeTruthy();
    }
  });

  it('包含 file 默认类别', () => {
    expect(FILE_TYPE_VISUALS.file).toBeDefined();
    expect(FILE_TYPE_VISUALS.file.badge).toBe('FILE');
  });
});

describe('FILE_EXTENSION_VISUAL_MAP', () => {
  it('所有映射值都在 FILE_TYPE_VISUALS 中存在', () => {
    for (const [, category] of Object.entries(FILE_EXTENSION_VISUAL_MAP)) {
      expect(FILE_TYPE_VISUALS[category]).toBeDefined();
    }
  });

  it('包含常见扩展名映射', () => {
    expect(FILE_EXTENSION_VISUAL_MAP.pdf).toBe('pdf');
    expect(FILE_EXTENSION_VISUAL_MAP.docx).toBe('word');
    expect(FILE_EXTENSION_VISUAL_MAP.xlsx).toBe('excel');
    expect(FILE_EXTENSION_VISUAL_MAP.py).toBe('python');
    expect(FILE_EXTENSION_VISUAL_MAP.ts).toBe('typescript');
    expect(FILE_EXTENSION_VISUAL_MAP.js).toBe('javascript');
  });
});

describe('MIME_TYPE_CATEGORY_MAP', () => {
  it('所有映射值都在 FILE_TYPE_VISUALS 中存在', () => {
    for (const [, category] of Object.entries(MIME_TYPE_CATEGORY_MAP)) {
      expect(FILE_TYPE_VISUALS[category]).toBeDefined();
    }
  });

  it('包含常见 MIME 类型映射', () => {
    expect(MIME_TYPE_CATEGORY_MAP['application/pdf']).toBe('pdf');
    expect(MIME_TYPE_CATEGORY_MAP['application/json']).toBe('json');
    expect(MIME_TYPE_CATEGORY_MAP['text/plain']).toBe('text');
  });
});
