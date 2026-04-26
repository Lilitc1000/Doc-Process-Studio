import { describe, expect, it, vi, beforeEach } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { createRouter, createMemoryHistory } from 'vue-router';
import IncidentReportListView from '../../../src/views/incident-report/list/IncidentReportListView.vue';

vi.mock('../../../src/api/incident-report', () => ({
  fetchIncidentReportList: vi.fn().mockResolvedValue({
    total: 2,
    items: [
      { id: 'rep-1', ref_no: 'DAS-001', title: '测试1', status: 'draft', severity: 'P1', reporter_id: 'usr-1', reporter_name: null, assignee_id: null, assignee_name: null, verifier_id: null, verifier_name: null, fault_date: null, created_at: '2026-04-20', updated_at: '2026-04-20' },
      { id: 'rep-2', ref_no: 'DAS-002', title: '测试2', status: 'pending', severity: 'P2', reporter_id: 'usr-2', reporter_name: null, assignee_id: null, assignee_name: null, verifier_id: null, verifier_name: null, fault_date: null, created_at: '2026-04-19', updated_at: '2026-04-19' },
    ],
  }),
  fetchUserIncidentRoles: vi.fn().mockResolvedValue(['reporter']),
  fetchIncidentAnalyticsOverview: vi.fn().mockResolvedValue({
    total_this_month: 2,
    pending_count: 1,
    in_progress_count: 0,
    closed_this_month: 1,
    avg_resolution_hours: null,
  }),
  deleteIncidentReport: vi.fn().mockResolvedValue(undefined),
}));

describe('IncidentReportListView', () => {
  let router: ReturnType<typeof createRouter>;

  beforeEach(() => {
    vi.clearAllMocks();
    setActivePinia(createPinia());
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/incident-report', component: { template: '<div />' } },
        { path: '/incident-report/create', component: { template: '<div />' } },
        { path: '/incident-report/:id', component: { template: '<div />' } },
      ],
    });
  });

  it('渲染报告列表', async () => {
    router.push('/incident-report');
    await router.isReady();

    const wrapper = mount(IncidentReportListView, {
      global: {
        plugins: [router],
        stubs: {
          BaseButton: true,
          BaseInput: true,
          BaseDropdown: true,
          BaseTextarea: true,
          ReportListStats: true,
          ReportListFilters: true,
          ReportListTable: { template: '<div class="report-list-table"><div v-for="item in items" :key="item.id" class="report-list-row">{{ item.ref_no }} {{ item.title }}</div></div>', props: ['items', 'loading', 'canDelete'] },
        },
      },
    });

    await flushPromises();

    const rows = wrapper.findAll('.report-list-row');
    expect(rows).toHaveLength(2);
  });

  it('reporter 角色可以看到新建按钮', async () => {
    router.push('/incident-report');
    await router.isReady();

    const wrapper = mount(IncidentReportListView, {
      global: {
        plugins: [router],
        stubs: {
          BaseButton: { template: '<button :class="variant" @click="$emit(\'click\')"><slot /></button>', props: ['variant', 'size', 'disabled'] },
          BaseInput: true,
          BaseDropdown: true,
          BaseTextarea: true,
          ReportListStats: true,
          ReportListFilters: true,
          ReportListTable: true,
        },
      },
    });

    await flushPromises();

    const createBtn = wrapper.find('.btn-create-report');
    expect(createBtn.exists()).toBe(true);
  });
});
