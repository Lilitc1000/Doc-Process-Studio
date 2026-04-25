import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import PasswordInput from '../../../src/components/base/PasswordInput.vue';

describe('PasswordInput', () => {
  it('默认类型为 password', () => {
    const wrapper = mount(PasswordInput, {
      props: { modelValue: 'secret' },
    });
    const input = wrapper.find('input');
    expect(input.attributes('type')).toBe('password');
  });

  it('点击切换按钮后类型变为 text', async () => {
    const wrapper = mount(PasswordInput, {
      props: { modelValue: 'secret' },
    });
    const toggleBtn = wrapper.find('.password-toggle-btn');
    await toggleBtn.trigger('click');

    const input = wrapper.find('input');
    expect(input.attributes('type')).toBe('text');
  });

  it('再次点击切换按钮后类型变回 password', async () => {
    const wrapper = mount(PasswordInput, {
      props: { modelValue: 'secret' },
    });
    const toggleBtn = wrapper.find('.password-toggle-btn');

    await toggleBtn.trigger('click');
    expect(wrapper.find('input').attributes('type')).toBe('text');

    await toggleBtn.trigger('click');
    expect(wrapper.find('input').attributes('type')).toBe('password');
  });

  it('渲染切换按钮', () => {
    const wrapper = mount(PasswordInput, {
      props: { modelValue: 'secret' },
    });
    expect(wrapper.find('.password-toggle-btn').exists()).toBe(true);
  });
});
