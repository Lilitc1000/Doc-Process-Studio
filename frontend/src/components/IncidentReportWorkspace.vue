<template>
  <div class="incident-workspace">
    <Transition name="session-switch" mode="out-in">
      <section v-if="!session" key="welcome" class="incident-welcome">
        <h2>事故报告助手</h2>
        <p class="incident-welcome-text">
          {{
            schema?.intro_message ||
            '欢迎使用事故报告专区。支持快填生成正文、完整分段润色、附录富文本编辑与多版本附件历史。'
          }}
        </p>
        <ul class="incident-welcome-list">
          <li>手工首页字段与参考文档第一页保持一致。</li>
          <li>AI 正文支持快填和完整模式联动生成。</li>
          <li>附件生成支持历史版本对比与下载。</li>
        </ul>
        <button
          type="button"
          class="incident-primary-btn"
          @click="$emit('start')"
        >
          开始
        </button>
      </section>

      <section v-else key="form" class="incident-form-page">
        <header class="incident-form-header">
          <h2>{{ session.title }}</h2>
          <span v-if="statusLabel" class="incident-status">{{
            statusLabel
          }}</span>
        </header>

        <div class="incident-zone-grid">
          <section class="incident-zone-card">
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
                <input
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
                <DateTimeField
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
                <DateTimeField
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
                <input
                  :value="getTextAnswer(MANUAL_REPORTING_PERSON)"
                  :class="{
                    invalid: missingFieldSet.has(MANUAL_REPORTING_PERSON),
                  }"
                  @input="onTextInput(MANUAL_REPORTING_PERSON, $event)"
                />
              </label>

              <label class="field-item">
                <span>审核人（Verified By）</span>
                <input
                  :value="getTextAnswer(MANUAL_VERIFIED_BY)"
                  @input="onTextInput(MANUAL_VERIFIED_BY, $event)"
                />
              </label>

              <label class="field-item" :data-field="MANUAL_SITE_ID">
                <span>站点编号（Site ID）*</span>
                <input
                  :value="getTextAnswer(MANUAL_SITE_ID)"
                  :class="{ invalid: missingFieldSet.has(MANUAL_SITE_ID) }"
                  @input="onTextInput(MANUAL_SITE_ID, $event)"
                />
              </label>

              <label class="field-item" :data-field="MANUAL_SYSTEM">
                <span>系统 / 子系统（System / Subsystems）*</span>
                <input
                  :value="getTextAnswer(MANUAL_SYSTEM)"
                  :class="{ invalid: missingFieldSet.has(MANUAL_SYSTEM) }"
                  @input="onTextInput(MANUAL_SYSTEM, $event)"
                />
              </label>

              <label class="field-item" :data-field="MANUAL_LOCATION">
                <span>故障位置（Location of Fault）*</span>
                <input
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
                <textarea
                  rows="3"
                  :value="getTextAnswer(MANUAL_FAULT_SYMPTOM)"
                  :class="{
                    invalid: missingFieldSet.has(MANUAL_FAULT_SYMPTOM),
                  }"
                  @input="onTextInput(MANUAL_FAULT_SYMPTOM, $event)"
                ></textarea>
              </label>

              <label class="field-item">
                <span>到场时间（Arrival Datetime）</span>
                <DateTimeField
                  mode="datetime"
                  :model-value="getTextAnswer(MANUAL_ARRIVAL_DATETIME)"
                  @update:model-value="
                    setAnswerValue(MANUAL_ARRIVAL_DATETIME, $event)
                  "
                />
              </label>

              <label class="field-item">
                <span>恢复时间（Clearance Datetime）</span>
                <DateTimeField
                  mode="datetime"
                  :model-value="getTextAnswer(MANUAL_CLEARANCE_DATETIME)"
                  @update:model-value="
                    setAnswerValue(MANUAL_CLEARANCE_DATETIME, $event)
                  "
                />
              </label>

              <label class="field-item">
                <span>维护人员（Service Person）</span>
                <input
                  :value="getTextAnswer(MANUAL_SERVICE_PERSON)"
                  @input="onTextInput(MANUAL_SERVICE_PERSON, $event)"
                />
              </label>

              <label class="field-item">
                <span>故障原因（Fault Cause）</span>
                <input
                  :value="getTextAnswer(MANUAL_FAULT_CAUSE)"
                  @input="onTextInput(MANUAL_FAULT_CAUSE, $event)"
                />
              </label>

              <label class="field-item">
                <span>使用物料（Materials Used）</span>
                <input
                  :value="getTextAnswer(MANUAL_MATERIALS_USED)"
                  @input="onTextInput(MANUAL_MATERIALS_USED, $event)"
                />
              </label>

              <div class="manual-section-heading">
                <h4>SECTION B - 维修与验证（Repair Works & Verification）</h4>
              </div>

              <label class="field-item full-width">
                <span>维修详情（Repair Details）</span>
                <textarea
                  rows="3"
                  :value="getTextAnswer(MANUAL_REPAIR_DETAILS)"
                  @input="onTextInput(MANUAL_REPAIR_DETAILS, $event)"
                ></textarea>
              </label>

              <label class="field-item">
                <span>承包商人员（Contractor Staff）</span>
                <input
                  :value="getTextAnswer(MANUAL_CONTRACTOR_STAFF)"
                  @input="onTextInput(MANUAL_CONTRACTOR_STAFF, $event)"
                />
              </label>

              <label class="field-item">
                <span>承包商签名（Contractor Signature）</span>
                <input
                  :value="getTextAnswer(MANUAL_CONTRACTOR_SIGNATURE)"
                  @input="onTextInput(MANUAL_CONTRACTOR_SIGNATURE, $event)"
                />
              </label>

              <label class="field-item">
                <span>承包商日期（Contractor Date）</span>
                <DateTimeField
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
                <div ref="statusDropdownRef" class="manual-dropdown">
                  <button
                    type="button"
                    class="manual-dropdown-trigger"
                    :class="{ open: statusDropdownOpen }"
                    aria-haspopup="listbox"
                    :aria-expanded="statusDropdownOpen"
                    aria-label="状态（Status）"
                    @click="toggleStatusDropdown"
                    @keydown.enter.prevent="toggleStatusDropdown"
                    @keydown.space.prevent="toggleStatusDropdown"
                    @keydown.esc.prevent="closeManualDropdowns"
                  >
                    <span class="manual-dropdown-trigger-text">{{
                      selectedStatusLabel
                    }}</span>
                    <span
                      class="manual-dropdown-trigger-icon"
                      aria-hidden="true"
                    >
                      <svg viewBox="0 0 16 16">
                        <path
                          d="M3.5 6.25L8 10.75L12.5 6.25"
                          fill="none"
                          stroke="currentColor"
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                        />
                      </svg>
                    </span>
                  </button>
                  <Transition name="dropdown">
                    <div
                      v-if="statusDropdownOpen"
                      class="manual-dropdown-panel"
                      role="listbox"
                    >
                      <button
                        v-for="option in statusOptions"
                        :key="option.value"
                        type="button"
                        class="manual-dropdown-option"
                        :class="{
                          active: option.value === selectedStatusOption,
                        }"
                        @click="selectStatusOption(option.value)"
                      >
                        <span>{{ option.label }}</span>
                        <span
                          v-if="option.value === selectedStatusOption"
                          class="manual-dropdown-option-tag"
                        >
                          当前
                        </span>
                      </button>
                    </div>
                  </Transition>
                </div>
              </label>

              <label
                v-if="
                  selectedStatusOption ===
                  STATUS_OPTION_FOLLOW_UP_ACTION_REQUIRED
                "
                class="field-item"
              >
                <span>跟进单号（Follow-up Ref No.）</span>
                <input
                  :value="getTextAnswer(MANUAL_STATUS_REF_NO)"
                  placeholder="例如：DAS2-FAULT-016"
                  @input="onTextInput(MANUAL_STATUS_REF_NO, $event)"
                />
              </label>

              <label class="field-item">
                <span>严重级别（Severity）</span>
                <div ref="severityDropdownRef" class="manual-dropdown">
                  <button
                    type="button"
                    class="manual-dropdown-trigger"
                    :class="{ open: severityDropdownOpen }"
                    aria-haspopup="listbox"
                    :aria-expanded="severityDropdownOpen"
                    aria-label="严重级别（Severity）"
                    @click="toggleSeverityDropdown"
                    @keydown.enter.prevent="toggleSeverityDropdown"
                    @keydown.space.prevent="toggleSeverityDropdown"
                    @keydown.esc.prevent="closeManualDropdowns"
                  >
                    <span class="manual-dropdown-trigger-text">{{
                      selectedSeverityLabel
                    }}</span>
                    <span
                      class="manual-dropdown-trigger-icon"
                      aria-hidden="true"
                    >
                      <svg viewBox="0 0 16 16">
                        <path
                          d="M3.5 6.25L8 10.75L12.5 6.25"
                          fill="none"
                          stroke="currentColor"
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                        />
                      </svg>
                    </span>
                  </button>
                  <Transition name="dropdown">
                    <div
                      v-if="severityDropdownOpen"
                      class="manual-dropdown-panel"
                      role="listbox"
                    >
                      <button
                        v-for="option in severityOptions"
                        :key="option.value"
                        type="button"
                        class="manual-dropdown-option"
                        :class="{
                          active: option.value === selectedSeverityOption,
                        }"
                        @click="selectSeverityOption(option.value)"
                      >
                        <span>{{ option.label }}</span>
                        <span
                          v-if="option.value === selectedSeverityOption"
                          class="manual-dropdown-option-tag"
                        >
                          当前
                        </span>
                      </button>
                    </div>
                  </Transition>
                </div>
              </label>

              <label class="field-item">
                <span>业主代表（Employer Rep）</span>
                <input
                  :value="getTextAnswer(MANUAL_EMPLOYER_REP)"
                  @input="onTextInput(MANUAL_EMPLOYER_REP, $event)"
                />
              </label>

              <label class="field-item">
                <span>业主代表签名（Employer Signature）</span>
                <input
                  :value="getTextAnswer(MANUAL_EMPLOYER_SIGNATURE)"
                  @input="onTextInput(MANUAL_EMPLOYER_SIGNATURE, $event)"
                />
              </label>

              <label class="field-item">
                <span>结案日期（Closeout Date）</span>
                <DateTimeField
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
                <textarea
                  rows="2"
                  :value="getTextAnswer(MANUAL_COMMENTS)"
                  @input="onTextInput(MANUAL_COMMENTS, $event)"
                ></textarea>
              </label>
            </div>
          </section>

          <section class="incident-zone-card">
            <header class="zone-header">
              <h3>AI 正文（AI Body）</h3>
              <p>快填模式可一键生成完整正文，完整模式支持按段单独润色。</p>
            </header>

            <div class="mode-tabs">
              <button
                type="button"
                class="mode-tab-btn"
                :class="{ active: bodyMode === 'quick' }"
                @click="bodyMode = 'quick'"
              >
                快填模式
              </button>
              <button
                type="button"
                class="mode-tab-btn"
                :class="{ active: bodyMode === 'full' }"
                @click="bodyMode = 'full'"
              >
                完整模式
              </button>
            </div>

            <div v-if="bodyMode === 'quick'" class="zone-grid">
              <label class="field-item full-width">
                <span>快填内容（Quick Prompt）*</span>
                <textarea
                  rows="3"
                  class="quick-input-area"
                  :value="getTextAnswer(QUICK_NARRATIVE)"
                  placeholder="例如：3月12号下午3点客户下单报错，定位数据库 CPU 打满，3点半降级并加索引，4点恢复，后续加强 code review。"
                  @input="onTextInput(QUICK_NARRATIVE, $event)"
                ></textarea>
              </label>
              <div class="action-row">
                <button
                  type="button"
                  class="incident-primary-btn"
                  @click="$emit('quick-generate-body')"
                >
                  一键生成正文
                </button>
                <button
                  v-if="sectionTraceMap.quick"
                  type="button"
                  class="incident-secondary-btn"
                  @click="$emit('open-trace', sectionTraceMap.quick)"
                >
                  查看链路
                </button>
              </div>
            </div>

            <div v-else class="zone-grid">
              <div class="section-card" :data-field="BODY_DESCRIPTION">
                <div class="section-header">
                  <h4>事故简述（Incident Summary）*</h4>
                  <div class="section-actions">
                    <button
                      type="button"
                      class="incident-secondary-btn"
                      @click="emitGenerateSection('description')"
                    >
                      生成
                    </button>
                    <button
                      v-if="sectionTraceMap.description"
                      type="button"
                      class="incident-secondary-btn"
                      @click="$emit('open-trace', sectionTraceMap.description)"
                    >
                      链路
                    </button>
                  </div>
                </div>
                <textarea
                  rows="4"
                  :class="{ invalid: missingFieldSet.has(BODY_DESCRIPTION) }"
                  :value="getTextAnswer(BODY_DESCRIPTION)"
                  @input="onTextInput(BODY_DESCRIPTION, $event)"
                ></textarea>
              </div>

              <div class="section-card" :data-field="BODY_TIMELINE">
                <div class="section-header">
                  <h4>时间线（Timeline）*</h4>
                </div>

                <div class="field-item full-width affected-date-editor">
                  <span>受影响日期摘要（Affected Date Summary）</span>
                  <div class="affected-date-grid">
                    <DateTimeField
                      mode="date"
                      placeholder="选择日期"
                      :model-value="affectedDateParts.date"
                      @update:model-value="
                        onAffectedDatePartChange('date', $event)
                      "
                    />
                    <div class="affected-time-pair">
                      <span class="affected-time-label">从</span>
                      <DateTimeField
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
                      <DateTimeField
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
                    <DateTimeField
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
                    <input
                      :value="item.event"
                      placeholder="发生了什么"
                      @input="onFullTimelineText(index, 'event', $event)"
                    />
                    <input
                      :value="item.resolution"
                      placeholder="如何处理"
                      @input="onFullTimelineText(index, 'resolution', $event)"
                    />
                    <input
                      :value="item.evidence"
                      placeholder="证据"
                      @input="onFullTimelineText(index, 'evidence', $event)"
                    />
                    <div class="timeline-inline-actions">
                      <button
                        type="button"
                        class="incident-secondary-btn"
                        @click="emitGenerateSection('timeline_item', index)"
                      >
                        生成
                      </button>
                      <button
                        v-if="sectionTraceMap[`timeline_item_${index}`]"
                        type="button"
                        class="incident-secondary-btn"
                        @click="
                          $emit(
                            'open-trace',
                            sectionTraceMap[`timeline_item_${index}`],
                          )
                        "
                      >
                        链路
                      </button>
                      <button
                        type="button"
                        class="danger-mini-btn"
                        @click="removeFullTimelineItem(index)"
                      >
                        删除
                      </button>
                    </div>
                  </div>
                </div>
                <button
                  type="button"
                  class="incident-secondary-btn"
                  @click="addFullTimelineItem"
                >
                  新增时间线
                </button>
                <p
                  v-if="missingFieldSet.has(BODY_TIMELINE)"
                  class="incident-error-text"
                >
                  时间线至少需要一条。
                </p>
              </div>

              <div class="section-card" :data-field="BODY_IMPACT_SCOPE">
                <div class="section-header">
                  <h4>影响范围 / 严重级别（Impact / Severity）*</h4>
                  <div class="section-actions">
                    <button
                      type="button"
                      class="incident-secondary-btn"
                      @click="emitGenerateSection('impact')"
                    >
                      生成
                    </button>
                    <button
                      v-if="sectionTraceMap.impact"
                      type="button"
                      class="incident-secondary-btn"
                      @click="$emit('open-trace', sectionTraceMap.impact)"
                    >
                      链路
                    </button>
                  </div>
                </div>
                <label class="field-item">
                  <span>影响范围（Impact Scope）*</span>
                  <input
                    :class="{ invalid: missingFieldSet.has(BODY_IMPACT_SCOPE) }"
                    :value="getTextAnswer(BODY_IMPACT_SCOPE)"
                    @input="onTextInput(BODY_IMPACT_SCOPE, $event)"
                  />
                </label>
                <label class="field-item" :data-field="BODY_IMPACT_SEVERITY">
                  <span>严重级别（Impact Severity）*</span>
                  <input
                    :class="{
                      invalid: missingFieldSet.has(BODY_IMPACT_SEVERITY),
                    }"
                    :value="getTextAnswer(BODY_IMPACT_SEVERITY)"
                    @input="onTextInput(BODY_IMPACT_SEVERITY, $event)"
                  />
                </label>
                <label class="field-item full-width">
                  <span>业务影响（Business Impact）</span>
                  <textarea
                    rows="2"
                    :value="getTextAnswer(BODY_BUSINESS_IMPACT)"
                    @input="onTextInput(BODY_BUSINESS_IMPACT, $event)"
                  ></textarea>
                </label>
              </div>

              <div class="section-card" :data-field="BODY_ROOT_CAUSE">
                <div class="section-header">
                  <h4>根因分析（Root Cause）*</h4>
                  <div class="section-actions">
                    <button
                      type="button"
                      class="incident-secondary-btn"
                      @click="emitGenerateSection('root_cause')"
                    >
                      生成
                    </button>
                    <button
                      v-if="sectionTraceMap.root_cause"
                      type="button"
                      class="incident-secondary-btn"
                      @click="$emit('open-trace', sectionTraceMap.root_cause)"
                    >
                      链路
                    </button>
                  </div>
                </div>
                <label class="field-item">
                  <span>触发原因（Trigger）</span>
                  <input
                    :value="getTextAnswer(BODY_TRIGGER)"
                    @input="onTextInput(BODY_TRIGGER, $event)"
                  />
                </label>
                <label class="field-item full-width">
                  <span>根因（Root Cause）*</span>
                  <textarea
                    rows="3"
                    :class="{ invalid: missingFieldSet.has(BODY_ROOT_CAUSE) }"
                    :value="getTextAnswer(BODY_ROOT_CAUSE)"
                    @input="onTextInput(BODY_ROOT_CAUSE, $event)"
                  ></textarea>
                </label>
              </div>

              <div class="section-card" :data-field="BODY_FOLLOW_UP">
                <div class="section-header">
                  <h4>后续动作（Follow-Up Actions）*</h4>
                  <div class="section-actions">
                    <button
                      type="button"
                      class="incident-secondary-btn"
                      @click="emitGenerateSection('follow_up')"
                    >
                      生成
                    </button>
                    <button
                      v-if="sectionTraceMap.follow_up"
                      type="button"
                      class="incident-secondary-btn"
                      @click="$emit('open-trace', sectionTraceMap.follow_up)"
                    >
                      链路
                    </button>
                  </div>
                </div>
                <textarea
                  rows="4"
                  :class="{ invalid: missingFieldSet.has(BODY_FOLLOW_UP) }"
                  :value="getTextAnswer(BODY_FOLLOW_UP)"
                  @input="onTextInput(BODY_FOLLOW_UP, $event)"
                ></textarea>
              </div>
            </div>
          </section>

          <section class="incident-zone-card">
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
                    <button
                      type="button"
                      class="incident-secondary-btn"
                      @click="formatAppendixCommand('bold')"
                    >
                      加粗
                    </button>
                    <button
                      type="button"
                      class="incident-secondary-btn"
                      @click="formatAppendixCommand('insertUnorderedList')"
                    >
                      列表
                    </button>
                    <button
                      type="button"
                      class="incident-secondary-btn"
                      @click="triggerAppendixImagePicker"
                    >
                      插入图片
                    </button>
                    <button
                      type="button"
                      class="incident-secondary-btn"
                      @click="clearAppendixContent"
                    >
                      清空
                    </button>
                    <input
                      ref="appendixImageInputRef"
                      class="appendix-hidden-input"
                      type="file"
                      accept="image/*"
                      multiple
                      @change="onAppendixRichImagesSelected"
                    />
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

        <section class="incident-preview-zone">
          <header class="zone-header">
            <h3>预览附件</h3>
            <p>表单内容编辑后会自动同步到预览，下载内容与预览保持一致。</p>
          </header>
          <div class="action-row">
            <button
              type="button"
              class="incident-secondary-btn"
              @click="openPreviewDialog"
            >
              预览附件
            </button>
          </div>
          <p v-if="previewValidationError" class="incident-error-text">
            {{ previewValidationError }}
          </p>
        </section>
      </section>
    </Transition>

    <Teleport to="body">
      <Transition name="dialog-fade">
        <div v-if="previewVisible" class="incident-modal-mask">
          <div class="incident-modal preview-modal">
            <div class="preview-header">
              <h3>附件预览</h3>
              <button
                type="button"
                class="incident-secondary-btn"
                @click="closePreviewDialog"
              >
                关闭
              </button>
            </div>
            <div class="preview-body word-preview-body">
              <p v-if="previewLoading" class="preview-placeholder">
                正在生成预览，请稍候...
              </p>
              <p v-else-if="previewError" class="incident-error-text">
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
              <button
                type="button"
                class="incident-secondary-btn"
                :disabled="!canDownloadPreviewDocx"
                @click="onDownloadPreviewDocx"
              >
                下载当前预览文档
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <Teleport to="body">
      <Transition name="dialog-fade">
        <div v-if="showGenerationModal" class="incident-modal-mask">
          <div class="incident-modal quick-generation-modal">
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
              <button
                type="button"
                class="danger-mini-btn"
                @click="$emit('stop-generation')"
              >
                停止
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from 'vue';
import DateTimeField from './DateTimeField.vue';
import type {
  IncidentFormAnswer,
  IncidentFormSchemaPayload,
  IncidentSessionDetail,
} from '../types/incident-report';

