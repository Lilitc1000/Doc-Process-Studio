import { describe, expect, it, vi, beforeEach } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { createRouter, createMemoryHistory } from 'vue-router';
import IncidentReportDetailView from '@modules/incident-report/views/detail/IncidentReportDetailView.vue';

vi.mock('@modules/incident-report', async (importOriginal) => {
  const original =
    await importOriginal<typeof import('@modules/incident-report')>();
  return {
    ...original,
    fetchIncidentReportDetail: vi.fn().mockResolvedValue({
      id: 'rep-1',
      refNo: 'DAS-001',
      title: '测试报告',
      status: 'pending',
      severity: 'P1',
      reporterId: 'usr-1',
      reporterName: '张三',
      assigneeId: null,
      assigneeName: null,
      verifierId: null,
      verifierName: null,
      faultDate: '2026-04-20',
      createdAt: '2026-04-20T10:00:00Z',
      updatedAt: '2026-04-20T10:00:00Z',
      system: '数据库系统',
      siteId: 'SITE-01',
      formData: { description: '数据库连接超时' },
      reportData: null,
      submittedAt: '2026-04-20T11:00:00Z',
      approvedAt: null,
      closedAt: null,
      resolutionDate: null,
    }),
    fetchIncidentReportAuditLogs: vi.fn().mockResolvedValue([
      {
        id: 'log-1',
        action: 'create',
        actorId: 'usr-1',
        actorName: null,
        fromStatus: null,
        toStatus: 'draft',
        comment: null,
        createdAt: '2026-04-20T10:00:00Z',
      },
      {
        id: 'log-2',
        action: 'submit',
        actorId: 'usr-1',
        actorName: null,
        fromStatus: 'draft',
        toStatus: 'pending',
        comment: null,
        createdAt: '2026-04-20T11:00:00Z',
      },
    ]),
    fetchIncidentReportComments: vi.fn().mockResolvedValue([]),
    createIncidentReportComment: vi.fn(),
    closeIncidentReport: vi.fn(),
    reopenIncidentReport: vi.fn(),
    fetchUserIncidentRolesAndPermissions: vi.fn().mockResolvedValue({
      roles: ['reporter', 'verifier'],
      permissions: [
        'report:create',
        'report:edit_own',
        'report:submit',
        'report:audit',
        'report:assign',
      ],
    }),
  };
});

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
          BaseButton: {
            template: '<button @click="$emit(\'click\')"><slot /></button>',
            props: ['variant', 'size', 'disabled'],
          },
          ReportStatusBadge: {
            template: '<span class="status-badge">{{ status }}</span>',
            props: ['status'],
          },
          ReportAuditTimeline: {
            template: '<div class="audit-timeline" />',
            props: ['auditLogs'],
          },
          ReportDetailContent: {
            template: '<div class="detail-content" />',
            props: ['report'],
          },
          ReportComments: {
            template: '<div class="report-comments" />',
            props: ['reportId', 'comments'],
          },
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
          BaseButton: {
            template: '<button @click="$emit(\'click\')"><slot /></button>',
            props: ['variant', 'size', 'disabled'],
          },
          ReportStatusBadge: {
            template: '<span class="status-badge">{{ status }}</span>',
            props: ['status'],
          },
          ReportAuditTimeline: { template: '<div />', props: ['auditLogs'] },
          ReportDetailContent: { template: '<div />', props: ['report'] },
          ReportComments: {
            template: '<div />',
            props: ['reportId', 'comments'],
          },
        },
      },
    });

    await flushPromises();

    const text = wrapper.text();
    expect(text).toContain('审核');
  });
});
