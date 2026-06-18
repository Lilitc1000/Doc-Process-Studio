<template>
  <section class="incident-report-edit-view">
    <div v-if="loading" class="edit-loading">加载中...</div>
    <div v-else-if="!report" class="edit-empty">报告不存在</div>
    <template v-else>
      <div class="edit-header">
        <base-button
          variant="ghost"
          size="sm"
          @click="router.push('/incident-report')"
        >
          <svg
            viewBox="0 0 20 20"
            width="16"
            height="16"
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M12.5 15L7.5 10L12.5 5" />
          </svg>
          返回列表
        </base-button>
        <h1>编辑报告 / Edit Report - {{ report.refNo }}</h1>
        <div class="edit-header-actions">
          <base-button
            variant="ghost"
            size="sm"
            :disabled="downloadingDocx"
            @click="handleDownloadDocx"
          >
            <svg
              viewBox="0 0 20 20"
              width="14"
              height="14"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M10 3V13M10 13L6.5 9.5M10 13L13.5 9.5M3 16H17" />
            </svg>
            {{ downloadingDocx ? '生成中...' : '下载 Word' }}
          </base-button>
        </div>
      </div>

      <div class="wizard-steps">
        <div
          v-for="(step, index) in EDIT_WIZARD_STEPS"
          :key="step.key"
          :class="[
            'wizard-step',
            {
              active: currentStep === index,
              completed: currentStep > index,
              clickable: currentStep > index || currentStep === index - 1,
            },
          ]"
          @click="
            (currentStep > index || currentStep === index - 1) &&
            (currentStep = index as EditWizardStep)
          "
        >
          <span class="step-number">{{ index + 1 }}</span>
          <span class="step-label">{{ step.label }}</span>
        </div>
      </div>

      <div class="wizard-content">
        <div v-if="currentStep === 0" class="step-form zone-card">
          <div class="section-heading">
            <h3>SECTION A - 故障记录 / Fault Details</h3>
          </div>
          <div class="zone-grid two-column">
            <label class="field-item">
              <span>报告标题 / Report Title *</span>
              <base-input
                v-model="formData.title"
                placeholder="请输入报告标题"
              />
            </label>
            <label class="field-item">
              <span>参考编号 / Reference No.</span>
              <base-input
                v-model="formAnswers.manual_reference_no"
                placeholder="例如：DAS2 Fault Log Form-015"
              />
            </label>
            <label class="field-item">
              <span>故障上报日期 / Date of Fault Reporting *</span>
              <base-date-time-picker
                mode="date"
                placeholder="选择日期"
                :model-value="formData.faultDate"
                @update:model-value="formData.faultDate = $event"
              />
            </label>
            <label class="field-item">
              <span>故障上报时间 / Time of Fault Reporting</span>
              <base-date-time-picker
                mode="time"
                placeholder="选择时间"
                :model-value="formAnswers.manual_fault_time"
                @update:model-value="formAnswers.manual_fault_time = $event"
              />
            </label>
            <label class="field-item">
              <span>报告人 / Reporting Person *</span>
              <base-input
                v-model="formAnswers.manual_reporting_person"
                placeholder="报告人姓名"
              />
            </label>
            <label class="field-item">
              <span>审核人 / Verified By</span>
              <base-input
                v-model="formAnswers.manual_verified_by"
                placeholder="审核人姓名"
              />
            </label>
            <label class="field-item">
              <span>站点编号 / Site ID *</span>
              <base-input v-model="formData.siteId" placeholder="如：SITE-01" />
            </label>
            <label class="field-item">
              <span>系统 / 子系统 / System / Subsystems *</span>
              <base-input
                v-model="formData.system"
                placeholder="如：数据库系统"
              />
            </label>
            <label class="field-item">
              <span>故障位置 / Location of Fault *</span>
              <base-input
                v-model="formAnswers.manual_location"
                placeholder="故障发生位置"
              />
            </label>
            <label class="field-item full-width">
              <span>故障现象详情 / Details of Fault Symptom *</span>
              <base-textarea
                v-model="formAnswers.manual_fault_symptom"
                rows="3"
                placeholder="请详细描述故障现象..."
              />
            </label>
            <label class="field-item">
              <span>到场时间 / Arrival Datetime</span>
              <base-date-time-picker
                mode="datetime"
                :model-value="formAnswers.manual_arrival_datetime"
                @update:model-value="
                  formAnswers.manual_arrival_datetime = $event
                "
              />
            </label>
            <label class="field-item">
              <span>恢复时间 / Clearance Datetime</span>
              <base-date-time-picker
                mode="datetime"
                :model-value="formAnswers.manual_clearance_datetime"
                @update:model-value="
                  formAnswers.manual_clearance_datetime = $event
                "
              />
            </label>
            <label class="field-item">
              <span>维护人员 / Service Person</span>
              <base-input
                v-model="formAnswers.manual_service_person"
                placeholder="维护人员姓名"
              />
            </label>
            <label class="field-item">
              <span>故障原因 / Fault Cause</span>
              <base-input
                v-model="formAnswers.manual_fault_cause"
                placeholder="故障原因"
              />
            </label>
            <label class="field-item">
              <span>使用物料 / Materials Used</span>
              <base-input
                v-model="formAnswers.manual_materials_used"
                placeholder="使用的物料"
              />
            </label>
          </div>

          <div class="section-heading section-heading--spaced">
            <h3>SECTION B - 维修与验证 / Repair Works & Verification</h3>
          </div>
          <div class="zone-grid two-column">
            <label class="field-item full-width">
              <span>维修详情 / Repair Details</span>
              <base-textarea
                v-model="formAnswers.manual_repair_details"
                rows="3"
                placeholder="请描述维修过程..."
              />
            </label>
            <label class="field-item">
              <span>承包商人员 / Contractor Staff</span>
              <base-input
                v-model="formAnswers.manual_contractor_staff"
                placeholder="承包商人员"
              />
            </label>
            <label class="field-item">
              <span>承包商签名 / Contractor Signature</span>
              <base-input
                v-model="formAnswers.manual_contractor_signature"
                placeholder="签名"
              />
            </label>
            <label class="field-item">
              <span>承包商日期 / Contractor Date</span>
              <base-date-time-picker
                mode="date"
                placeholder="选择日期"
                :model-value="formAnswers.manual_contractor_date"
                @update:model-value="
                  formAnswers.manual_contractor_date = $event
                "
              />
            </label>
          </div>

          <div class="section-heading section-heading--spaced">
            <h3>SECTION C - 结案与签署 / Closeout & Sign-off</h3>
          </div>
          <div class="zone-grid two-column">
            <label class="field-item">
              <span>严重级别 / Severity</span>
              <base-dropdown
                :model-value="formData.severity"
                :options="severityOptions"
                placeholder="请选择严重级别"
                @update:model-value="formData.severity = $event"
              />
            </label>
            <label class="field-item">
              <span>状态 / Status</span>
              <base-dropdown
                :model-value="formAnswers.manual_status"
                :options="statusOptions"
                placeholder="请选择状态"
                @update:model-value="formAnswers.manual_status = $event"
              />
            </label>
            <label
              v-if="formAnswers.manual_status === 'follow_up_action_required'"
              class="field-item"
            >
              <span>跟进单号 / Follow-up Ref No.</span>
              <base-input
                v-model="formAnswers.manual_status_ref_no"
                placeholder="例如：DAS2-FAULT-016"
              />
            </label>
            <label class="field-item">
              <span>业主代表 / Employer Rep</span>
              <base-input
                v-model="formAnswers.manual_employer_rep"
                placeholder="业主代表"
              />
            </label>
            <label class="field-item">
              <span>业主代表签名 / Employer Signature</span>
              <base-input
                v-model="formAnswers.manual_employer_signature"
                placeholder="签名"
              />
            </label>
            <label class="field-item">
              <span>结案日期 / Closeout Date</span>
              <base-date-time-picker
                mode="date"
                placeholder="选择日期"
                :model-value="formAnswers.manual_closeout_date"
                @update:model-value="formAnswers.manual_closeout_date = $event"
              />
            </label>
            <label class="field-item full-width">
              <span>备注 / Comments</span>
              <base-textarea
                v-model="formAnswers.manual_comments"
                rows="2"
                placeholder="备注信息..."
              />
            </label>
          </div>
        </div>

        <div v-if="currentStep === 1" class="step-form zone-card">
          <div class="section-heading">
            <h3>快填模式 / Quick Fill</h3>
            <p>
              可跳过此步骤直接进入正文编辑，也可填写简述后一键 AI 生成完整正文。
            </p>
          </div>
          <div class="section-card">
            <div class="section-header">
              <h4>事故简述 / Quick Narrative</h4>
              <base-button
                type="button"
                variant="ghost"
                size="sm"
                :disabled="generating || !formAnswers.quick_narrative.trim()"
                @click="handleQuickGenerate"
              >
                <svg
                  viewBox="0 0 20 20"
                  width="14"
                  height="14"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.5"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path
                    d="M10 2L12.1 7.1L17.5 8.1L13.7 12L14.5 17.5L10 14.8L5.5 17.5L6.3 12L2.5 8.1L7.9 7.1L10 2z"
                  />
                </svg>
                {{ generating ? '生成中...' : 'AI 生成' }}
              </base-button>
            </div>
            <base-textarea
              v-model="formAnswers.quick_narrative"
              rows="6"
              placeholder="例如：3月12号下午3点客户下单报错，定位数据库 CPU 打满，3点半降级并加索引，4点恢复，后续加强 code review。"
            />
          </div>
        </div>

        <div v-if="currentStep === 2" class="step-form zone-card">
          <div class="section-heading">
            <h3>AI 正文 / AI Body</h3>
            <p>可逐段使用 AI 生成或手动编辑。</p>
          </div>

          <div class="section-card">
            <div class="section-header">
              <h4>事故简述 / Incident Summary *</h4>
              <base-button
                type="button"
                variant="ghost"
                size="sm"
                :disabled="generating"
                @click="handleSectionGenerate('description')"
              >
                <svg
                  viewBox="0 0 20 20"
                  width="14"
                  height="14"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.5"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path
                    d="M10 2L12.1 7.1L17.5 8.1L13.7 12L14.5 17.5L10 14.8L5.5 17.5L6.3 12L2.5 8.1L7.9 7.1L10 2z"
                  />
                </svg>
                AI 生成
              </base-button>
            </div>
            <base-textarea
              v-model="formAnswers.body_description"
              rows="4"
              placeholder="请描述事故概况..."
            />
          </div>

          <div class="section-card">
            <div class="section-header">
              <h4>时间线 / Timeline *</h4>
            </div>
            <div class="timeline-summary">
              <div class="zone-grid two-column">
                <label class="field-item">
                  <span>开始时间 / Start Time</span>
                  <base-date-time-picker
                    mode="datetime"
                    placeholder="选择开始时间"
                    :model-value="formAnswers.body_affected_start_time"
                    @update:model-value="
                      formAnswers.body_affected_start_time = $event
                    "
                  />
                </label>
                <label class="field-item">
                  <span>结束时间 / End Time</span>
                  <base-date-time-picker
                    mode="datetime"
                    placeholder="选择结束时间"
                    :model-value="formAnswers.body_affected_end_time"
                    @update:model-value="
                      formAnswers.body_affected_end_time = $event
                    "
                  />
                </label>
              </div>
            </div>
            <div class="timeline-list">
              <div
                v-for="(item, index) in bodyTimelineItems"
                :key="index"
                class="timeline-item-wrapper"
              >
                <div class="timeline-row">
                  <base-date-time-picker
                    mode="time"
                    placeholder="时间"
                    :model-value="item.time"
                    @update:model-value="
                      onBodyTimelineChange(index, 'time', $event)
                    "
                  />
                  <base-input
                    :value="item.event"
                    placeholder="发生了什么"
                    @input="onBodyTimelineInput(index, 'event', $event)"
                  />
                  <base-input
                    :value="item.resolution"
                    placeholder="如何处理"
                    @input="onBodyTimelineInput(index, 'resolution', $event)"
                  />
                  <base-button
                    type="button"
                    variant="ghost"
                    size="sm"
                    :disabled="generating"
                    @click="handleTimelineItemGenerate(index)"
                  >
                    <svg
                      viewBox="0 0 20 20"
                      width="14"
                      height="14"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="1.5"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    >
                      <path
                        d="M10 2L12.1 7.1L17.5 8.1L13.7 12L14.5 17.5L10 14.8L5.5 17.5L6.3 12L2.5 8.1L7.9 7.1L10 2z"
                      />
                    </svg>
                    AI 生成
                  </base-button>
                  <base-button
                    type="button"
                    variant="danger"
                    size="sm"
                    @click="bodyTimelineItems.splice(index, 1)"
                  >
                    <svg
                      viewBox="0 0 20 20"
                      width="12"
                      height="12"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="1.8"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    >
                      <path
                        d="M4 5H16M8 5V3.5H12V5M5 5L5.5 16H14.5L15 5M8 8V13M12 8V13"
                      />
                    </svg>
                    删除
                  </base-button>
                </div>
                <span
                  v-if="timelineTimeErrors[index]"
                  class="timeline-time-error"
                >
                  {{ timelineTimeErrors[index] }}
                </span>
              </div>
            </div>
            <base-button
              type="button"
              variant="secondary"
              size="sm"
              @click="
                bodyTimelineItems.push({ time: '', event: '', resolution: '' })
              "
            >
              新增时间线 / Add Timeline
            </base-button>
          </div>

          <div class="section-card">
            <div class="section-header">
              <h4>影响范围 / 严重级别 / Impact & Severity *</h4>
              <base-button
                type="button"
                variant="ghost"
                size="sm"
                :disabled="generating"
                @click="handleSectionGenerate('impact')"
              >
                <svg
                  viewBox="0 0 20 20"
                  width="14"
                  height="14"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.5"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path
                    d="M10 2L12.1 7.1L17.5 8.1L13.7 12L14.5 17.5L10 14.8L5.5 17.5L6.3 12L2.5 8.1L7.9 7.1L10 2z"
                  />
                </svg>
                AI 生成
              </base-button>
            </div>
            <div class="zone-grid two-column">
              <label class="field-item">
                <span>影响范围 / Impact Scope *</span>
                <base-input
                  v-model="formAnswers.body_impact_scope"
                  placeholder="影响范围"
                />
              </label>
              <label class="field-item">
                <span>严重级别 / Impact Severity *</span>
                <base-input
                  v-model="formAnswers.body_impact_severity"
                  placeholder="严重级别"
                />
              </label>
              <label class="field-item full-width">
                <span>业务影响 / Business Impact</span>
                <base-textarea
                  v-model="formAnswers.body_business_impact"
                  rows="2"
                  placeholder="业务影响描述..."
                />
              </label>
            </div>
          </div>

          <div class="section-card">
            <div class="section-header">
              <h4>根因分析 / Root Cause *</h4>
              <base-button
                type="button"
                variant="ghost"
                size="sm"
                :disabled="generating"
                @click="handleSectionGenerate('root_cause')"
              >
                <svg
                  viewBox="0 0 20 20"
                  width="14"
                  height="14"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.5"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path
                    d="M10 2L12.1 7.1L17.5 8.1L13.7 12L14.5 17.5L10 14.8L5.5 17.5L6.3 12L2.5 8.1L7.9 7.1L10 2z"
                  />
                </svg>
                AI 生成
              </base-button>
            </div>
            <div class="zone-grid">
              <label class="field-item">
                <span>触发原因 / Trigger</span>
                <base-input
                  v-model="formAnswers.body_trigger"
                  placeholder="触发原因"
                />
              </label>
              <label class="field-item full-width">
                <span>根因 / Root Cause *</span>
                <base-textarea
                  v-model="formAnswers.body_root_cause"
                  rows="3"
                  placeholder="根因分析..."
                />
              </label>
            </div>
          </div>

          <div class="section-card">
            <div class="section-header">
              <h4>后续动作 / Follow-Up Actions *</h4>
              <base-button
                type="button"
                variant="ghost"
                size="sm"
                :disabled="generating"
                @click="handleSectionGenerate('follow_up')"
              >
                <svg
                  viewBox="0 0 20 20"
                  width="14"
                  height="14"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.5"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path
                    d="M10 2L12.1 7.1L17.5 8.1L13.7 12L14.5 17.5L10 14.8L5.5 17.5L6.3 12L2.5 8.1L7.9 7.1L10 2z"
                  />
                </svg>
                AI 生成
              </base-button>
            </div>
            <base-textarea
              v-model="formAnswers.body_follow_up"
              rows="4"
              placeholder="后续动作计划..."
            />
          </div>

          <div v-if="generationError" class="error-hint">
            {{ generationError }}
          </div>
        </div>

        <div v-if="currentStep === 3" class="step-form zone-card">
          <div class="section-heading">
            <h3>附录 / Appendix</h3>
            <p>支持富文本输入，附加信息将在生成文档时同步写入附录页。</p>
          </div>
          <div class="zone-grid">
            <label class="field-item full-width">
              <span>附录内容 / Appendix Notes</span>
              <rich-text-editor
                v-model="formAnswers.appendix_notes"
                placeholder="请输入附录内容..."
              />
            </label>
          </div>
        </div>

        <div v-if="currentStep === 4" class="step-form zone-card">
          <div class="section-heading">
            <h3>预览 / Preview</h3>
            <p>点击生成预览后，将自动打开 PDF 预览。</p>
          </div>
          <div class="preview-actions">
            <base-button
              type="button"
              variant="primary"
              :disabled="previewing"
              @click="handleGeneratePreview"
            >
              <svg
                viewBox="0 0 20 20"
                width="14"
                height="14"
                fill="none"
                stroke="currentColor"
                stroke-width="1.5"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path
                  d="M10 2L12.1 7.1L17.5 8.1L13.7 12L14.5 17.5L10 14.8L5.5 17.5L6.3 12L2.5 8.1L7.9 7.1L10 2z"
                />
              </svg>
              {{ previewing ? '生成中...' : '生成预览' }}
            </base-button>
            <base-button
              v-if="previewData?.docxBase64"
              type="button"
              variant="secondary"
              @click="downloadDocx"
            >
              <svg
                viewBox="0 0 20 20"
                width="14"
                height="14"
                fill="none"
                stroke="currentColor"
                stroke-width="1.5"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d="M10 3V13M10 13L6.5 9.5M10 13L13.5 9.5M3 16H17" />
              </svg>
              下载 DOCX
            </base-button>
          </div>
          <div v-if="previewData?.warnings?.length" class="preview-warnings">
            <p v-for="w in previewData.warnings" :key="w" class="warning-hint">
              {{ w }}
            </p>
          </div>

          <div
            v-if="showPdfPreview && previewData?.pdfBase64"
            class="pdf-preview-dialog"
            @click.self="showPdfPreview = false"
            @keydown.esc="showPdfPreview = false"
          >
            <div class="pdf-preview-content">
              <iframe
                :src="pdfPreviewUrl + '#toolbar=0&navpanes=0'"
                class="pdf-preview-iframe"
                frameborder="0"
              />
              <base-button
                class="pdf-preview-close"
                variant="ghost"
                size="sm"
                @click="showPdfPreview = false"
              >
                <svg
                  viewBox="0 0 20 20"
                  width="16"
                  height="16"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                >
                  <path d="M5 5L15 15M15 5L5 15" />
                </svg>
              </base-button>
            </div>
          </div>
        </div>
      </div>

      <div class="wizard-actions">
        <base-button
          variant="secondary"
          @click="router.push('/incident-report')"
        >
          取消 / Cancel
        </base-button>
        <div class="wizard-nav">
          <base-button
            v-if="currentStep > 0"
            variant="ghost"
            @click="currentStep--"
          >
            <svg
              viewBox="0 0 20 20"
              width="14"
              height="14"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M12.5 15L7.5 10L12.5 5" />
            </svg>
            上一步
          </base-button>
          <base-button
            v-if="currentStep < EDIT_WIZARD_STEPS.length - 1"
            variant="primary"
            class="wizard-btn-next"
            @click="handleNextStep"
          >
            下一步
            <svg
              viewBox="0 0 20 20"
              width="14"
              height="14"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M7.5 5L12.5 10L7.5 15" />
            </svg>
          </base-button>
          <base-button
            v-if="currentStep === EDIT_WIZARD_STEPS.length - 1"
            variant="primary"
            class="wizard-btn-save"
            :disabled="!formData.title.trim() || saving"
            @click="handleSave"
          >
            <svg
              viewBox="0 0 20 20"
              width="14"
              height="14"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M4 10.5L8 14.5L16 5.5" />
            </svg>
            {{ saving ? '保存中...' : '保存' }}
          </base-button>
          <base-button
            v-if="currentStep === EDIT_WIZARD_STEPS.length - 1"
            variant="primary"
            class="wizard-btn-submit"
            :disabled="!formData.title.trim() || submitting"
            @click="handleSubmit"
          >
            <svg
              viewBox="0 0 20 20"
              width="14"
              height="14"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M4 10.5L8 14.5L16 5.5" />
            </svg>
            {{ submitting ? '提交中...' : '提交审核' }}
          </base-button>
        </div>
      </div>

      <ai-generating-modal
        :visible="generating || previewing"
        :label="generatingLabel"
        @stop="handleStopGeneration"
      />

      <floating-toast
        :visible="showSaveToast"
        :title="saveToastTitle"
        :message="saveToastMessage"
      />
    </template>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, watch, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import humps from 'humps';