interface TimelineItem {
  time: string;
  event: string;
  resolution: string;
  evidence: string;
}

interface AppendixImageItem {
  name: string;
  data_url: string;
}

interface AffectedDateParts {
  date: string;
  from: string;
  to: string;
}

const MANUAL_REFERENCE_NO = 'manual_reference_no';
const MANUAL_FAULT_DATE = 'manual_fault_date';
const MANUAL_FAULT_TIME = 'manual_fault_time';
const MANUAL_REPORTING_PERSON = 'manual_reporting_person';
const MANUAL_VERIFIED_BY = 'manual_verified_by';
const MANUAL_SITE_ID = 'manual_site_id';
const MANUAL_SYSTEM = 'manual_system';
const MANUAL_LOCATION = 'manual_location';
const MANUAL_FAULT_SYMPTOM = 'manual_fault_symptom';
const MANUAL_ARRIVAL_DATETIME = 'manual_arrival_datetime';
const MANUAL_CLEARANCE_DATETIME = 'manual_clearance_datetime';
const MANUAL_SERVICE_PERSON = 'manual_service_person';
const MANUAL_FAULT_CAUSE = 'manual_fault_cause';
const MANUAL_MATERIALS_USED = 'manual_materials_used';
const MANUAL_REPAIR_DETAILS = 'manual_repair_details';
const MANUAL_CONTRACTOR_STAFF = 'manual_contractor_staff';
const MANUAL_CONTRACTOR_SIGNATURE = 'manual_contractor_signature';
const MANUAL_CONTRACTOR_DATE = 'manual_contractor_date';
const MANUAL_STATUS = 'manual_status';
const MANUAL_STATUS_REF_NO = 'manual_status_ref_no';
const MANUAL_SEVERITY = 'manual_severity';
const MANUAL_COMMENTS = 'manual_comments';
const MANUAL_EMPLOYER_REP = 'manual_employer_rep';
const MANUAL_EMPLOYER_SIGNATURE = 'manual_employer_signature';
const MANUAL_CLOSEOUT_DATE = 'manual_closeout_date';

