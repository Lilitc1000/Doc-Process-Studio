import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import UserAvatar from '../../../src/components/business/UserAvatar.vue';

describe('UserAvatar', () => {
  it('显示用户名首字母大写', () => {
    const wrapper = mount(UserAvatar, {
      props: { username: 'admin', color: '#4f46e5', size: 'md' },
    });
    expect(wrapper.text()).toBe('A');
  });

  it('显示用户名首字母（小写输入）', () => {
    const wrapper = mount(UserAvatar, {
      props: { username: 'testuser', color: '#ef4444', size: 'sm' },
    });
    expect(wrapper.text()).toBe('T');
  });

  it('空用户名显示问号', () => {
    const wrapper = mount(UserAvatar, {
      props: { username: '', color: '#4f46e5', size: 'md' },
    });
    expect(wrapper.text()).toBe('?');
  });

  it('应用正确的背景色', () => {
    const wrapper = mount(UserAvatar, {
      props: { username: 'admin', color: '#ef4444', size: 'md' },
    });
    expect(wrapper.find('.user-avatar').attributes('style')).toContain(
      '#ef4444',
    );
  });

  it('应用正确的尺寸类', () => {
    const sm = mount(UserAvatar, {
      props: { username: 'a', color: '#4f46e5', size: 'sm' },
    });
    expect(sm.find('.user-avatar').classes()).toContain('size-sm');

    const lg = mount(UserAvatar, {
      props: { username: 'a', color: '#4f46e5', size: 'lg' },
    });
    expect(lg.find('.user-avatar').classes()).toContain('size-lg');
  });
});
