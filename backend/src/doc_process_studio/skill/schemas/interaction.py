from typing import Any, Literal

from pydantic import BaseModel, Field


class SkillInteractionOption(BaseModel):
    value: str = Field(..., description="选项值")
    label: str = Field(..., description="选项展示名称")
    description: str | None = Field(default=None, description="选项补充说明")


class SkillInteractionStep(BaseModel):
    id: str = Field(..., description="步骤标识")
    title: str = Field(..., description="步骤标题")
    prompt: str = Field(..., description="当前步骤问题描述")
    field_path: str = Field(..., description="写入 collected 的字段路径，支持 a.b.c")
    kind: Literal["single_select", "multi_select", "text"] = Field(
        default="single_select",
        description="步骤交互类型",
    )
    options: list[SkillInteractionOption] = Field(
        default_factory=list,
        description="可选项列表，single/multi 模式下生效",
    )
    allow_custom: bool = Field(default=False, description="是否允许用户输入自定义值")
    required: bool = Field(default=True, description="是否必填")
    placeholder: str | None = Field(default=None, description="文本输入占位提示")


class SkillInteractionFinalToolConfig(BaseModel):
    name: str = Field(..., description="完成交互后调用的声明式工具名称")
    argument_name: str = Field(default="report_data", description="写入工具入参的字段名")
    output_name_template: str | None = Field(
        default=None,
        description="可选输出文件名模板，例如 incident-{reference_no}.docx",
    )
    static_arguments: dict[str, Any] = Field(
        default_factory=dict,
        description="完成时固定注入的额外工具参数",
    )


class SkillInteractionConfig(BaseModel):
    enabled: bool = Field(default=False, description="是否启用交互式步骤采集")
    intro_message: str | None = Field(default=None, description="交互开始时展示的提示文案")
    completion_message: str | None = Field(default=None, description="交互完成后的提示文案")
    defaults: dict[str, Any] = Field(default_factory=dict, description="最终结果默认值")
    steps: list[SkillInteractionStep] = Field(default_factory=list, description="步骤列表")
    final_tool: SkillInteractionFinalToolConfig | None = Field(
        default=None,
        description="步骤完成后的工具调用配置",
    )