const STATUS_OPTION_FAULT_CLEARED = 'fault_cleared';
const STATUS_OPTION_TEMPORARILY_FIXED = 'temporarily_fixed';
const STATUS_OPTION_FOLLOW_UP_ACTION_REQUIRED = 'follow_up_action_required';

const SEVERITY_OPTION_NOT_APPLICABLE = 'not_applicable';
const SEVERITY_OPTION_MINOR = 'minor';
const SEVERITY_OPTION_MAJOR = 'major';

const statusOptions = [
  {
    value: STATUS_OPTION_FAULT_CLEARED,
    label: '已清除（Fault has been Cleared）',
  },
  {
    value: STATUS_OPTION_TEMPORARILY_FIXED,
    label: '临时修复（Temporarily Fixed）',
  },
  {
    value: STATUS_OPTION_FOLLOW_UP_ACTION_REQUIRED,
    label: '需要后续动作（Follow up action required）',
  },
] as const;

const severityOptions = [
  {
    value: SEVERITY_OPTION_NOT_APPLICABLE,
    label: '不适用（Not Applicable）',
  },
  {
    value: SEVERITY_OPTION_MINOR,
    label: '轻微（Minor）',
  },
  {
    value: SEVERITY_OPTION_MAJOR,
    label: '重大（Major）',
  },
] as const;