import { useAppStore } from '../../../stores/app';
import {
  useReportEditWizard,
  EDIT_WIZARD_STEPS,
} from './composables/useReportEditWizard';
import type { EditWizardStep } from './composables/useReportEditWizard';
import {
  convertToIso,
  severityOptions,
  statusOptions,
  defaultFormAnswers,
  buildFormPayload as _buildFormPayload,
  validateTimelineTimeOrder as _validateTimelineTimeOrder,
  type TimelineItem,
} from '../composables/useReportForm';
import AiGeneratingModal from '../../../components/business/AiGeneratingModal.vue';
import FloatingToast from '../../../components/business/FloatingToast.vue';
import BaseButton from '../../../components/base/BaseButton.vue';
import BaseInput from '../../../components/base/BaseInput.vue';
import BaseDropdown from '../../../components/base/BaseDropdown.vue';
import BaseTextarea from '../../../components/base/BaseTextarea.vue';
import BaseDateTimePicker from '../../../components/base/BaseDateTimePicker.vue';
import RichTextEditor from '../components/RichTextEditor.vue';

const route = useRoute();
const router = useRouter();

const reportId = route.params.id as string;

const {
  currentStep,
  loading,
  saving,
  submitting,
  generating,
  previewing,
  report,
  previewData,
  generationError,
  load,
  save,
  submit,
  quickGenerate,
  generateSection,
  generatePreview,
  applyGenerationResult,
} = useReportEditWizard(reportId);

