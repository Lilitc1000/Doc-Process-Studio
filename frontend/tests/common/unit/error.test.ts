import { describe, expect, it } from 'vitest';
import { getErrorMessage } from '../../../src/utils/common/error';

describe('getErrorMessage', () => {
  it('返回 Error 实例的 message', () => {
    const error = new Error('网络请求失败');
    expect(getErrorMessage(error, '默认消息')).toBe('网络请求失败');
  });

  it('非 Error 实例返回 fallback', () => {
    expect(getErrorMessage('string error', '默认消息')).toBe('默认消息');
  });

  it('null 返回 fallback', () => {
    expect(getErrorMessage(null, '默认消息')).toBe('默认消息');
  });

  it('undefined 返回 fallback', () => {
    expect(getErrorMessage(undefined, '默认消息')).toBe('默认消息');
  });

  it('数字返回 fallback', () => {
    expect(getErrorMessage(42, '默认消息')).toBe('默认消息');
  });

  it('对象返回 fallback', () => {
    expect(getErrorMessage({ message: 'test' }, '默认消息')).toBe('默认消息');
  });

  it('TypeError 实例返回 message', () => {
    const error = new TypeError('类型错误');
    expect(getErrorMessage(error, '默认消息')).toBe('类型错误');
  });

  it('RangeError 实例返回 message', () => {
    const error = new RangeError('范围错误');
    expect(getErrorMessage(error, '默认消息')).toBe('范围错误');
  });
});
