<template>
  <div class="incident-report-workspace">
    <Transition name="session-switch" mode="out-in">
      <section v-if="!session" key="welcome" class="incident-report-welcome">
        <h2>事故报告助手</h2>
        <p class="incident-report-welcome-text">
          {{
            schema?.introMessage ||
            '欢迎使用事故报告专区。支持快填生成正文、完整分段润色、附录富文本编辑与多版本附件历史。'
          }}
        </p>
        <ul class="incident-report-welcome-list">
          <li>手工首页字段与参考文档第一页保持一致。</li>
          <li>AI 正文支持快填和完整模式联动生成。</li>
          <li>附件生成支持历史版本对比与下载。</li>
        </ul>
        <BaseButton
          type="button"
          class="incident-report-primary-btn"
          variant="primary"
          @click="$emit('start')"
        >
          开始
        </BaseButton>
      </section>

      <section
        v-else
        :key="`form-${session?.id ?? 'unknown'}`"
        class="incident-report-form-page"
      >
        <header class="incident-report-form-header">
          <h2>{{ session.title }}</h2>
          <span v-if="statusLabel" class="incident-report-status">{{
            statusLabel
          }}</span>
        </header>

        <div class="incident-report-zone-grid">
          <section class="incident-report-zone-card">
            <header class="zone-header">
              <h3>手工首页（Manual Cover）</h3>
              <p>对应参考文档第一页表格，优先人工确认。</p>
            </header>
            <div class="zone-grid two-column manual-cover-grid">
              <div class="manual-section-heading">
                <h4>SECTION A - 故障记录（Fault Details）</h4>
              </div>

              <label class="field-item">
                <span>参考编号（Reference No.）</span>
                <BaseInput
                  :value="getTextAnswer(MANUAL_REFERENCE_NO)"
                  placeholder="例如：DAS2 Fault Log Form-015"
                  @input="onTextInput(MANUAL_REFERENCE_NO, $event)"
                />
              </label>

              <label
                class="field-item"
                :class="{ invalid: missingFieldSet.has(MANUAL_FAULT_DATE) }"
                :data-field="MANUAL_FAULT_DATE"
              >
                <span>故障上报日期（Date of Fault Reporting）*</span>
                <BaseDateTimePicker
                  mode="date"
                  placeholder="选择日期"
                  :model-value="getTextAnswer(MANUAL_FAULT_DATE)"
                  @update:model-value="
                    setAnswerValue(MANUAL_FAULT_DATE, $event)
                  "
                />
              </label>

              <label
                class="field-item"
                :class="{ invalid: missingFieldSet.has(MANUAL_FAULT_TIME) }"
                :data-field="MANUAL_FAULT_TIME"
              >
                <span>故障上报时间（Time of Fault Reporting）*</span>
                <BaseDateTimePicker
                  mode="time"
                  placeholder="选择时间"
                  :model-value="getTextAnswer(MANUAL_FAULT_TIME)"
                  @update:model-value="
                    setAnswerValue(MANUAL_FAULT_TIME, normalizeTimeOnly($event))
                  "
                />
              </label>

              <label class="field-item" :data-field="MANUAL_REPORTING_PERSON">
                <span>报告人（Reporting Person）*</span>
                <BaseInput
                  :value="getTextAnswer(MANUAL_REPORTING_PERSON)"
                  :class="{
                    invalid: missingFieldSet.has(MANUAL_REPORTING_PERSON),
                  }"
                  @input="onTextInput(MANUAL_REPORTING_PERSON, $event)"
                />
              </label>

              <label class="field-item">
                <span>审核人（Verified By）</span>
                <BaseInput
                  :value="getTextAnswer(MANUAL_VERIFIED_BY)"
                  @input="onTextInput(MANUAL_VERIFIED_BY, $event)"
                />
              </label>

              <label class="field-item" :data-field="MANUAL_SITE_ID">
                <span>站点编号（Site ID）*</span>
                <BaseInput
                  :value="getTextAnswer(MANUAL_SITE_ID)"
                  :class="{ invalid: missingFieldSet.has(MANUAL_SITE_ID) }"
                  @input="onTextInput(MANUAL_SITE_ID, $event)"
                />
              </label>

              <label class="field-item" :data-field="MANUAL_SYSTEM">
                <span>系统 / 子系统（System / Subsystems）*</span>
                <BaseInput
                  :value="getTextAnswer(MANUAL_SYSTEM)"
                  :class="{ invalid: missingFieldSet.has(MANUAL_SYSTEM) }"
                  @input="onTextInput(MANUAL_SYSTEM, $event)"
                />
              </label>

              <label class="field-item" :data-field="MANUAL_LOCATION">
                <span>故障位置（Location of Fault）*</span>
                <BaseInput
                  :value="getTextAnswer(MANUAL_LOCATION)"
                  :class="{ invalid: missingFieldSet.has(MANUAL_LOCATION) }"
                  @input="onTextInput(MANUAL_LOCATION, $event)"
                />
              </label>

              <label
                class="field-item full-width"
                :data-field="MANUAL_FAULT_SYMPTOM"
              >
                <span>故障现象详情（Details of Fault Symptom）*</span>
                <BaseTextarea
                  rows="3"
                  :value="getTextAnswer(MANUAL_FAULT_SYMPTOM)"
                  :class="{
                    invalid: missingFieldSet.has(MANUAL_FAULT_SYMPTOM),
                  }"
                  @input="onTextInput(MANUAL_FAULT_SYMPTOM, $event)"
                ></BaseTextarea>
              </label>

              <label class="field-item">
                <span>到场时间（Arrival Datetime）</span>
                <BaseDateTimePicker
                  mode="datetime"
                  :model-value="getTextAnswer(MANUAL_ARRIVAL_DATETIME)"
                  @update:model-value="
                    setAnswerValue(MANUAL_ARRIVAL_DATETIME, $event)
                  "
                />
              </label>

              <label class="field-item">
                <span>恢复时间（Clearance Datetime）</span>
                <BaseDateTimePicker
                  mode="datetime"
                  :model-value="getTextAnswer(MANUAL_CLEARANCE_DATETIME)"
                  @update:model-value="
                    setAnswerValue(MANUAL_CLEARANCE_DATETIME, $event)
                  "
                />
              </label>

              <label class="field-item">
                <span>维护人员（Service Person）</span>
                <BaseInput
                  :value="getTextAnswer(MANUAL_SERVICE_PERSON)"
                  @input="onTextInput(MANUAL_SERVICE_PERSON, $event)"
                />
              </label>

              <label class="field-item">
                <span>故障原因（Fault Cause）</span>
                <BaseInput
                  :value="getTextAnswer(MANUAL_FAULT_CAUSE)"
                  @input="onTextInput(MANUAL_FAULT_CAUSE, $event)"
                />
              </label>

              <label class="field-item">
                <span>使用物料（Materials Used）</span>
                <BaseInput
                  :value="getTextAnswer(MANUAL_MATERIALS_USED)"
                  @input="onTextInput(MANUAL_MATERIALS_USED, $event)"
                />
              </label>

              <div class="manual-section-heading">
                <h4>SECTION B - 维修与验证（Repair Works & Verification）</h4>
              </div>

              <label class="field-item full-width">
                <span>维修详情（Repair Details）</span>
                <BaseTextarea
                  rows="3"
                  :value="getTextAnswer(MANUAL_REPAIR_DETAILS)"
                  @input="onTextInput(MANUAL_REPAIR_DETAILS, $event)"
                ></BaseTextarea>
              </label>

              <label class="field-item">
                <span>承包商人员（Contractor Staff）</span>
                <BaseInput
                  :value="getTextAnswer(MANUAL_CONTRACTOR_STAFF)"
                  @input="onTextInput(MANUAL_CONTRACTOR_STAFF, $event)"
                />
              </label>

              <label class="field-item">
                <span>承包商签名（Contractor Signature）</span>
                <BaseInput
                  :value="getTextAnswer(MANUAL_CONTRACTOR_SIGNATURE)"
                  @input="onTextInput(MANUAL_CONTRACTOR_SIGNATURE, $event)"
                />
              </label>

              <label class="field-item">
                <span>承包商日期（Contractor Date）</span>
                <BaseDateTimePicker
                  mode="date"
                  placeholder="选择日期"
                  :model-value="getTextAnswer(MANUAL_CONTRACTOR_DATE)"
                  @update:model-value="
                    setAnswerValue(MANUAL_CONTRACTOR_DATE, $event)
                  "
                />
              </label>

              <div class="manual-section-heading">
                <h4>SECTION C - 结案与签署（Closeout & Sign-off）</h4>
              </div>

              <label class="field-item">
                <span>状态（Status）</span>
                <BaseDropdown
                  :model-value="selectedStatusOption"
                  :options="statusOptions"
                  placeholder="请选择状态"
                  @update:model-value="onStatusChange"
                />
              </label>

              <label
                v-if="
                  selectedStatusOption ===
                  STATUS_OPTION_FOLLOW_UP_ACTION_REQUIRED
                "
                class="field-item"
              >
                <span>跟进单号（Follow-up Ref No.）</span>
                <BaseInput
                  :value="getTextAnswer(MANUAL_STATUS_REF_NO)"
                  placeholder="例如：DAS2-FAULT-016"
                  @input="onTextInput(MANUAL_STATUS_REF_NO, $event)"
                />
              </label>

              <label class="field-item">
                <span>严重级别（Severity）</span>
                <BaseDropdown
                  :model-value="selectedSeverityOption"
                  :options="severityOptions"
                  placeholder="请选择严重级别"
                  @update:model-value="onSeverityChange"
                />
              </label>

              <label class="field-item">
                <span>业主代表（Employer Rep）</span>
                <BaseInput
                  :value="getTextAnswer(MANUAL_EMPLOYER_REP)"
                  @input="onTextInput(MANUAL_EMPLOYER_REP, $event)"
                />
              </label>

              <label class="field-item">
                <span>业主代表签名（Employer Signature）</span>
                <BaseInput
                  :value="getTextAnswer(MANUAL_EMPLOYER_SIGNATURE)"
                  @input="onTextInput(MANUAL_EMPLOYER_SIGNATURE, $event)"
                />
              </label>

              <label class="field-item">
                <span>结案日期（Closeout Date）</span>
                <BaseDateTimePicker
                  mode="date"
                  placeholder="选择日期"
                  :model-value="getTextAnswer(MANUAL_CLOSEOUT_DATE)"
                  @update:model-value="
                    setAnswerValue(MANUAL_CLOSEOUT_DATE, $event)
                  "
                />
              </label>

              <label class="field-item full-width">
                <span>备注（Comments）</span>
                <BaseTextarea
                  rows="2"
                  :value="getTextAnswer(MANUAL_COMMENTS)"
                  @input="onTextInput(MANUAL_COMMENTS, $event)"
                ></BaseTextarea>
              </label>
            </div>
          </section>

          <section class="incident-report-zone-card">
            <header class="zone-header">
              <h3>AI 正文（AI Body）</h3>
              <p>快填模式可一键生成完整正文，完整模式支持按段单独润色。</p>
            </header>

            <div class="mode-tabs">
              <BaseButton
                type="button"
                class="mode-tab-btn"
                variant="ghost"
                size="sm"
                :class="{ active: bodyMode === 'quick' }"
                @click="bodyMode = 'quick'"
              >
                快填模式
              </BaseButton>
              <BaseButton
                type="button"
                class="mode-tab-btn"
                variant="ghost"
                size="sm"
                :class="{ active: bodyMode === 'full' }"
                @click="bodyMode = 'full'"
              >
                完整模式
              </BaseButton>
            </div>

            <div v-if="bodyMode === 'quick'" class="zone-grid">
              <label class="field-item full-width">
                <span>快填内容（Quick Prompt）*</span>
                <BaseTextarea
                  rows="3"
                  class="quick-input-area"
                  :value="getTextAnswer(QUICK_NARRATIVE)"
                  placeholder="例如：3月12号下午3点客户下单报错，定位数据库 CPU 打满，3点半降级并加索引，4点恢复，后续加强 code review。"
                  @input="onTextInput(QUICK_NARRATIVE, $event)"
                ></BaseTextarea>
              </label>
              <div class="action-row">
                <BaseButton
                  type="button"
                  class="incident-report-primary-btn"
                  variant="primary"
                  @click="$emit('quick-generate-body')"
                >
                  一键生成正文
                </BaseButton>
                <BaseButton
                  v-if="sectionTraceMap.quick"
                  type="button"
                  class="incident-report-secondary-btn"
                  variant="secondary"
                  @click="$emit('open-trace', sectionTraceMap.quick)"
                >
                  查看链路
                </BaseButton>
              </div>
            </div>

            <div v-else class="zone-grid">
              <div class="section-card" :data-field="BODY_DESCRIPTION">
                <div class="section-header">
                  <h4>事故简述（Incident Summary）*</h4>
                  <div class="section-actions">
                    <BaseButton
                      type="button"
                      class="incident-report-secondary-btn"
                      variant="secondary"
                      @click="emitGenerateSection('description')"
                    >
                      生成
                    </BaseButton>
                    <BaseButton
                      v-if="sectionTraceMap.description"
                      type="button"
                      class="incident-report-secondary-btn"
                      variant="secondary"
                      @click="$emit('open-trace', sectionTraceMap.description)"
                    >
                      链路
                    </BaseButton>
                  </div>
                </div>
                <BaseTextarea
                  rows="4"
                  :class="{ invalid: missingFieldSet.has(BODY_DESCRIPTION) }"
                  :value="getTextAnswer(BODY_DESCRIPTION)"
                  @input="onTextInput(BODY_DESCRIPTION, $event)"
                ></BaseTextarea>
              </div>

              <div class="section-card" :data-field="BODY_TIMELINE">
                <div class="section-header">
                  <h4>时间线（Timeline）*</h4>
                </div>

                <div class="field-item full-width affected-date-editor">
                  <span>受影响日期摘要（Affected Date Summary）</span>
                  <div class="affected-date-grid">
                    <BaseDateTimePicker
                      mode="date"
                      placeholder="选择日期"
                      :model-value="affectedDateParts.date"
                      @update:model-value="
                        onAffectedDatePartChange('date', $event)
                      "
                    />
                    <div class="affected-time-pair">
                      <span class="affected-time-label">从</span>
                      <BaseDateTimePicker
                        mode="time"
                        placeholder="开始时间"
                        :model-value="affectedDateParts.from"
                        @update:model-value="
                          onAffectedDatePartChange(
                            'from',
                            normalizeTimeOnly($event),
                          )
                        "
                      />
                    </div>
                    <div class="affected-time-pair">
                      <span class="affected-time-label">至</span>
                      <BaseDateTimePicker
                        mode="time"
                        placeholder="结束时间"
                        :model-value="affectedDateParts.to"
                        @update:model-value="
                          onAffectedDatePartChange(
                            'to',
                            normalizeTimeOnly($event),
                          )
                        "
                      />
                    </div>
                  </div>
                </div>

                <div class="timeline-list">
                  <div
                    v-for="(item, index) in fullTimeline"
                    :key="`full-${index}`"
                    class="timeline-row full"
                  >
                    <BaseDateTimePicker
                      mode="time"
                      placeholder="时间"
                      :model-value="item.time"
                      @update:model-value="
                        onFullTimelineChange(
                          index,
                          'time',
                          normalizeTimeOnly($event),
                        )
                      "
                    />
                    <BaseInput
                      :value="item.event"
                      placeholder="发生了什么"
                      @input="onFullTimelineText(index, 'event', $event)"
                    />
                    <BaseInput
                      :value="item.resolution"
                      placeholder="如何处理"
                      @input="onFullTimelineText(index, 'resolution', $event)"
                    />
                    <BaseInput
                      :value="item.evidence"
                      placeholder="证据"
                      @input="onFullTimelineText(index, 'evidence', $event)"
                    />
                    <div class="timeline-inline-actions">
                      <BaseButton
                        type="button"
                        class="incident-report-secondary-btn"
                        variant="secondary"
                        @click="emitGenerateSection('timeline_item', index)"
                      >
                        生成
                      </BaseButton>
                      <BaseButton
                        v-if="sectionTraceMap[`timeline_item_${index}`]"
                        type="button"
                        class="incident-report-secondary-btn"
                        variant="secondary"
                        @click="
                          $emit(
                            'open-trace',
                            sectionTraceMap[`timeline_item_${index}`],
                          )
                        "
                      >
                        链路
                      </BaseButton>
                      <BaseButton
                        type="button"
                        class="danger-mini-btn"
                        variant="danger"
                        size="sm"
                        @click="removeFullTimelineItem(index)"
                      >
                        删除
                      </BaseButton>
                    </div>
                  </div>
                </div>
                <BaseButton
                  type="button"
                  class="incident-report-secondary-btn"
                  variant="secondary"
                  @click="addFullTimelineItem"
                >
                  新增时间线
                </BaseButton>
                <p
                  v-if="missingFieldSet.has(BODY_TIMELINE)"
                  class="incident-report-error-text"
                >
                  时间线至少需要一条。
                </p>
              </div>

              <div class="section-card" :data-field="BODY_IMPACT_SCOPE">
                <div class="section-header">
                  <h4>影响范围 / 严重级别（Impact / Severity）*</h4>
                  <div class="section-actions">
                    <BaseButton
                      type="button"
                      class="incident-report-secondary-btn"
                      variant="secondary"
                      @click="emitGenerateSection('impact')"
                    >
                      生成
                    </BaseButton>
                    <BaseButton
                      v-if="sectionTraceMap.impact"
                      type="button"
                      class="incident-report-secondary-btn"
                      variant="secondary"
                      @click="$emit('open-trace', sectionTraceMap.impact)"
                    >
                      链路
                    </BaseButton>
                  </div>
                </div>
                <label class="field-item">
                  <span>影响范围（Impact Scope）*</span>
                  <BaseInput
                    :class="{ invalid: missingFieldSet.has(BODY_IMPACT_SCOPE) }"
                    :value="getTextAnswer(BODY_IMPACT_SCOPE)"
                    @input="onTextInput(BODY_IMPACT_SCOPE, $event)"
                  />
                </label>
                <label class="field-item" :data-field="BODY_IMPACT_SEVERITY">
                  <span>严重级别（Impact Severity）*</span>
                  <BaseInput
                    :class="{
                      invalid: missingFieldSet.has(BODY_IMPACT_SEVERITY),
                    }"
                    :value="getTextAnswer(BODY_IMPACT_SEVERITY)"
                    @input="onTextInput(BODY_IMPACT_SEVERITY, $event)"
                  />
                </label>
                <label class="field-item full-width">
                  <span>业务影响（Business Impact）</span>
                  <BaseTextarea
                    rows="2"
                    :value="getTextAnswer(BODY_BUSINESS_IMPACT)"
                    @input="onTextInput(BODY_BUSINESS_IMPACT, $event)"
                  ></BaseTextarea>
                </label>
              </div>

              <div class="section-card" :data-field="BODY_ROOT_CAUSE">
                <div class="section-header">
                  <h4>根因分析（Root Cause）*</h4>
                  <div class="section-actions">
                    <BaseButton
                      type="button"
                      class="incident-report-secondary-btn"
                      variant="secondary"
                      @click="emitGenerateSection('root_cause')"
                    >
                      生成
                    </BaseButton>
                    <BaseButton
                      v-if="sectionTraceMap.root_cause"
                      type="button"
                      class="incident-report-secondary-btn"
                      variant="secondary"
                      @click="$emit('open-trace', sectionTraceMap.root_cause)"
                    >
                      链路
                    </BaseButton>
                  </div>
                </div>
                <label class="field-item">
                  <span>触发原因（Trigger）</span>
                  <BaseInput
                    :value="getTextAnswer(BODY_TRIGGER)"
                    @input="onTextInput(BODY_TRIGGER, $event)"
                  />
                </label>
                <label class="field-item full-width">
                  <span>根因（Root Cause）*</span>
                  <BaseTextarea
                    rows="3"
                    :class="{ invalid: missingFieldSet.has(BODY_ROOT_CAUSE) }"
                    :value="getTextAnswer(BODY_ROOT_CAUSE)"
                    @input="onTextInput(BODY_ROOT_CAUSE, $event)"
                  ></BaseTextarea>
                </label>
              </div>

              <div class="section-card" :data-field="BODY_FOLLOW_UP">
                <div class="section-header">
                  <h4>后续动作（Follow-Up Actions）*</h4>
                  <div class="section-actions">
                    <BaseButton
                      type="button"
                      class="incident-report-secondary-btn"
                      variant="secondary"
                      @click="emitGenerateSection('follow_up')"
                    >
                      生成
                    </BaseButton>
                    <BaseButton
                      v-if="sectionTraceMap.follow_up"
                      type="button"
                      class="incident-report-secondary-btn"
                      variant="secondary"
                      @click="$emit('open-trace', sectionTraceMap.follow_up)"
                    >
                      链路
                    </BaseButton>
                  </div>
                </div>
                <BaseTextarea
                  rows="4"
                  :class="{ invalid: missingFieldSet.has(BODY_FOLLOW_UP) }"
                  :value="getTextAnswer(BODY_FOLLOW_UP)"
                  @input="onTextInput(BODY_FOLLOW_UP, $event)"
                ></BaseTextarea>
              </div>
            </div>
          </section>

          <section class="incident-report-zone-card">
            <header class="zone-header">
              <h3>附录（Appendix）</h3>
              <p>
                支持富文本输入，可直接插入图片，生成文档时会同步写入附录页。
              </p>
            </header>
            <div class="zone-grid">
              <div class="field-item full-width">
                <span>附录内容（文本 + 图片）</span>
                <div class="appendix-editor-shell">
                  <div class="appendix-toolbar">
                    <BaseButton
                      type="button"
                      class="incident-report-secondary-btn"
                      variant="secondary"
                      @click="formatAppendixCommand('bold')"
                    >
                      加粗
                    </BaseButton>
                    <BaseButton
                      type="button"
                      class="incident-report-secondary-btn"
                      variant="secondary"
                      @click="formatAppendixCommand('insertUnorderedList')"
                    >
                      列表
                    </BaseButton>
                    <BaseFileUpload
                      class="appendix-image-upload"
                      accept="image/*"
                      multiple
                      @select="onAppendixRichImagesSelected"
                    >
                      插入图片
                    </BaseFileUpload>
                    <BaseButton
                      type="button"
                      class="incident-report-secondary-btn"
                      variant="secondary"
                      @click="clearAppendixContent"
                    >
                      清空
                    </BaseButton>
                  </div>
                  <div
                    ref="appendixEditorRef"
                    class="appendix-rich-editor"
                    contenteditable="true"
                    data-placeholder="请输入附录内容，可直接输入文字并插入图片"
                    @input="onAppendixRichInput"
                    @paste="onAppendixRichInput"
                    @blur="onAppendixRichInput"
                  ></div>
                </div>
              </div>
            </div>
          </section>
        </div>

        <section class="incident-report-preview-zone">
          <header class="zone-header">
            <h3>预览附件</h3>
            <p>表单内容编辑后会自动同步到预览，下载内容与预览保持一致。</p>
          </header>
          <div class="action-row">
            <BaseButton
              type="button"
              class="incident-report-secondary-btn"
              variant="secondary"
              @click="openPreviewDialog"
            >
              预览附件
            </BaseButton>
          </div>
          <p v-if="previewValidationError" class="incident-report-error-text">
            {{ previewValidationError }}
          </p>
        </section>
      </section>
    </Transition>

    <Teleport to="body">
      <Transition name="fade-slide-up">
        <div v-if="previewVisible" class="incident-report-modal-mask">
          <div class="incident-report-modal preview-modal">
            <div class="preview-header">
              <h3>附件预览</h3>
              <BaseButton
                type="button"
                class="incident-report-secondary-btn"
                variant="secondary"
                @click="closePreviewDialog"
              >
                关闭
              </BaseButton>
            </div>
            <div class="preview-body word-preview-body">
              <p v-if="previewLoading" class="preview-placeholder">
                正在生成预览，请稍候...
              </p>
              <p v-else-if="previewError" class="incident-report-error-text">
                {{ previewError }}
              </p>
              <iframe
                v-else-if="previewPdfSrc"
                class="word-preview-pdf-frame"
                :src="previewPdfSrc"
              ></iframe>
              <iframe
                v-else-if="previewHtml"
                class="word-preview-html-frame"
                :srcdoc="previewHtmlSrcDoc"
                sandbox="allow-same-origin"
              ></iframe>
              <p v-else class="preview-placeholder">暂无可预览内容。</p>
            </div>
            <div class="preview-footer">
              <BaseButton
                type="button"
                class="incident-report-secondary-btn"
                variant="secondary"
                :disabled="!canDownloadPreviewDocx"
                @click="onDownloadPreviewDocx"
              >
                下载当前预览文档
              </BaseButton>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <Teleport to="body">
      <Transition name="fade-slide-up">
        <div v-if="showGenerationModal" class="incident-report-modal-mask">
          <div class="incident-report-modal quick-generation-modal">
            <div class="preview-header">
              <h3>正在生成中</h3>
            </div>
            <div class="preview-body">
              <div class="generation-thinking-row">
                <span
                  class="generation-thinking-spinner"
                  aria-hidden="true"
                ></span>
                <p>{{ generationModalText }}</p>
              </div>
            </div>
            <div class="preview-footer">
              <BaseButton
                type="button"
                class="danger-mini-btn"
                variant="danger"
                size="sm"
                @click="$emit('stop-generation')"
              >
                停止
              </BaseButton>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
