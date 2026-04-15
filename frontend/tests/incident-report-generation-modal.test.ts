import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import IncidentReportWorkspace from '../src/components/IncidentReportWorkspace.vue';

describe('incident report generation modal', () => {
  it('生成中弹窗展示进度并支持停止与链路回放', async () => {
    const wrapper = mount(IncidentReportWorkspace, {
      global: {
        stubs: {
          teleport: true,
        },
      },
      props: {
        schema: null,
        session: null,
        isGenerating: true,
        generationState: 'generating',
        generationProgressLines: [
          '10:00:01 表单校验通过',
          '10:00:02 已写入 incident_data.json',
        ],
      },
    });

    expect(wrapper.text()).toContain('正在生成中，请稍候');
    expect(wrapper.text()).toContain('表单校验通过');
    expect(wrapper.text()).toContain('已写入 incident_data.json');

    const stopButton = wrapper
      .findAll('button')
      .find((node) => node.text().trim() === '停止生成');
    expect(stopButton).toBeTruthy();
    await stopButton!.trigger('click');

    expect(wrapper.emitted('stop-generation')).toHaveLength(1);
  });
});