const appStore = useAppStore();

let abortController: AbortController | null = null;

const generatingLabel = computed(() => {
  if (previewing.value) return '正在生成预览';
  return 'AI 正在生成';
});

const handleStopGeneration = () => {
  if (abortController) {
    abortController.abort();
    abortController = null;
  }
};

const downloadingDocx = ref(false);
const showPdfPreview = ref(false);
const pdfPreviewUrl = ref('');

const showSaveToast = ref(false);
const saveToastTitle = ref('保存成功');
const saveToastMessage = ref('草稿已保存');

const formData = ref({
  title: '',
  severity: '',
  system: '',
  siteId: '',
  faultDate: '',
});

const formAnswers = ref<Record<string, string>>({ ...defaultFormAnswers });

const bodyTimelineItems = ref<TimelineItem[]>([
  { time: '', event: '', resolution: '' },
]);

watch(
  bodyTimelineItems,
  (items) => {
    formAnswers.value.body_timeline = JSON.stringify(items);
  },
  { deep: true },
);

const onBodyTimelineChange = (
  index: number,
  key: keyof TimelineItem,
  value: string,
) => {
  if (bodyTimelineItems.value[index]) {
    bodyTimelineItems.value[index][key] = value;
  }
  if (key === 'time') {
    _validateTimelineTimeOrder(bodyTimelineItems, timelineTimeErrors);
  }
};