import BaseButton from '../../../components/base/BaseButton.vue';
import BaseDateTimePicker from '../../../components/base/BaseDateTimePicker.vue';
import BaseDropdown from '../../../components/base/BaseDropdown.vue';
import BaseFileUpload from '../../../components/base/BaseFileUpload.vue';
import BaseInput from '../../../components/base/BaseInput.vue';
import BaseTextarea from '../../../components/base/BaseTextarea.vue';
import type {
  IncidentReportFormAnswer,
  IncidentReportFormSchemaPayload,
  IncidentReportSessionDetail,
} from '../../../types/incident-report/incident-report';
import {
  normalizeTimeOnly,
  parseDateToken,
  parseAffectedDateSummary,
  composeAffectedDateSummary,
  type TimelineItem,
  type AffectedDateParts,
} from '../../../utils/incident-report/date-normalization';
import {
  MANUAL_REFERENCE_NO,
  MANUAL_FAULT_DATE,
  MANUAL_FAULT_TIME,
  MANUAL_REPORTING_PERSON,
  MANUAL_VERIFIED_BY,
  MANUAL_SITE_ID,
  MANUAL_SYSTEM,
  MANUAL_LOCATION,
  MANUAL_FAULT_SYMPTOM,
  MANUAL_ARRIVAL_DATETIME,
  MANUAL_CLEARANCE_DATETIME,
  MANUAL_SERVICE_PERSON,
  MANUAL_FAULT_CAUSE,
  MANUAL_MATERIALS_USED,
  MANUAL_REPAIR_DETAILS,
  MANUAL_CONTRACTOR_STAFF,
  MANUAL_CONTRACTOR_SIGNATURE,
  MANUAL_CONTRACTOR_DATE,
  MANUAL_STATUS,
  MANUAL_STATUS_REF_NO,
  MANUAL_SEVERITY,
  MANUAL_COMMENTS,
  MANUAL_EMPLOYER_REP,
  MANUAL_EMPLOYER_SIGNATURE,
  MANUAL_CLOSEOUT_DATE,
  QUICK_NARRATIVE,
  BODY_DESCRIPTION,
  BODY_AFFECTED_DATE,
  BODY_TIMELINE,
  BODY_IMPACT_SCOPE,
  BODY_IMPACT_SEVERITY,
  BODY_BUSINESS_IMPACT,
  BODY_TRIGGER,
  BODY_ROOT_CAUSE,
  BODY_FOLLOW_UP,
  APPENDIX_NOTES,
  APPENDIX_IMAGES,
  PREVIEW_REQUIRED_FIELDS,
  STATUS_OPTION_FOLLOW_UP_ACTION_REQUIRED,
  statusOptions,
  severityOptions,
  normalizeStatusOption,
  normalizeSeverityOption,
  DOCX_SAFE_IMAGE_MIME_TYPES,
} from '../../../utils/incident-report/constants';

