<template>
  <section class="incident-report-create-view">
    <div class="create-header">
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
      <h1>新建事故报告 / New Incident Report</h1>
    </div>

    <div class="wizard-steps">
      <div
        v-for="(step, index) in WIZARD_STEPS"
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
          (currentStep = index as WizardStep)
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
          <label
            ref="fieldTitle"
            class="field-item"
            :class="{ invalid: attemptedNextStep && !formData.title.trim() }"
          >
            <span>报告标题 / Report Title *</span>
            <base-input v-model="formData.title" placeholder="请输入报告标题" />
            <span
              v-if="attemptedNextStep && !formData.title.trim()"
              class="field-error"
              >请填写报告标题</span
            >
          </label>
          <label class="field-item">
            <span>参考编号 / Reference No.</span>
            <base-input
              v-model="formAnswers.manual_reference_no"
              placeholder="例如：DAS2 Fault Log Form-015"
            />
          </label>
          <label
            ref="fieldFaultDate"
            class="field-item"
            :class="{ invalid: attemptedNextStep && !formData.faultDate }"
          >
            <span>故障上报日期 / Date of Fault Reporting *</span>
            <base-date-time-picker
              mode="date"
              placeholder="选择日期"
              :model-value="formData.faultDate"
              @update:model-value="formData.faultDate = $event"
            />
            <span
              v-if="attemptedNextStep && !formData.faultDate"
              class="field-error"
              >请选择故障上报日期</span
            >
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
          <label
            ref="fieldReporter"
            class="field-item"
            :class="{
              invalid:
                attemptedNextStep &&
                !formAnswers.manual_reporting_person.trim(),
            }"
          >
            <span>报告人 / Reporting Person *</span>
            <base-input
              v-model="formAnswers.manual_reporting_person"
              placeholder="报告人姓名"
            />
            <span
              v-if="
                attemptedNextStep && !formAnswers.manual_reporting_person.trim()
              "
              class="field-error"
              >请填写报告人</span
            >
          </label>
          <label class="field-item">
            <span>审核人 / Verified By</span>
            <base-input
              v-model="formAnswers.manual_verified_by"
              placeholder="审核人姓名"
            />
          </label>
          <label
            ref="fieldSiteId"
            class="field-item"
            :class="{ invalid: attemptedNextStep && !formData.siteId }"
          >
            <span>站点编号 / Site ID *</span>
            <base-input v-model="formData.siteId" placeholder="如：SITE-01" />
            <span
              v-if="attemptedNextStep && !formData.siteId"
              class="field-error"
              >请填写站点编号</span
            >
          </label>
          <label
            ref="fieldSystem"
            class="field-item"
            :class="{ invalid: attemptedNextStep && !formData.system }"
          >
            <span>系统 / 子系统 / System / Subsystems *</span>
            <base-input
              v-model="formData.system"
              placeholder="如：数据库系统"
            />
            <span
              v-if="attemptedNextStep && !formData.system"
              class="field-error"
              >请填写系统/子系统</span
            >
          </label>
          <label
            ref="fieldLocation"
            class="field-item"
            :class="{
              invalid: attemptedNextStep && !formAnswers.manual_location.trim(),
            }"
          >
            <span>故障位置 / Location of Fault *</span>
            <base-input
              v-model="formAnswers.manual_location"
              placeholder="故障发生位置"
            />
            <span
              v-if="attemptedNextStep && !formAnswers.manual_location.trim()"
              class="field-error"
              >请填写故障位置</span
            >
          </label>
          <label
            ref="fieldSymptom"
            class="field-item full-width"
            :class="{
              invalid:
                attemptedNextStep && !formAnswers.manual_fault_symptom.trim(),
            }"
          >
            <span>故障现象详情 / Details of Fault Symptom *</span>
            <base-textarea
              v-model="formAnswers.manual_fault_symptom"
              rows="3"
              placeholder="请详细描述故障现象..."
            />
            <span
              v-if="
                attemptedNextStep && !formAnswers.manual_fault_symptom.trim()
              "
              class="field-error"
              >请填写故障现象详情</span
            >
          </label>
          <label class="field-item">
            <span>到场时间 / Arrival Datetime</span>
            <base-date-time-picker
              mode="datetime"
              :model-value="formAnswers.manual_arrival_datetime"
              @update:model-value="formAnswers.manual_arrival_datetime = $event"
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
              @update:model-value="formAnswers.manual_contractor_date = $event"
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
          <p>可由快填自动填充，也可逐段使用 AI 生成或手动编辑。</p>
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
        :disabled="saving"
        @click="handleSaveDraft"
      >
        保存草稿 / Save Draft
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
          v-if="currentStep < WIZARD_STEPS.length - 1"
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
          v-if="currentStep === WIZARD_STEPS.length - 1"
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
          提交报告
        </base-button>
      </div>
    </div>

    <ai-generating-modal
      :visible="generating || previewing"
      :label="generatingLabel"
      @stop="handleStopGeneration"
    />

    <floating-toast
      :visible="showSubmitToast"
      :title="submitToastTitle"
      :message="submitToastMessage"
    />
  </section>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useAppStore } from '@shared/stores/app';