const timelineTimeErrors = ref<Record<number, string>>({});

const onBodyTimelineInput = (
  index: number,
  key: keyof TimelineItem,
  event: Event,
) => {
  const value = (event.target as HTMLInputElement).value;
  onBodyTimelineChange(index, key, value);
};

const buildFormPayload = () =>
  _buildFormPayload(formData.value, formAnswers.value, bodyTimelineItems.value);

const handleNextStep = () => {
  if (currentStep.value < EDIT_WIZARD_STEPS.length - 1) {
    currentStep.value = (currentStep.value + 1) as EditWizardStep;
  }
};

const handleQuickGenerate = async () => {
  if (!formAnswers.value.quick_narrative.trim() || generating.value) return;
  try {
    abortController = new AbortController();
    const result = await quickGenerate(buildFormPayload(), {
      model: appStore.selectedModel,
      rerankerModel: appStore.selectedRerankerModel,
      signal: abortController.signal,
    });
    applyGenerationResult(result, formAnswers.value);
    if (result.formAnswers.bodyTimeline) {
      const timeline = result.formAnswers.bodyTimeline.value;
      if (Array.isArray(timeline) && timeline.length > 0) {
        bodyTimelineItems.value = timeline.map(
          (item: Record<string, string>) => ({
            time: item.time || '',
            event: item.event || '',
            resolution: item.resolution || '',
          }),
        );
        const firstTime = timeline[0].time;
        const lastTime = timeline[timeline.length - 1].time;
        if (firstTime) {
          formAnswers.value.body_affected_start_time = convertToIso(
            firstTime,
            formData.value.faultDate,
          );
        }
        if (lastTime) {
          formAnswers.value.body_affected_end_time = convertToIso(
            lastTime,
            formData.value.faultDate,
          );
        }
      }
    }
    saveToastTitle.value = '生成成功';
    saveToastMessage.value = 'AI 正文已生成，可进入下一步查看和编辑';
    showSaveToast.value = true;
    setTimeout(() => {
      showSaveToast.value = false;
    }, 3000);
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') return;
  } finally {
    abortController = null;
  }
};