interface AppendixImageItem {
  name: string;
  dataUrl: string;
}

const props = withDefaults(
  defineProps<{
    schema: IncidentReportFormSchemaPayload | null;
    session: IncidentReportSessionDetail | null;
    isGenerating: boolean;
    generationState: 'idle' | 'generating' | 'done';
    generationTask?: 'none' | 'attachment' | 'quick-body' | 'section';
    previewHtml?: string;
    previewPdfBase64?: string;
    previewDocxBase64?: string;
    previewLoading?: boolean;
    previewError?: string;
  }>(),
  {
    generationTask: 'none',
    previewHtml: '',
    previewPdfBase64: '',
    previewDocxBase64: '',
    previewLoading: false,
    previewError: '',
  },
);

const emit = defineEmits<{
  (e: 'start'): void;
  (
    e: 'update-answers',
    answers: Record<string, IncidentReportFormAnswer>,
  ): void;
  (e: 'quick-generate-body'): void;
  (
    e: 'generate-section',
    payload: { sectionId: string; timelineIndex?: number },
  ): void;
  (e: 'download-preview-docx'): void;
  (e: 'open-trace', traceId: string): void;
  (e: 'stop-generation'): void;
  (e: 'request-preview'): void;
  (e: 'cancel-preview'): void;
}>();