import { useReportWizard, WIZARD_STEPS } from './composables/useReportWizard';
import type { WizardStep } from './composables/useReportWizard';
import {
  convertToIso,
  severityOptions,
  statusOptions,
  defaultFormAnswers,
  buildFormPayload as _buildFormPayload,
  validateTimelineTimeOrder as _validateTimelineTimeOrder,
  type TimelineItem,
} from '../composables/useReportForm';
import AiGeneratingModal from '@shared/components/AiGeneratingModal.vue';
import FloatingToast from '@shared/components/FloatingToast.vue';
import BaseButton from '@shared/ui/BaseButton.vue';
import BaseInput from '@shared/ui/BaseInput.vue';
import BaseTextarea from '@shared/ui/BaseTextarea.vue';
import BaseDropdown from '@shared/ui/BaseDropdown.vue';
import BaseDateTimePicker from '@shared/ui/BaseDateTimePicker.vue';
import RichTextEditor from '../components/RichTextEditor.vue';

const router = useRouter();

const {
  currentStep,
  saving,
  submitting,
  generating,
  previewing,
  reportId,
  previewData,
  generationError,
  saveAsDraft,
  createAndSubmit,
  quickGenerate,
  generateSection,
  generatePreview,
  applyGenerationResult,
} = useReportWizard();

let abortController: AbortController | null = null;

const attemptedNextStep = ref(false);
const showSubmitToast = ref(false);
const submitToastMessage = ref('报告提交成功');
const submitToastTitle = ref('提交成功');

const fieldTitle = ref<HTMLLabelElement | null>(null);
const fieldFaultDate = ref<HTMLLabelElement | null>(null);
const fieldReporter = ref<HTMLLabelElement | null>(null);
const fieldSiteId = ref<HTMLLabelElement | null>(null);
const fieldSystem = ref<HTMLLabelElement | null>(null);
const fieldLocation = ref<HTMLLabelElement | null>(null);
const fieldSymptom = ref<HTMLLabelElement | null>(null);

const appStore = useAppStore();

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

const handleNextStep = async () => {
  if (currentStep.value === 0) {
    attemptedNextStep.value = true;
    const requiredFields = [
      { ref: 'fieldTitle', valid: !!formData.value.title.trim() },
      { ref: 'fieldFaultDate', valid: !!formData.value.faultDate },
      {
        ref: 'fieldReporter',
        valid: !!formAnswers.value.manual_reporting_person.trim(),
      },
      { ref: 'fieldSiteId', valid: !!formData.value.siteId },
      { ref: 'fieldSystem', valid: !!formData.value.system },
      {
        ref: 'fieldLocation',
        valid: !!formAnswers.value.manual_location.trim(),
      },
      {
        ref: 'fieldSymptom',
        valid: !!formAnswers.value.manual_fault_symptom.trim(),
      },
    ];
    const firstInvalid = requiredFields.find((f) => !f.valid);
    if (firstInvalid) {
      const refMap: Record<string, typeof fieldTitle> = {
        fieldTitle,
        fieldFaultDate,
        fieldReporter,
        fieldSiteId,
        fieldSystem,
        fieldLocation,
        fieldSymptom,
      };
      const el = refMap[firstInvalid.ref]?.value;
      el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }
  }

  if (currentStep.value < WIZARD_STEPS.length - 1) {
    currentStep.value = (currentStep.value + 1) as WizardStep;
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
    submitToastTitle.value = '生成成功';
    submitToastMessage.value = 'AI 正文已生成，可进入下一步查看和编辑';
    showSubmitToast.value = true;
    setTimeout(() => {
      showSubmitToast.value = false;
    }, 3000);
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') return;
  } finally {
    abortController = null;
  }
};

const handleSaveDraft = async () => {
  if (!formData.value.title.trim()) return;
  saving.value = true;
  try {
    const report = await saveAsDraft(buildFormPayload());
    submitToastTitle.value = '保存成功';
    submitToastMessage.value = '草稿已保存';
    showSubmitToast.value = true;
    setTimeout(() => {
      showSubmitToast.value = false;
    }, 3000);
    if (!reportId.value) {
      router.push(`/incident-report/${report.id}`);
    }
  } finally {
    saving.value = false;
  }
};

const handleSubmit = async () => {
  if (!formData.value.title.trim()) return;
  submitting.value = true;
  try {
    await createAndSubmit(buildFormPayload());
    sessionStorage.setItem('incident_report_submitted', '1');
    router.push('/incident-report');
  } catch (err: unknown) {
    let message = '提交失败，请稍后重试';
    if (err && typeof err === 'object' && 'response' in err) {
      const resp = (err as { response?: { data?: { detail?: string } } })
        .response;
      if (resp?.data?.detail) {
        message = resp.data.detail;
      }
    } else if (err instanceof Error) {
      message = err.message;
    }
    submitToastTitle.value = '提交失败';
    submitToastMessage.value = message;
    showSubmitToast.value = true;
    setTimeout(() => {
      showSubmitToast.value = false;
    }, 5000);
  } finally {
    submitting.value = false;
  }
};

const handleSectionGenerate = async (sectionId: string) => {
  if (generating.value) return;
  try {
    abortController = new AbortController();
    generating.value = true;
    await saveAsDraft(buildFormPayload());
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
    generating.value = true;
    await saveAsDraft(buildFormPayload());
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

const showPdfPreview = ref(false);
const pdfPreviewUrl = ref('');

const handleGeneratePreview = async () => {
  try {
    abortController = new AbortController();
    await saveAsDraft(buildFormPayload());
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
</script>

<style scoped src="./styles/incident-report-create.css"></style>