const handleSave = async () => {
  if (!formData.value.title.trim()) return;
  try {
    await save(buildFormPayload());
    saveToastTitle.value = '保存成功';
    saveToastMessage.value = '草稿已保存';
    showSaveToast.value = true;
    setTimeout(() => {
      showSaveToast.value = false;
    }, 3000);
    router.push('/incident-report');
  } finally {
    // saving state managed by composable
  }
};

const handleSubmit = async () => {
  if (!formData.value.title.trim()) return;
  try {
    await submit(buildFormPayload());
    saveToastTitle.value = '提交成功';
    saveToastMessage.value = '报告已提交审核';
    showSaveToast.value = true;
    setTimeout(() => {
      showSaveToast.value = false;
    }, 3000);
    router.push('/incident-report');
  } catch {
    saveToastTitle.value = '提交失败';
    saveToastMessage.value = '请稍后重试';
    showSaveToast.value = true;
    setTimeout(() => {
      showSaveToast.value = false;
    }, 3000);
  }
};

const handleSectionGenerate = async (sectionId: string) => {
  if (generating.value) return;
  try {
    abortController = new AbortController();
    await save(buildFormPayload());
    const result = await generateSection(sectionId, {
      model: appStore.selectedModel,
      rerankerModel: appStore.selectedRerankerModel,
      signal: abortController.signal,
    });
    applyGenerationResult(result, formAnswers.value);
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') return;
    throw err;
  } finally {
    abortController = null;
  }
};