const localAnswers = ref<Record<string, IncidentReportFormAnswer>>({});
const bodyMode = ref<'quick' | 'full'>('quick');
const previewVisible = ref(false);
const appendixEditorRef = ref<HTMLDivElement | null>(null);
let syncingAnswersFromSession = false;
const missingFieldIds = ref<string[]>([]);
const previewValidationError = ref('');

const previewHtml = computed(() => props.previewHtml ?? '');
const previewHtmlSrcDoc = computed(() => {
  const rawHtml = previewHtml.value.trim();
  if (!rawHtml) {
    return '';
  }
  const sanitizedHtml = rawHtml
    .replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, '')
    .replace(/\son\w+=(['"]).*?\1/gi, '');
  return [
    '<!doctype html>',
    '<html><head><meta charset="utf-8" />',
    '<style>',
    'html, body { margin: 0; padding: 0; background: #fff; }',
    'body { font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif; line-height: 1.5; color: #0f172a; padding: 1.8rem; }',
    'p { margin: 0.5rem 0; }',
    'table { width: 100%; border-collapse: collapse; margin: 0.75rem 0; }',
    'td, th { border: 1px solid #dbe3ee; padding: 0.4rem 0.45rem; vertical-align: top; }',
    'img { max-width: 100%; height: auto; border-radius: 8px; }',
    '</style></head><body>',
    sanitizedHtml,
    '</body></html>',
  ].join('');
});
const previewPdfSrc = computed(() => {
  const base64 = (props.previewPdfBase64 ?? '').trim();
  if (!base64) {
    return '';
  }
  return `data:application/pdf;base64,${base64}#toolbar=0&navpanes=0&scrollbar=0`;
});
const previewLoading = computed(() => props.previewLoading ?? false);
const previewError = computed(() => props.previewError ?? '');

const normalizeHtmlForCompare = (value: string) => {
  return value.replace(/\s+/g, ' ').trim();
};

const escapeHtml = (value: string) => {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
};

const toRichHtml = (value: string) => {
  const lines = value
    .split(/\n+/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
  if (!lines.length) {
    return '';
  }
  return lines.map((line) => `<p>${escapeHtml(line)}</p>`).join('');
};

const isProbablyHtml = (value: string) => /<[^>]+>/.test(value);

const buildAffectedDatePartsFromTimeline = (timeline: TimelineItem[]) => {
  const current = parseAffectedDateSummary(getTextAnswer(BODY_AFFECTED_DATE));
  const fallbackDate = parseDateToken(getTextAnswer(MANUAL_FAULT_DATE));
  const sortedTimes = timeline
    .map((item) => normalizeTimeOnly(item.time))
    .filter((item) => item.length > 0)
    .sort();
  const from = sortedTimes[0] ?? '';
  const to = sortedTimes[sortedTimes.length - 1] ?? from;
  return {
    date: fallbackDate || current.date,
    from,
    to,
  } satisfies AffectedDateParts;
};

const syncAffectedDateSummaryFromTimeline = (timeline: TimelineItem[]) => {
  const hasTimelineTime = timeline.some(
    (item) => normalizeTimeOnly(item.time).length > 0,
  );
  if (!hasTimelineTime) {
    return;
  }
  const nextParts = buildAffectedDatePartsFromTimeline(timeline);
  const nextSummary = composeAffectedDateSummary(nextParts);
  if (nextSummary === getTextAnswer(BODY_AFFECTED_DATE)) {
    return;
  }
  setAnswerValue(BODY_AFFECTED_DATE, nextSummary);
};

const getTextAnswer = (fieldId: string) => {
  const value = localAnswers.value[fieldId]?.value;
  return typeof value === 'string' ? value : '';
};

const ensureAnswer = (fieldId: string) => {
  if (!localAnswers.value[fieldId]) {
    localAnswers.value[fieldId] = {
      value: '',
      customValue: '',
    };
  }
  return localAnswers.value[fieldId];
};

const emitAnswersUpdate = () => {
  emit('update-answers', JSON.parse(JSON.stringify(localAnswers.value)));
};

const areAnswerValuesEqual = (left: unknown, right: unknown) => {
  if (left === right) {
    return true;
  }
  if (typeof left === 'string' || typeof right === 'string') {
    return String(left ?? '') === String(right ?? '');
  }
  try {
    return JSON.stringify(left) === JSON.stringify(right);
  } catch {
    return false;
  }
};

const setAnswerValue = (
  fieldId: string,
  value: unknown,
  options?: { force?: boolean },
) => {
  const answer = ensureAnswer(fieldId);
  if (!options?.force && areAnswerValuesEqual(answer.value, value)) {
    return;
  }
  answer.value = value;
  emitAnswersUpdate();
  if (missingFieldIds.value.length > 0 || previewValidationError.value) {
    const nextMissing = collectMissingRequiredFields();
    missingFieldIds.value = nextMissing;
    if (!nextMissing.length) {
      previewValidationError.value = '';
    }
  }
  if (!syncingAnswersFromSession) {
    scheduleDraftPreviewRefresh();
  }
  if (fieldId === MANUAL_FAULT_DATE) {
    syncAffectedDateSummaryFromTimeline(fullTimeline.value);
  }
};

const onTextInput = (fieldId: string, event: Event) => {
  const target = event.target as HTMLInputElement | HTMLTextAreaElement;
  setAnswerValue(fieldId, target.value);
};

const onStatusChange = (value: string) => {
  const nextValue = normalizeStatusOption(value);
  setAnswerValue(MANUAL_STATUS, nextValue);
  if (nextValue !== STATUS_OPTION_FOLLOW_UP_ACTION_REQUIRED) {
    setAnswerValue(MANUAL_STATUS_REF_NO, '');
  }
};

const onSeverityChange = (value: string) => {
  setAnswerValue(MANUAL_SEVERITY, normalizeSeverityOption(value));
};

const onAffectedDatePartChange = (
  key: keyof AffectedDateParts,
  value: string,
) => {
  const parts = parseAffectedDateSummary(getTextAnswer(BODY_AFFECTED_DATE));
  const nextParts: AffectedDateParts = {
    ...parts,
    [key]: value,
  };
  setAnswerValue(BODY_AFFECTED_DATE, composeAffectedDateSummary(nextParts));
};

const hasValue = (fieldId: string) => {
  return getTextAnswer(fieldId).trim().length > 0;
};

const hasValidTimelineItem = () => {
  const timelineValue = localAnswers.value[BODY_TIMELINE]?.value;
  if (!Array.isArray(timelineValue)) {
    return false;
  }
  return timelineValue.some((item) => {
    if (typeof item !== 'object' || item === null) {
      return false;
    }
    const candidate = item as Record<string, unknown>;
    const time = normalizeTimeOnly(
      typeof candidate.time === 'string' ? candidate.time : '',
    );
    const event =
      typeof candidate.event === 'string' ? candidate.event.trim() : '';
    return time.length > 0 && event.length > 0;
  });
};

const collectMissingRequiredFields = () => {
  const missing: string[] = PREVIEW_REQUIRED_FIELDS.filter(
    (fieldId) => !hasValue(fieldId),
  );
  if (!hasValidTimelineItem()) {
    missing.push(BODY_TIMELINE);
  }
  return missing;
};

const focusAndScrollToField = (fieldId: string) => {
  const target = document.querySelector(
    `[data-field="${fieldId}"]`,
  ) as HTMLElement | null;
  if (!target) {
    if (fieldId.startsWith('body_') && bodyMode.value !== 'full') {
      bodyMode.value = 'full';
      void nextTick(() => {
        focusAndScrollToField(fieldId);
      });
    }
    return;
  }
  target.scrollIntoView({
    behavior: 'smooth',
    block: 'center',
  });
  const focusTarget = target.querySelector(
    'input, textarea, .date-time-trigger, [contenteditable="true"]',
  ) as HTMLElement | null;
  focusTarget?.focus?.();
};

const validateBeforePreview = () => {
  const missing = collectMissingRequiredFields();
  missingFieldIds.value = missing;
  if (!missing.length) {
    previewValidationError.value = '';
    return true;
  }
  previewValidationError.value = '存在必填项未填写，请先补充后再预览附件。';
  focusAndScrollToField(missing[0]);
  return false;
};

const parseLegacyAppendixImages = (): AppendixImageItem[] => {
  const value = localAnswers.value[APPENDIX_IMAGES]?.value;
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .filter((item) => {
      if (typeof item !== 'object' || item === null) {
        return false;
      }
      const candidate = item as Record<string, unknown>;
      return (
        typeof candidate.name === 'string' &&
        typeof candidate.dataUrl === 'string' &&
        candidate.name.length > 0 &&
        candidate.dataUrl.length > 0
      );
    })
    .map((item) => item as AppendixImageItem);
};

const syncAppendixEditorFromAnswer = () => {
  const editor = appendixEditorRef.value;
  if (!editor) {
    return;
  }
  if (document.activeElement === editor) {
    return;
  }
  const raw = getTextAnswer(APPENDIX_NOTES);
  const nextHtml = raw
    ? isProbablyHtml(raw)
      ? raw
      : escapeHtml(raw).replace(/\n/g, '<br>')
    : '';
  if (
    normalizeHtmlForCompare(editor.innerHTML) ===
    normalizeHtmlForCompare(nextHtml)
  ) {
    return;
  }
  editor.innerHTML = nextHtml;
};

const migrateLegacyAppendixImages = () => {
  const images = parseLegacyAppendixImages();
  if (!images.length) {
    return;
  }
  const existing = getTextAnswer(APPENDIX_NOTES);
  if (/<img[\s>]/i.test(existing)) {
    setAnswerValue(APPENDIX_IMAGES, []);
    return;
  }
  const baseHtml = existing
    ? isProbablyHtml(existing)
      ? existing
      : toRichHtml(existing)
    : '';
  const imageHtml = images
    .map(
      (image) =>
        `<p><img src="${image.dataUrl}" alt="${escapeHtml(image.name)}" /></p>`,
    )
    .join('');
  setAnswerValue(APPENDIX_NOTES, `${baseHtml}${imageHtml}`);
  setAnswerValue(APPENDIX_IMAGES, []);
};

watch(
  () => props.session?.snapshot.formAnswers,
  async (nextAnswers) => {
    syncingAnswersFromSession = true;
    try {
      missingFieldIds.value = [];
      previewValidationError.value = '';
      localAnswers.value = JSON.parse(
        JSON.stringify(nextAnswers ?? {}),
      ) as Record<string, IncidentReportFormAnswer>;
      syncAppendixEditorFromAnswer();
      migrateLegacyAppendixImages();
      await nextTick();
      syncAppendixEditorFromAnswer();
    } finally {
      syncingAnswersFromSession = false;
    }
  },
  { immediate: true },
);

watch(appendixEditorRef, (editor) => {
  if (editor) {
    syncAppendixEditorFromAnswer();
    migrateLegacyAppendixImages();
  }
});

watch(
  () => props.session?.id,
  () => {
    const editor = appendixEditorRef.value;
    if (editor && document.activeElement !== editor) {
      editor.innerHTML = '';
    }
    emit('cancel-preview');
    previewVisible.value = false;
  },
);

const statusLabel = computed(() => {
  const status = props.session?.status ?? 'draft';
  if (status === 'generated') {
    return '已生成';
  }
  if (status === 'generating') {
    return '生成中';
  }
  if (status === 'failed') {
    return '失败';
  }
  return '';
});

const showGenerationModal = computed(() => {
  return (
    props.isGenerating &&
    props.generationState === 'generating' &&
    (props.generationTask === 'quick-body' ||
      props.generationTask === 'section')
  );
});

const generationModalText = computed(() => {
  if (props.generationTask === 'quick-body') {
    return '正在根据快填模式参考生成完整正文，请稍候。';
  }
  if (props.generationTask === 'section') {
    return '正在根据当前分段参考生成内容，请稍候。';
  }
  return '正在生成内容，请稍候。';
});

const sectionTraceMap = computed<Record<string, string>>(() => {
  return (props.session?.snapshot.sectionTraceIds ?? {}) as Record<
    string,
    string
  >;
});

const canDownloadPreviewDocx = computed(() => {
  return Boolean((props.previewDocxBase64 ?? '').trim());
});

const selectedStatusOption = computed(() =>
  normalizeStatusOption(getTextAnswer(MANUAL_STATUS)),
);

const selectedSeverityOption = computed(() =>
  normalizeSeverityOption(getTextAnswer(MANUAL_SEVERITY)),
);

const affectedDateParts = computed(() => {
  return parseAffectedDateSummary(getTextAnswer(BODY_AFFECTED_DATE));
});

const missingFieldSet = computed(() => new Set<string>(missingFieldIds.value));

const parseTimeline = (fieldId: string): TimelineItem[] => {
  const value = localAnswers.value[fieldId]?.value;
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => {
    if (typeof item !== 'object' || item === null) {
      return {
        time: '',
        event: '',
        resolution: '',
        evidence: '',
      };
    }
    const candidate = item as Record<string, unknown>;
    return {
      time:
        typeof candidate.time === 'string'
          ? normalizeTimeOnly(candidate.time)
          : '',
      event: typeof candidate.event === 'string' ? candidate.event : '',
      resolution:
        typeof candidate.resolution === 'string' ? candidate.resolution : '',
      evidence:
        typeof candidate.evidence === 'string' ? candidate.evidence : '',
    };
  });
};

const fullTimeline = computed(() => parseTimeline(BODY_TIMELINE));

const setTimeline = (fieldId: string, timeline: TimelineItem[]) => {
  const normalizedTimeline = timeline.map((item) => ({
    time: normalizeTimeOnly(item.time),
    event: item.event,
    resolution: item.resolution,
    evidence: item.evidence,
  }));
  setAnswerValue(fieldId, normalizedTimeline);
  if (fieldId === BODY_TIMELINE) {
    syncAffectedDateSummaryFromTimeline(normalizedTimeline);
  }
};

const buildEmptyTimelineItem = (time = ''): TimelineItem => ({
  time: normalizeTimeOnly(time),
  event: '',
  resolution: '',
  evidence: '',
});

const addFullTimelineItem = () => {
  const previousTime =
    fullTimeline.value.length > 0
      ? normalizeTimeOnly(
          fullTimeline.value[fullTimeline.value.length - 1]?.time ?? '',
        )
      : '';
  const next = [...fullTimeline.value, buildEmptyTimelineItem(previousTime)];
  setTimeline(BODY_TIMELINE, next);
};

const removeFullTimelineItem = (index: number) => {
  const next = fullTimeline.value.filter((_, current) => current !== index);
  setTimeline(BODY_TIMELINE, next);
};

const onFullTimelineChange = (
  index: number,
  key: keyof TimelineItem,
  value: string,
) => {
  const next = [...fullTimeline.value];
  if (!next[index]) {
    return;
  }
  let nextValue = key === 'time' ? normalizeTimeOnly(value) : value;
  if (key === 'time' && nextValue && index > 0) {
    const previousTime = normalizeTimeOnly(next[index - 1]?.time ?? '');
    if (previousTime && nextValue < previousTime) {
      nextValue = previousTime;
    }
  }
  next[index] = {
    ...next[index],
    [key]: nextValue,
  };
  setTimeline(BODY_TIMELINE, next);
};

const onFullTimelineText = (
  index: number,
  key: keyof TimelineItem,
  event: Event,
) => {
  onFullTimelineChange(index, key, (event.target as HTMLInputElement).value);
};

const readFileAsDataURL = (file: File) =>
  new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ''));
    reader.onerror = () => reject(new Error('读取图片失败'));
    reader.readAsDataURL(file);
  });

