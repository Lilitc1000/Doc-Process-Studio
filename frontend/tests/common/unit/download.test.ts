import { describe, expect, it, vi, beforeEach } from 'vitest';
import { triggerBlobDownload } from '../../../src/utils/common/download';

describe('triggerBlobDownload', () => {
  let createObjectURLSpy: ReturnType<typeof vi.fn>;
  let revokeObjectURLSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    createObjectURLSpy = vi.fn(() => 'blob:http://localhost/fake-url');
    revokeObjectURLSpy = vi.fn();
    globalThis.URL.createObjectURL = createObjectURLSpy;
    globalThis.URL.revokeObjectURL = revokeObjectURLSpy;
  });

  it('创建 Object URL 并触发下载', () => {
    const blob = new Blob(['test content'], { type: 'text/plain' });
    triggerBlobDownload(blob, 'test.txt');

    expect(createObjectURLSpy).toHaveBeenCalledWith(blob);
    expect(revokeObjectURLSpy).toHaveBeenCalledWith(
      'blob:http://localhost/fake-url',
    );
  });

  it('创建的链接有正确的 download 属性', () => {
    const blob = new Blob(['data'], { type: 'application/pdf' });
    const clickSpy = vi.fn();

    const originalCreateElement = document.createElement.bind(document);
    vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
      const el = originalCreateElement(tag);
      if (tag === 'a') {
        el.click = clickSpy;
      }
      return el;
    });

    triggerBlobDownload(blob, 'report.pdf');
    expect(clickSpy).toHaveBeenCalled();

    vi.restoreAllMocks();
  });
});