const handleTimelineItemGenerate = async (index: number) => {
  if (generating.value) return;
  try {
    abortController = new AbortController();
    await save(buildFormPayload());
    const result = await generateSection('timeline_item', {
      timelineIndex: index,
      model: appStore.selectedModel,
      rerankerModel: appStore.selectedRerankerModel,
      signal: abortController.signal,
    });
    applyGenerationResult(result, formAnswers.value);
    if (result.formAnswers.bodyTimeline) {
      const timeline = result.formAnswers.bodyTimeline.value;
      if (Array.isArray(timeline)) {
        bodyTimelineItems.value = timeline.map(
          (item: Record<string, string>) => ({
            time: item.time || '',
            event: item.event || '',
            resolution: item.resolution || '',
          }),
        );
      }
    }
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') return;
    throw err;
  } finally {
    abortController = null;
  }
};

const handleGeneratePreview = async () => {
  try {
    abortController = new AbortController();
    await save(buildFormPayload());
    await generatePreview({ signal: abortController.signal });
    if (previewData.value?.pdfBase64) {
      const binaryString = atob(previewData.value.pdfBase64);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      const blob = new Blob([bytes], { type: 'application/pdf' });
      if (pdfPreviewUrl.value) {
        URL.revokeObjectURL(pdfPreviewUrl.value);
      }
      pdfPreviewUrl.value = URL.createObjectURL(blob);
      showPdfPreview.value = true;
    }
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') return;
    throw err;
  } finally {
    abortController = null;
  }
};

