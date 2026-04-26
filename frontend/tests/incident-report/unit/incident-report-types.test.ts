import { describe, expect, it } from 'vitest';
import {
  INCIDENT_STATUS_LABELS,
  INCIDENT_SEVERITY_LABELS,
} from '../../../src/types/incident-report/incident-report';
import type {
  IncidentReportStatus,
  IncidentSeverity,
} from '../../../src/types/incident-report/incident-report';

describe('IncidentReport 类型常量', () => {
  it('INCIDENT_STATUS_LABELS 包含所有状态', () => {
    const statuses: IncidentReportStatus[] = [
      'draft',
      'pending',
      'approved',
      'rejected',
      'in_progress',
      'closed',
    ];
    for (const status of statuses) {
      expect(INCIDENT_STATUS_LABELS[status]).toBeDefined();
      expect(typeof INCIDENT_STATUS_LABELS[status]).toBe('string');
    }
  });

  it('INCIDENT_SEVERITY_LABELS 包含所有级别', () => {
    const severities: IncidentSeverity[] = ['P0', 'P1', 'P2', 'P3'];
    for (const severity of severities) {
      expect(INCIDENT_SEVERITY_LABELS[severity]).toBeDefined();
      expect(typeof INCIDENT_SEVERITY_LABELS[severity]).toBe('string');
    }
  });

  it('状态标签为中文', () => {
    expect(INCIDENT_STATUS_LABELS.draft).toBe('草稿');
    expect(INCIDENT_STATUS_LABELS.pending).toBe('待审核');
    expect(INCIDENT_STATUS_LABELS.approved).toBe('已批准');
    expect(INCIDENT_STATUS_LABELS.rejected).toBe('已驳回');
    expect(INCIDENT_STATUS_LABELS.in_progress).toBe('处理中');
    expect(INCIDENT_STATUS_LABELS.closed).toBe('已关闭');
  });

  it('级别标签包含级别编号', () => {
    expect(INCIDENT_SEVERITY_LABELS.P0).toContain('P0');
    expect(INCIDENT_SEVERITY_LABELS.P1).toContain('P1');
    expect(INCIDENT_SEVERITY_LABELS.P2).toContain('P2');
    expect(INCIDENT_SEVERITY_LABELS.P3).toContain('P3');
  });
});