const normalizeMimeType = (raw: string) => {
  const value = raw.trim().toLowerCase();
  if (value === 'image/jpg') {
    return 'image/jpeg';
  }
  return value;
};

const loadImageElementFromFile = (file: File) =>
  new Promise<HTMLImageElement>((resolve, reject) => {
    const objectUrl = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      URL.revokeObjectURL(objectUrl);
      resolve(image);
    };
    image.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      reject(new Error('加载图片失败'));
    };
    image.src = objectUrl;
  });

const convertImageFileToDocxDataUrl = async (file: File) => {
  const mimeType = normalizeMimeType(file.type);
  const canKeepOriginal =
    DOCX_SAFE_IMAGE_MIME_TYPES.has(mimeType) && file.size <= 5 * 1024 * 1024;
  if (canKeepOriginal) {
    return readFileAsDataURL(file);
  }

  try {
    const image = await loadImageElementFromFile(file);
    const maxEdge = 2200;
    const scale = Math.min(1, maxEdge / Math.max(image.width, image.height));
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(1, Math.round(image.width * scale));
    canvas.height = Math.max(1, Math.round(image.height * scale));
    const context = canvas.getContext('2d');
    if (!context) {
      return readFileAsDataURL(file);
    }
    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    const outputType = DOCX_SAFE_IMAGE_MIME_TYPES.has(mimeType)
      ? mimeType
      : 'image/png';
    return outputType === 'image/jpeg'
      ? canvas.toDataURL(outputType, 0.9)
      : canvas.toDataURL(outputType);
  } catch {
    return readFileAsDataURL(file);
  }
};

