import { describe, expect, it, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import ReportStatusBadge from '@modules/incident-report/views/components/ReportStatusBadge.vue';

describe('ReportStatusBadge', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('渲染草稿状态', () => {
    const wrapper = mount(ReportStatusBadge, {
      props: { status: 'draft' },
    });
    expect(wrapper.text()).toBe('草稿');
    expect(wrapper.find('.status-draft').exists()).toBe(true);
  });

  it('渲染待审核状态', () => {
    const wrapper = mount(ReportStatusBadge, {
      props: { status: 'pending' },
    });
    expect(wrapper.text()).toBe('待审核');
    expect(wrapper.find('.status-pending').exists()).toBe(true);
  });

  it('渲染已批准状态', () => {
    const wrapper = mount(ReportStatusBadge, {
      props: { status: 'approved' },
    });
    expect(wrapper.text()).toBe('已批准');
    expect(wrapper.find('.status-approved').exists()).toBe(true);
  });

  it('渲染已驳回状态', () => {
    const wrapper = mount(ReportStatusBadge, {
      props: { status: 'rejected' },
    });
    expect(wrapper.text()).toBe('已驳回');
    expect(wrapper.find('.status-rejected').exists()).toBe(true);
  });

  it('渲染处理中状态', () => {
    const wrapper = mount(ReportStatusBadge, {
      props: { status: 'in_progress' },
    });
    expect(wrapper.text()).toBe('处理中');
    expect(wrapper.find('.status-in-progress').exists()).toBe(true);
  });

  it('渲染已关闭状态', () => {
    const wrapper = mount(ReportStatusBadge, {
      props: { status: 'closed' },
    });
    expect(wrapper.text()).toBe('已关闭');
    expect(wrapper.find('.status-closed').exists()).toBe(true);
  });
});