const downloadDocx = () => {
  if (!previewData.value?.docxBase64 || !previewData.value?.docxFileName)
    return;
  const binaryString = atob(previewData.value.docxBase64);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  const blob = new Blob([bytes], {
    type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = previewData.value.docxFileName;
  link.click();
  URL.revokeObjectURL(url);
};

const handleDownloadDocx = async () => {
  if (!report.value || downloadingDocx.value) return;
  downloadingDocx.value = true;
  try {
    const preview = await generatePreview();
    if (!preview.docxBase64 || !preview.docxFileName) return;
    const binaryString = atob(preview.docxBase64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    const blob = new Blob([bytes], {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = preview.docxFileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  } finally {
    downloadingDocx.value = false;
  }
};

onMounted(async () => {
  try {
    await load();
  } catch {
    // load sets report to null on failure, UI shows "报告不存在"
  }
  if (report.value) {
    formData.value = {
      title: report.value.title,
      severity: report.value.severity ?? '',
      system: report.value.system ?? '',
      siteId: report.value.siteId ?? '',
      faultDate: report.value.faultDate ?? '',
    };
    const fd = humps.decamelizeKeys(report.value.formData || {}) as Record<
      string,
      unknown
    >;
    const answers = { ...defaultFormAnswers };
    for (const key of Object.keys(defaultFormAnswers)) {
      if (fd[key] !== undefined && fd[key] !== null) {
        const raw = fd[key];
        if (
          typeof raw === 'object' &&
          raw !== null &&
          'value' in (raw as Record<string, unknown>)
        ) {
          answers[key] = String((raw as Record<string, unknown>).value ?? '');
        } else {
          answers[key] = String(raw);
        }
      }
    }
    formAnswers.value = answers;

    if (fd.body_timeline) {
      try {
        let timelineRaw: unknown = fd.body_timeline;
        if (
          typeof timelineRaw === 'object' &&
          timelineRaw !== null &&
          'value' in (timelineRaw as Record<string, unknown>)
        ) {
          timelineRaw = (timelineRaw as Record<string, unknown>).value;
        }
        const parsed: unknown =
          typeof timelineRaw === 'string'
            ? JSON.parse(timelineRaw)
            : timelineRaw;
        if (Array.isArray(parsed) && parsed.length > 0) {
          bodyTimelineItems.value = parsed.map(
            (item: Record<string, string>) => ({
              time: item.time || '',
              event: item.event || '',
              resolution: item.resolution || '',
            }),
          );
        }
      } catch {
        // ignore parse errors
      }
    }
  }
});
</script>

<style scoped src="../create/styles/incident-report-create.css"></style>
