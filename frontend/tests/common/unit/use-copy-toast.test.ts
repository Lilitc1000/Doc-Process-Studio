import { describe, expect, it } from 'vitest';
import { useCopyToast } from '../../../src/composables/business/useCopyToast';
import { withSetup } from '../../helpers/composable-setup';

describe('useCopyToast', () => {
  it('初始状态：不可见', () => {
    const { copyToastTitle, copyToastMessage, isCopyToastVisible } = withSetup(
      () => useCopyToast(),
    );
    expect(isCopyToastVisible.value).toBe(false);
    expect(copyToastTitle.value).toBe('复制成功');
    expect(copyToastMessage.value).toBe('复制成功');
  });

  it('showCopyToast 设置消息并显示', () => {
    const { showCopyToast, copyToastMessage, isCopyToastVisible } = withSetup(
      () => useCopyToast(),
    );
    showCopyToast('已复制到剪贴板');
    expect(isCopyToastVisible.value).toBe(true);
    expect(copyToastMessage.value).toBe('已复制到剪贴板');
  });

  it('showCopyToast 可自定义标题', () => {
    const { showCopyToast, copyToastTitle } = withSetup(() => useCopyToast());
    showCopyToast('内容', { title: '自定义标题' });
    expect(copyToastTitle.value).toBe('自定义标题');
  });

  it('showCopyToast 标题为空时使用默认', () => {
    const { showCopyToast, copyToastTitle } = withSetup(() => useCopyToast());
    showCopyToast('内容', { title: '   ' });
    expect(copyToastTitle.value).toBe('复制成功');
  });

  it('showCopyToast 标题未提供时使用默认', () => {
    const { showCopyToast, copyToastTitle } = withSetup(() => useCopyToast());
    showCopyToast('内容');
    expect(copyToastTitle.value).toBe('复制成功');
  });

  it('多次调用 showCopyToast 更新消息', () => {
    const { showCopyToast, copyToastMessage } = withSetup(() => useCopyToast());
    showCopyToast('消息1');
    expect(copyToastMessage.value).toBe('消息1');
    showCopyToast('消息2');
    expect(copyToastMessage.value).toBe('消息2');
  });
});
