from pydantic import BaseModel, Field


class FormFieldSchema(BaseModel):
    field_id: str = Field(..., description="字段ID")
    label: str = Field(..., description="字段标签")
    field_type: str = Field(
        ..., description="字段类型: text/textarea/select/date/datetime/rich_text/timeline/attachment"
    )
    required: bool = Field(default=False, description="是否必填")
    placeholder: str | None = Field(default=None, description="占位文本")
    options: list[dict[str, str]] | None = Field(default=None, description="选项列表(select类型)")
    section: str = Field(default="default", description="所属区块")


class FormStepSchema(BaseModel):
    step_id: str = Field(..., description="步骤ID")
    title: str = Field(..., description="步骤标题")
    description: str | None = Field(default=None, description="步骤描述")
    fields: list[FormFieldSchema] = Field(default_factory=list, description="步骤字段列表")


class FormSchemaDefinition(BaseModel):
    version: int = Field(default=1, description="Schema版本")
    steps: list[FormStepSchema] = Field(default_factory=list, description="表单步骤列表")


INCIDENT_REPORT_FORM_SCHEMA = FormSchemaDefinition(
    version=1,
    steps=[
        FormStepSchema(
            step_id="basic_info",
            title="基本信息",
            description="填写事故的基本信息",
            fields=[
                FormFieldSchema(
                    field_id="manual_reference_no",
                    label="参考编号",
                    field_type="text",
                    placeholder="如：DAS-001，留空自动生成",
                ),
                FormFieldSchema(field_id="manual_fault_date", label="故障日期", field_type="datetime", required=True),
                FormFieldSchema(field_id="manual_reporting_person", label="报告人", field_type="text", required=True),
                FormFieldSchema(
                    field_id="manual_site_id",
                    label="站点编号",
                    field_type="text",
                    required=True,
                    placeholder="如：SITE-01",
                ),
                FormFieldSchema(
                    field_id="manual_system",
                    label="系统",
                    field_type="text",
                    required=True,
                    placeholder="如：数据库系统",
                ),
                FormFieldSchema(field_id="manual_location", label="位置", field_type="text", placeholder="如：机房A"),
                FormFieldSchema(
                    field_id="manual_fault_symptom", label="故障现象", field_type="textarea", required=True
                ),
                FormFieldSchema(
                    field_id="manual_status",
                    label="状态",
                    field_type="select",
                    options=[
                        {"value": "open", "label": "开放"},
                        {"value": "investigating", "label": "调查中"},
                        {"value": "resolved", "label": "已解决"},
                    ],
                ),
                FormFieldSchema(
                    field_id="manual_severity",
                    label="严重级别",
                    field_type="select",
                    options=[
                        {"value": "P0", "label": "P0 - 紧急"},
                        {"value": "P1", "label": "P1 - 严重"},
                        {"value": "P2", "label": "P2 - 一般"},
                        {"value": "P3", "label": "P3 - 轻微"},
                    ],
                ),
            ],
        ),
        FormStepSchema(
            step_id="description",
            title="事故描述",
            description="使用快填模式或分段模式描述事故",
            fields=[
                FormFieldSchema(
                    field_id="quick_narrative",
                    label="事故简述（快填）",
                    field_type="textarea",
                    placeholder="简要描述事故，AI将自动生成详细报告",
                ),
                FormFieldSchema(field_id="body_description", label="事故简述", field_type="rich_text"),
                FormFieldSchema(field_id="body_impact", label="影响范围", field_type="rich_text"),
                FormFieldSchema(field_id="body_root_cause", label="根因分析", field_type="rich_text"),
                FormFieldSchema(field_id="body_follow_up", label="后续动作", field_type="rich_text"),
            ],
        ),
        FormStepSchema(
            step_id="timeline",
            title="时间线",
            description="记录事故发生的关键时间节点",
            fields=[
                FormFieldSchema(field_id="body_timeline", label="时间线", field_type="timeline"),
            ],
        ),
        FormStepSchema(
            step_id="appendix",
            title="附录",
            description="附加信息和附件",
            fields=[
                FormFieldSchema(field_id="appendix_content", label="附录内容", field_type="rich_text"),
                FormFieldSchema(field_id="appendix_attachments", label="附件", field_type="attachment"),
            ],
        ),
    ],
)