const onAppendixRichInput = () => {
  const editor = appendixEditorRef.value;
  if (!editor) {
    return;
  }
  setAnswerValue(APPENDIX_NOTES, editor.innerHTML, { force: true });
};

const formatAppendixCommand = (command: string) => {
  appendixEditorRef.value?.focus();
  document.execCommand(command);
  onAppendixRichInput();
};

const clearAppendixContent = () => {
  if (!appendixEditorRef.value) {
    return;
  }
  appendixEditorRef.value.innerHTML = '';
  onAppendixRichInput();
};

const onAppendixRichImagesSelected = async (files: File[]) => {
  if (files.length === 0 || !appendixEditorRef.value) {
    return;
  }
  let currentHtml = appendixEditorRef.value.innerHTML;
  for (const file of files) {
    const dataUrl = await convertImageFileToDocxDataUrl(file);
    currentHtml += `<p><img src="${dataUrl}" alt="${escapeHtml(file.name)}" /></p>`;
  }
  appendixEditorRef.value.innerHTML = currentHtml;
  onAppendixRichInput();
};

const emitGenerateSection = (sectionId: string, timelineIndex?: number) => {
  emit('generate-section', {
    sectionId,
    timelineIndex,
  });
};

const onDownloadPreviewDocx = () => {
  if (!canDownloadPreviewDocx.value) {
    return;
  }
  emit('download-preview-docx');
};

