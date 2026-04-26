import { describe, expect, it, vi, beforeEach } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { createRouter, createMemoryHistory } from 'vue-router';
import IncidentReportDetailView from '../../../src/views/incident-report/detail/IncidentReportDetailView.vue';

vi.mock('../../../src/api/incident-report', () => ({
  fetchIncidentReportDetail: vi.fn().mockResolvedValue({
    id: 'rep-1',
    ref_no: 'DAS-001',
    title: '测试报告',
    status: 'pending',
    severity: 'P1',
    reporter_id: 'usr-1',
    reporter_name: '张三',
    assignee_id: null,
    assignee_name: null,
    verifier_id: null,
    verifier_name: null,
    fault_date: '2026-04-20',
    created_at: '2026-04-20T10:00:00Z',
    updated_at: '2026-04-20T10:00:00Z',
    system: '数据库系统',
    site_id: 'SITE-01',
    form_data: { description: '数据库连接超时' },
    report_data: null,
    submitted_at: '2026-04-20T11:00:00Z',
    approved_at: null,
    closed_at: null,
    resolution_date: null,
  }),
  fetchIncidentReportAuditLogs: vi.fn().mockResolvedValue([
    { id: 'log-1', action: 'create', actor_id: 'usr-1', actor_name: null, from_status: null, to_status: 'draft', comment: null, created_at: '2026-04-20T10:00:00Z' },
    { id: 'log-2', action: 'submit', actor_id: 'usr-1', actor_name: null, from_status: 'draft', to_status: 'pending', comment: null, created_at: '2026-04-20T11:00:00Z' },
  ]),
  fetchIncidentReportComments: vi.fn().mockResolvedValue([]),
  createIncidentReportComment: vi.fn(),
  closeIncidentReport: vi.fn(),
  reopenIncidentReport: vi.fn(),
  fetchUserIncidentRoles: vi.fn().mockResolvedValue(['reporter', 'verifier']),
}));

describe('IncidentReportDetailView', () => {
  let router: ReturnType<typeof createRouter>;

  beforeEach(() => {
    vi.clearAllMocks();
    setActivePinia(createPinia());
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/incident-report/:id', component: { template: '<div />' } },
      ],
    });
  });

  it('渲染报告详情', async () => {
    router.push('/incident-report/rep-1');
    await router.isReady();

    const wrapper = mount(IncidentReportDetailView, {
      global: {
        plugins: [router],
        stubs: {
          BaseButton: { template: '<button @click="$emit(\'click\')"><slot /></button>', props: ['variant', 'size', 'disabled'] },
          ReportStatusBadge: { template: '<span class="status-badge">{{ status }}</span>', props: ['status'] },
          ReportAuditTimeline: { template: '<div class="audit-timeline" />', props: ['auditLogs'] },
          ReportDetailContent: { template: '<div class="detail-content" />', props: ['report'] },
          ReportComments: { template: '<div class="report-comments" />', props: ['reportId', 'comments'] },
        },
      },
    });

    await flushPromises();

    expect(wrapper.find('.detail-ref').text()).toBe('DAS-001');
    expect(wrapper.find('.detail-title').text()).toBe('测试报告');
  });

  it('verifier 角色可以看到审核按钮', async () => {
    router.push('/incident-report/rep-1');
    await router.isReady();

    const wrapper = mount(IncidentReportDetailView, {
      global: {
        plugins: [router],
        stubs: {
          BaseButton: { template: '<button @click="$emit(\'click\')"><slot /></button>', props: ['variant', 'size', 'disabled'] },
          ReportStatusBadge: { template: '<span class="status-badge">{{ status }}</span>', props: ['status'] },
          ReportAuditTimeline: { template: '<div />', props: ['auditLogs'] },
          ReportDetailContent: { template: '<div />', props: ['report'] },
          ReportComments: { template: '<div />', props: ['reportId', 'comments'] },
        },
      },
    });

    await flushPromises();

    const text = wrapper.text();
    expect(text).toContain('审核');
  });
});
