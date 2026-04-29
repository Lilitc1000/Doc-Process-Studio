import { describe, expect, it, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import StatsCards from '../../../src/views/incident-report/analytics/components/StatsCards.vue';
import type { IncidentAnalyticsOverview } from '../../../src/types/incident-report/incident-report';

describe('StatsCards', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('渲染概览数据', () => {
    const overview: IncidentAnalyticsOverview = {
      totalThisMonth: 10,
      pendingCount: 3,
      inProgressCount: 2,
      closedThisMonth: 5,
      avgResolutionHours: 24.5,
    };

    const wrapper = mount(StatsCards, {
      props: { overview },
    });

    expect(wrapper.text()).toContain('10');
    expect(wrapper.text()).toContain('3');
    expect(wrapper.text()).toContain('2');
    expect(wrapper.text()).toContain('5');
  });

  it('overview 为 null 时显示 0', () => {
    const wrapper = mount(StatsCards, {
      props: { overview: null },
    });

    expect(wrapper.text()).toContain('0');
  });
});
