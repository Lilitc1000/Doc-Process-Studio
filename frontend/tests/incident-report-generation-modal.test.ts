import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import IncidentReportWorkspace from '../src/components/IncidentReportWorkspace.vue';

const buildSession = () => ({
  id: 'incident-session-1',
  title: '事故报告-2026/04/14 12:30',
  status: 'generated',
  created_at: '2026-04-14T12:30:00Z',
  updated_at: '2026-04-14T12:40:00Z',
  snapshot: {
    form_answers: {
      manual_fault_date: {
        value: '2026-03-12',
        custom_value: '',
      },
      manual_fault_time: {
        value: '15:00',
        custom_value: '',
      },
      manual_reporting_person: {
        value: 'SOC',
        custom_value: '',
      },
      manual_site_id: {
        value: 'CHT',
        custom_value: '',
      },
      manual_system: {
        value: 'Order Service',
        custom_value: '',
      },
      manual_location: {
        value: 'CHT',
        custom_value: '',
      },
      manual_fault_symptom: {
        value: '客户下单报错',
        custom_value: '',
      },
      body_description: {
        value: '客户反馈下单报错，定位数据库 CPU 打满。',
        custom_value: '',
      },
      body_timeline: {
        value: [
          {
            time: '15:00',
            event: '客户报错',
            resolution: '服务降级',
            evidence: '监控告警',
          },
        ],
        custom_value: '',
      },
      body_impact_scope: {
        value: '下单链路',
        custom_value: '',
      },
      body_impact_severity: {
        value: 'High',
        custom_value: '',
      },
      body_root_cause: {
        value: '慢查询缺失索引',
        custom_value: '',
      },
      body_follow_up_actions: {
        value: '加强 code review',
        custom_value: '',
      },
      quick_narrative: {
        value: '3月12日下午3点客户下单报错。',
        custom_value: '',
      },
    },
    report_data: null,
    generated_attachment: {
      attachment_id: 'incident-attachment-1',
      name: 'incident-report-v1.docx',
      source: 'generated',
      size_label: '20 KB',
      download_url: '/api/attachments/incident-attachment-1/download',
      mime_type:
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      expires_at: '2026-04-15T00:00:00Z',
    },
    generated_versions: [
      {
        version: 1,
        label: 'V1 2026-04-14 12:40:00',
        generated_at: '2026-04-14T12:40:00Z',
        attachment: {
          attachment_id: 'incident-attachment-1',
          name: 'incident-report-v1.docx',
          source: 'generated',
          size_label: '20 KB',
          download_url: '/api/attachments/incident-attachment-1/download',
          mime_type:
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          expires_at: '2026-04-15T00:00:00Z',
        },
        report_data: {
          reference_no: 'DAS-20260312-001',
          detailed_description: '客户下单报错。',
          affected_date_summary: '12/03/2026 15:00 - 12/03/2026 16:00',
          event_sequence: [{ time: '12/03/2026 15:00', event: '客户报错' }],
          impact: { systems: '下单链路', severity: 'High' },
          root_cause: '慢查询缺失索引',
          preventive_actions: [{ action: '加强 code review' }],
        },
      },
    ],
    generated_trace_id: 'trace-quick-1',
    section_trace_ids: { quick: 'trace-quick-1' },
    generated_at: '2026-04-14T12:40:00Z',
    is_locked: false,
    fallback_used: false,
    polish_error: null,
  },
});

describe('incident report generation modal', () => {
  it('支持快填生成事件与实时预览下载', async () => {
    const wrapper = mount(IncidentReportWorkspace, {
      global: {
        stubs: {
          teleport: true,
        },
      },
      props: {
        schema: null,
        session: buildSession(),
        isGenerating: false,
        generationState: 'idle',
        previewDocxBase64: 'ZHVtbXk=',
      },
    });

    const quickGenerateButton = wrapper
      .findAll('button')
      .find((node) => node.text().includes('一键生成正文'));
    expect(quickGenerateButton).toBeTruthy();
    await quickGenerateButton!.trigger('click');
    expect(wrapper.emitted('quick-generate-body')).toHaveLength(1);

    const previewButton = wrapper
      .findAll('button')
      .find((node) => node.text().includes('预览附件'));
    expect(previewButton).toBeTruthy();
    await previewButton!.trigger('click');
    expect(wrapper.text()).toContain('附件预览');
    expect(wrapper.emitted('request-preview')).toHaveLength(1);

    const downloadButton = wrapper
      .findAll('button')
      .find((node) => node.text().includes('下载当前预览文档'));
    expect(downloadButton).toBeTruthy();
    await downloadButton!.trigger('click');
    expect(wrapper.emitted('download-preview-docx')).toHaveLength(1);
  });
});