const QUICK_NARRATIVE = 'quick_narrative';

const BODY_DESCRIPTION = 'body_description';
const BODY_AFFECTED_DATE = 'body_affected_date_summary';
const BODY_TIMELINE = 'body_timeline';
const BODY_IMPACT_SCOPE = 'body_impact_scope';
const BODY_IMPACT_SEVERITY = 'body_impact_severity';
const BODY_BUSINESS_IMPACT = 'body_business_impact';
const BODY_TRIGGER = 'body_trigger';
const BODY_ROOT_CAUSE = 'body_root_cause';
const BODY_FOLLOW_UP = 'body_follow_up_actions';
const PREVIEW_REQUIRED_FIELDS = [
  MANUAL_FAULT_DATE,
  MANUAL_FAULT_TIME,
  MANUAL_REPORTING_PERSON,
  MANUAL_SITE_ID,
  MANUAL_SYSTEM,
  MANUAL_LOCATION,
  MANUAL_FAULT_SYMPTOM,
  BODY_DESCRIPTION,
  BODY_IMPACT_SCOPE,
  BODY_IMPACT_SEVERITY,
  BODY_ROOT_CAUSE,
  BODY_FOLLOW_UP,
] as const;

const APPENDIX_NOTES = 'appendix_notes';
const APPENDIX_IMAGES = 'appendix_images';

