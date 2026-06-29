import { describe, expect, it } from 'vitest';
import { isRequestCanceled } from '@shared/utils/cancel';

describe('isRequestCanceled', () => {
  it('识别 DOMException AbortError', () => {
    const error = new DOMException('The operation was aborted.', 'AbortError');
    expect(isRequestCanceled(error)).toBe(true);
  });

  it('识别 code 为 ERR_CANCELED 的对象', () => {
    const error = { code: 'ERR_CANCELED' };
    expect(isRequestCanceled(error)).toBe(true);
  });

  it('识别 name 为 CanceledError 的对象', () => {
    const error = { name: 'CanceledError' };
    expect(isRequestCanceled(error)).toBe(true);
  });

  it('普通 Error 不被识别为取消', () => {
    const error = new Error('Something went wrong');
    expect(isRequestCanceled(error)).toBe(false);
  });

  it('null 不被识别为取消', () => {
    expect(isRequestCanceled(null)).toBe(false);
  });

  it('undefined 不被识别为取消', () => {
    expect(isRequestCanceled(undefined)).toBe(false);
  });

  it('字符串不被识别为取消', () => {
    expect(isRequestCanceled('AbortError')).toBe(false);
  });

  it('其他 code 的对象不被识别为取消', () => {
    const error = { code: 'ERR_NETWORK' };
    expect(isRequestCanceled(error)).toBe(false);
  });

  it('其他 name 的对象不被识别为取消', () => {
    const error = { name: 'TypeError' };
    expect(isRequestCanceled(error)).toBe(false);
  });
});