const requestPreview = () => {
  emit('request-preview');
};

const openPreviewDialog = () => {
  if (!validateBeforePreview()) {
    return;
  }
  previewVisible.value = true;
  requestPreview();
};

const closePreviewDialog = () => {
  previewVisible.value = false;
  emit('cancel-preview');
};

watch(previewVisible, (visible) => {
  if (visible) {
    return;
  }
  emit('cancel-preview');
});

let previewRefreshTimer: number | null = null;
const scheduleDraftPreviewRefresh = () => {
  if (!previewVisible.value) {
    return;
  }
  if (previewRefreshTimer !== null) {
    window.clearTimeout(previewRefreshTimer);
    previewRefreshTimer = null;
  }
  previewRefreshTimer = window.setTimeout(() => {
    requestPreview();
  }, 360);
};

watch(
  fullTimeline,
  (timeline) => {
    if (syncingAnswersFromSession) {
      return;
    }
    syncAffectedDateSummaryFromTimeline(timeline);
  },
  { deep: true },
);

onBeforeUnmount(() => {
  emit('cancel-preview');
  if (previewRefreshTimer !== null) {
    window.clearTimeout(previewRefreshTimer);
    previewRefreshTimer = null;
  }
});
</script>

<style scoped src="../styles/incident-report-workspace.css"></style>