const props = withDefaults(
  defineProps<{
    schema: IncidentFormSchemaPayload | null;
    session: IncidentSessionDetail | null;
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
  (e: 'update-answers', answers: Record<string, IncidentFormAnswer>): void;
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

const localAnswers = ref<Record<string, IncidentFormAnswer>>({});
const bodyMode = ref<'quick' | 'full'>('quick');
const previewVisible = ref(false);
const appendixEditorRef = ref<HTMLDivElement | null>(null);
const appendixImageInputRef = ref<HTMLInputElement | null>(null);
const statusDropdownRef = ref<HTMLDivElement | null>(null);
const severityDropdownRef = ref<HTMLDivElement | null>(null);
const statusDropdownOpen = ref(false);
const severityDropdownOpen = ref(false);
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
const DOCX_SAFE_IMAGE_MIME_TYPES = new Set([
  'image/png',
  'image/jpeg',
  'image/jpg',
  'image/gif',
  'image/bmp',
]);

const normalizeTimeOnly = (value: string) => {
  const normalized = value.trim();
  if (!normalized) {
    return '';
  }

  const applyAmpm = (rawHour: number, rawAmpm: string) => {
    let hour = rawHour;
    const ampm = rawAmpm.toLowerCase();
    if (ampm === 'pm' && hour >= 1 && hour <= 11) {
      hour += 12;
    } else if (ampm === 'am' && hour === 12) {
      hour = 0;
    }
    return hour;
  };

  const timePattern =
    /(?:^|[^\d])(?<hour>\d{1,2})\s*(?:[:：时hH点])\s*(?<minute>\d{1,2})(?:\s*(?:分|m|M))?\s*(?<ampm>am|pm)?/i;
  const matched = normalized.match(timePattern);
  if (matched?.groups) {
    let hour = Number(matched.groups.hour);
    const minute = Number(matched.groups.minute);
    hour = applyAmpm(hour, matched.groups.ampm ?? '');

    if (
      Number.isNaN(hour) ||
      Number.isNaN(minute) ||
      minute < 0 ||
      minute > 59 ||
      hour < 0 ||
      hour > 23
    ) {
      return '';
    }
    return `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
  }

  const halfPattern =
    /(?:^|[^\d])(?<hour>\d{1,2})\s*(?:点|时|h|H)\s*半\s*(?<ampm>am|pm)?/i;
  const halfMatched = normalized.match(halfPattern);
  if (halfMatched?.groups) {
    const hour = applyAmpm(
      Number(halfMatched.groups.hour),
      halfMatched.groups.ampm ?? '',
    );
    if (Number.isNaN(hour) || hour < 0 || hour > 23) {
      return '';
    }
    return `${String(hour).padStart(2, '0')}:30`;
  }

  const hourOnlyPattern =
    /(?:^|[^\d])(?<hour>\d{1,2})\s*(?:点|时|h|H)\s*(?<ampm>am|pm)?/i;
  const hourOnlyMatched = normalized.match(hourOnlyPattern);
  if (!hourOnlyMatched?.groups) {
    return '';
  }
  const hour = applyAmpm(
    Number(hourOnlyMatched.groups.hour),
    hourOnlyMatched.groups.ampm ?? '',
  );
  if (Number.isNaN(hour) || hour < 0 || hour > 23) {
    return '';
  }
  return `${String(hour).padStart(2, '0')}:00`;
};

const parseDateToken = (value: string) => {
  const normalized = value.trim();
  const isoMatched = normalized.match(/(\d{4})-(\d{1,2})-(\d{1,2})/);
  if (isoMatched) {
    const month = String(Number(isoMatched[2])).padStart(2, '0');
    const day = String(Number(isoMatched[3])).padStart(2, '0');
    return `${isoMatched[1]}-${month}-${day}`;
  }
  const slashMatched = normalized.match(/(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})/);
  if (slashMatched) {
    const day = String(Number(slashMatched[1])).padStart(2, '0');
    const month = String(Number(slashMatched[2])).padStart(2, '0');
    return `${slashMatched[3]}-${month}-${day}`;
  }
  return '';
};

const toDisplayDate = (isoDate: string) => {
  const matched = isoDate.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!matched) {
    return '';
  }
  return `${matched[3]}/${matched[2]}/${matched[1]}`;
};

const parseAffectedDateSummary = (value: string): AffectedDateParts => {
  const normalized = value.trim();
  if (!normalized) {
    return { date: '', from: '', to: '' };
  }

  const rangeParts = normalized.split(/\s*[-—–]\s*/);
  const times = Array.from(
    normalized.matchAll(
      /(?:^|[^\d])(\d{1,2}\s*(?:[:：]\s*\d{1,2}(?:\s*(?:分|m|M))?|(?:点|时|h|H)\s*(?:\d{1,2}\s*(?:分)?|半)?)(?:\s*(?:am|pm))?)/gi,
    ),
  )
    .map((match) => normalizeTimeOnly(match[1] ?? match[0]))
    .filter((item) => item.length > 0);

  if (rangeParts.length >= 2 || times.length >= 2) {
    const left = rangeParts[0] ?? normalized;
    const right = rangeParts[1] ?? normalized;
    const from = times[0] || normalizeTimeOnly(left);
    const to = times[1] || normalizeTimeOnly(right);
    return {
      date: parseDateToken(normalized),
      from,
      to,
    };
  }

  return {
    date: parseDateToken(normalized),
    from: times[0] || normalizeTimeOnly(normalized),
    to: '',
  };
};

const composeAffectedDateSummary = (parts: AffectedDateParts) => {
  const displayDate = parts.date ? toDisplayDate(parts.date) : '';
  if (!displayDate && !parts.from && !parts.to) {
    return '';
  }
  if (displayDate && parts.from && parts.to) {
    return `${displayDate} ${parts.from} - ${displayDate} ${parts.to}`;
  }
  if (displayDate && parts.from) {
    return `${displayDate} ${parts.from}`;
  }
  if (displayDate) {
    return displayDate;
  }
  if (parts.from && parts.to) {
    return `${parts.from} - ${parts.to}`;
  }
  return parts.from || parts.to;
};

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

const normalizeStatusOption = (value: string) => {
  const normalized = value.trim().toLowerCase();
  if (!normalized) {
    return STATUS_OPTION_FAULT_CLEARED;
  }
  if (
    normalized === STATUS_OPTION_FAULT_CLEARED ||
    normalized === STATUS_OPTION_TEMPORARILY_FIXED ||
    normalized === STATUS_OPTION_FOLLOW_UP_ACTION_REQUIRED
  ) {
    return normalized;
  }
  if (
    normalized.includes('follow') ||
    normalized.includes('后续') ||
    normalized.includes('跟进')
  ) {
    return STATUS_OPTION_FOLLOW_UP_ACTION_REQUIRED;
  }
  if (normalized.includes('temporar') || normalized.includes('临时')) {
    return STATUS_OPTION_TEMPORARILY_FIXED;
  }
  if (
    normalized.includes('clear') ||
    normalized.includes('cleared') ||
    normalized.includes('已清除')
  ) {
    return STATUS_OPTION_FAULT_CLEARED;
  }
  return STATUS_OPTION_FAULT_CLEARED;
};

const normalizeSeverityOption = (value: string) => {
  const normalized = value.trim().toLowerCase();
  if (!normalized) {
    return SEVERITY_OPTION_NOT_APPLICABLE;
  }
  if (
    normalized === SEVERITY_OPTION_NOT_APPLICABLE ||
    normalized === SEVERITY_OPTION_MINOR ||
    normalized === SEVERITY_OPTION_MAJOR
  ) {
    return normalized;
  }
  if (
    normalized.includes('major') ||
    normalized.includes('high') ||
    normalized.includes('critical') ||
    normalized.includes('严重') ||
    normalized.includes('重大')
  ) {
    return SEVERITY_OPTION_MAJOR;
  }
  if (
    normalized.includes('minor') ||
    normalized.includes('low') ||
    normalized.includes('轻微')
  ) {
    return SEVERITY_OPTION_MINOR;
  }
  return SEVERITY_OPTION_NOT_APPLICABLE;
};

const ensureAnswer = (fieldId: string) => {
  if (!localAnswers.value[fieldId]) {
    localAnswers.value[fieldId] = {
      value: '',
      custom_value: '',
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

const closeManualDropdowns = () => {
  statusDropdownOpen.value = false;
  severityDropdownOpen.value = false;
};

const selectStatusOption = (value: string) => {
  const nextValue = normalizeStatusOption(value);
  setAnswerValue(MANUAL_STATUS, nextValue);
  if (nextValue !== STATUS_OPTION_FOLLOW_UP_ACTION_REQUIRED) {
    setAnswerValue(MANUAL_STATUS_REF_NO, '');
  }
  statusDropdownOpen.value = false;
};

const selectSeverityOption = (value: string) => {
  setAnswerValue(MANUAL_SEVERITY, normalizeSeverityOption(value));
  severityDropdownOpen.value = false;
};

const toggleStatusDropdown = () => {
  statusDropdownOpen.value = !statusDropdownOpen.value;
  if (statusDropdownOpen.value) {
    severityDropdownOpen.value = false;
  }
};

const toggleSeverityDropdown = () => {
  severityDropdownOpen.value = !severityDropdownOpen.value;
  if (severityDropdownOpen.value) {
    statusDropdownOpen.value = false;
  }
};

const onManualDropdownPointerDown = (event: PointerEvent) => {
  const target = event.target as Node | null;
  if (!target) {
    return;
  }

  if (
    statusDropdownOpen.value &&
    statusDropdownRef.value &&
    !statusDropdownRef.value.contains(target)
  ) {
    statusDropdownOpen.value = false;
  }

  if (
    severityDropdownOpen.value &&
    severityDropdownRef.value &&
    !severityDropdownRef.value.contains(target)
  ) {
    severityDropdownOpen.value = false;
  }
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
        typeof candidate.data_url === 'string' &&
        candidate.name.length > 0 &&
        candidate.data_url.length > 0
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
        `<p><img src="${image.data_url}" alt="${escapeHtml(image.name)}" /></p>`,
    )
    .join('');
  setAnswerValue(APPENDIX_NOTES, `${baseHtml}${imageHtml}`);
  setAnswerValue(APPENDIX_IMAGES, []);
};

watch(
  () => props.session?.snapshot.form_answers,
  async (nextAnswers) => {
    syncingAnswersFromSession = true;
    try {
      missingFieldIds.value = [];
      previewValidationError.value = '';
      localAnswers.value = JSON.parse(
        JSON.stringify(nextAnswers ?? {}),
      ) as Record<string, IncidentFormAnswer>;
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
    closeManualDropdowns();
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
  return (props.session?.snapshot.section_trace_ids ?? {}) as Record<
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
const selectedStatusLabel = computed(
  () =>
    statusOptions.find((option) => option.value === selectedStatusOption.value)
      ?.label ?? statusOptions[0].label,
);

const selectedSeverityOption = computed(() =>
  normalizeSeverityOption(getTextAnswer(MANUAL_SEVERITY)),
);
const selectedSeverityLabel = computed(
  () =>
    severityOptions.find(
      (option) => option.value === selectedSeverityOption.value,
    )?.label ?? severityOptions[0].label,
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

const triggerAppendixImagePicker = () => {
  appendixImageInputRef.value?.click();
};

const onAppendixRichImagesSelected = async (event: Event) => {
  const files = (event.target as HTMLInputElement).files;
  if (!files || files.length === 0 || !appendixEditorRef.value) {
    return;
  }
  let currentHtml = appendixEditorRef.value.innerHTML;
  for (const file of Array.from(files)) {
    const dataUrl = await convertImageFileToDocxDataUrl(file);
    currentHtml += `<p><img src="${dataUrl}" alt="${escapeHtml(file.name)}" /></p>`;
  }
  appendixEditorRef.value.innerHTML = currentHtml;
  onAppendixRichInput();
  (event.target as HTMLInputElement).value = '';
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

onMounted(() => {
  document.addEventListener('pointerdown', onManualDropdownPointerDown, true);
});

onBeforeUnmount(() => {
  document.removeEventListener(
    'pointerdown',
    onManualDropdownPointerDown,
    true,
  );
  closeManualDropdowns();
  emit('cancel-preview');
  if (previewRefreshTimer !== null) {
    window.clearTimeout(previewRefreshTimer);
    previewRefreshTimer = null;
  }
});
</script>

<style scoped src="../styles/components/incident-report-workspace.css"></style>
