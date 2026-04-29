import { describe, expect, it, vi, beforeEach } from 'vitest';
import { useTraceModal } from '../../../src/composables/business/useTraceModal';
import * as traceApi from '../../../src/api/trace';

vi.mock('../../../src/api/trace', () => ({
  fetchAgentTraceReplay: vi.fn(),
}));

describe('useTraceModal', () => {
  const showCopyToast =
    vi.fn<(message: string, options?: { title?: string }) => void>();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('初始状态：模态框不可见', () => {
    const {
      isTraceModalVisible,
      isTraceModalLoading,
      activeTraceId,
      activeTracePayload,
      traceModalErrorMessage,
    } = useTraceModal({ showCopyToast });
    expect(isTraceModalVisible.value).toBe(false);
    expect(isTraceModalLoading.value).toBe(false);
    expect(activeTraceId.value).toBe('');
    expect(activeTracePayload.value).toBeNull();
    expect(traceModalErrorMessage.value).toBe('');
  });

  it('openTraceModalByTraceId 成功加载', async () => {
    const mockFetch = traceApi.fetchAgentTraceReplay as ReturnType<
      typeof vi.fn
    >;
    mockFetch.mockResolvedValue({
      payload: { traceId: 'trace-123', rounds: [] },
    });

    const {
      openTraceModalByTraceId,
      isTraceModalVisible,
      activeTracePayload,
      isTraceModalLoading,
    } = useTraceModal({ showCopyToast });
    await openTraceModalByTraceId('trace-123');

    expect(isTraceModalVisible.value).toBe(true);
    expect(activeTracePayload.value).toEqual({
      traceId: 'trace-123',
      rounds: [],
    });
    expect(isTraceModalLoading.value).toBe(false);
  });

  it('openTraceModalByTraceId 空字符串不打开', async () => {
    const { openTraceModalByTraceId, isTraceModalVisible } = useTraceModal({
      showCopyToast,
    });
    await openTraceModalByTraceId('');
    expect(isTraceModalVisible.value).toBe(false);
  });

  it('openTraceModalByTraceId 空白字符串不打开', async () => {
    const { openTraceModalByTraceId, isTraceModalVisible } = useTraceModal({
      showCopyToast,
    });
    await openTraceModalByTraceId('   ');
    expect(isTraceModalVisible.value).toBe(false);
  });

  it('openTraceModalByTraceId 失败时设置错误消息', async () => {
    const mockFetch = traceApi.fetchAgentTraceReplay as ReturnType<
      typeof vi.fn
    >;
    mockFetch.mockRejectedValue(new Error('服务器错误'));

    const {
      openTraceModalByTraceId,
      traceModalErrorMessage,
      isTraceModalVisible,
    } = useTraceModal({ showCopyToast });
    await openTraceModalByTraceId('trace-err');

    expect(isTraceModalVisible.value).toBe(true);
    expect(traceModalErrorMessage.value).toBe('服务器错误');
  });

  it('openTraceModalByTraceId 非 Error 失败时使用默认消息', async () => {
    const mockFetch = traceApi.fetchAgentTraceReplay as ReturnType<
      typeof vi.fn
    >;
    mockFetch.mockRejectedValue('unknown error');

    const { openTraceModalByTraceId, traceModalErrorMessage } = useTraceModal({
      showCopyToast,
    });
    await openTraceModalByTraceId('trace-err2');

    expect(traceModalErrorMessage.value).toBe('加载链路回放失败，请稍后重试。');
  });

  it('closeTraceModal 关闭模态框', () => {
    const { closeTraceModal, isTraceModalVisible } = useTraceModal({
      showCopyToast,
    });
    const mockFetch = traceApi.fetchAgentTraceReplay as ReturnType<
      typeof vi.fn
    >;
    mockFetch.mockResolvedValue({ payload: {} });

    closeTraceModal();
    expect(isTraceModalVisible.value).toBe(false);
  });

  it('retryTraceModalLoad 重新加载', async () => {
    const mockFetch = traceApi.fetchAgentTraceReplay as ReturnType<
      typeof vi.fn
    >;
    mockFetch.mockResolvedValue({
      payload: { traceId: 'trace-retry', rounds: [] },
    });

    const { openTraceModalByTraceId, retryTraceModalLoad } = useTraceModal({
      showCopyToast,
    });
    await openTraceModalByTraceId('trace-retry');
    await retryTraceModalLoad();

    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it('copyTraceId 调用剪贴板和 toast', async () => {
    const mockFetch = traceApi.fetchAgentTraceReplay as ReturnType<
      typeof vi.fn
    >;
    mockFetch.mockResolvedValue({ payload: {} });

    Object.defineProperty(navigator, 'clipboard', {
      value: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
      writable: true,
      configurable: true,
    });

    const { openTraceModalByTraceId, copyTraceId } = useTraceModal({
      showCopyToast,
    });
    await openTraceModalByTraceId('trace-copy');
    await copyTraceId();

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('trace-copy');
    expect(showCopyToast).toHaveBeenCalledWith('trace-copy', {
      title: 'Trace ID 已复制',
    });
  });

  it('404 错误会重试', async () => {
    const mockFetch = traceApi.fetchAgentTraceReplay as ReturnType<
      typeof vi.fn
    >;
    const error404 = { response: { status: 404 } };
    mockFetch
      .mockRejectedValueOnce(error404)
      .mockResolvedValueOnce({ payload: { traceId: 'trace-404' } });

    const { openTraceModalByTraceId } = useTraceModal({
      showCopyToast,
    });
    await openTraceModalByTraceId('trace-404');

    expect(mockFetch).toHaveBeenCalled();
  });
});
