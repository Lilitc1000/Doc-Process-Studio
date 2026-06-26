"""应用层端口接口。

定义应用服务依赖的外部能力抽象，由 infrastructure 层实现。
应用层只依赖这些接口，不依赖具体 ORM/数据库实现和跨域服务。
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from ...domain.entities.report import Report
from ...domain.events import ReportEvent
from ...domain.values.permission import Permission
from ..dtos import IncidentAuditLogEntry, IncidentCommentEntry, IncidentReportSummary


class ReportRepository(ABC):
    """报告仓储端口。"""

    @abstractmethod
    async def add(self, report: Report) -> Report:
        """新建报告（INSERT），包含 ref_no 生成与冲突重试。"""

    @abstractmethod
    async def get(self, report_id: str) -> Report | None:
        """按 ID 加载报告聚合根。"""

    @abstractmethod
    async def update(self, report: Report) -> Report | None:
        """更新已存在的报告（UPDATE），返回更新后的聚合根。"""

    @abstractmethod
    async def list(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        severity: str | None = None,
        search: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        reporter_id_filter: str | None = None,
    ) -> tuple[list[IncidentReportSummary], int]:
        """分页查询报告列表，返回摘要列表 + 总数。"""

    @abstractmethod
    async def delete(self, report_id: str) -> bool:
        """删除报告（级联删除评论和审计日志）。"""

    @abstractmethod
    async def update_form_data(
        self,
        report_id: str,
        form_data: dict[str, Any],
        report_data: dict[str, Any] | None = None,
    ) -> Report | None:
        """更新报告的 form_data 和 report_data，返回更新后的聚合根。"""


class PermissionChecker(ABC):
    """权限检查端口。"""

    @abstractmethod
    async def permissions_of(self, user_id: str) -> set[Permission]:
        """返回用户拥有的全部权限集合。"""

    async def require(self, user_id: str, permission: Permission) -> None:
        """校验用户是否拥有指定权限，不足则抛 PermissionDeniedError。"""
        from ...domain.values.errors import PermissionDeniedError

        if permission not in await self.permissions_of(user_id):
            raise PermissionDeniedError(f"需要权限: {permission.value}")


class AuditEventSink(ABC):
    """审计事件落库端口。"""

    @abstractmethod
    async def flush(self, events: list[ReportEvent]) -> None:
        """将领域事件批量写入审计日志表。"""


class AuditLogRepository(ABC):
    """审计日志查询端口。"""

    @abstractmethod
    async def list_by_report(self, report_id: str) -> list[IncidentAuditLogEntry]:
        """按报告 ID 查询审计日志列表（按创建时间升序），返回 DTO。"""


class CommentRepository(ABC):
    """评论仓储端口。"""

    @abstractmethod
    async def add(
        self,
        *,
        comment_id: str,
        report_id: str,
        author_id: str,
        content: str,
        parent_id: str | None = None,
    ) -> IncidentCommentEntry:
        """新增评论记录，返回 DTO。"""

    @abstractmethod
    async def list_by_report(self, report_id: str) -> list[IncidentCommentEntry]:
        """按报告 ID 查询评论列表（按创建时间升序），返回 DTO。"""


class UserDirectory(ABC):
    """用户目录端口（用户名解析）。"""

    @abstractmethod
    async def resolve_usernames(self, user_ids: set[str]) -> dict[str, str]:
        """解析用户 ID → 用户名映射，失败时返回空映射（不抛异常）。"""


class RefNoGenerator(ABC):
    """报告编号生成端口。"""

    @abstractmethod
    async def next(self) -> str:
        """生成下一个报告编号。"""


# ---- 跨域服务端口 ----


class LLMStreamingPort(ABC):
    """LLM 流式聊天补全端口。"""

    @abstractmethod
    async def stream_chat(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
    ) -> tuple[str, str]:
        """流式调用 LLM，返回 (完整响应文本, done_reason)。"""


class TraceRecorderPort(ABC):
    """追踪记录器端口。"""

    @abstractmethod
    def create_recorder(
        self,
        *,
        trace_id: str,
        tenant_id: str,
        conversation_id: str,
        user_message_id: str,
        model: str,
        reranker_model: str,
    ) -> Any:
        """创建追踪记录器实例。"""

    @abstractmethod
    async def add_event(self, recorder: Any, event_type: str, detail: dict[str, Any]) -> None:
        """向记录器添加事件。"""

    @abstractmethod
    async def set_final(self, recorder: Any, *, done_reason: str, error: str | None) -> None:
        """设置记录器最终状态。"""

    @abstractmethod
    async def flush_recorder(self, recorder: Any) -> None:
        """将记录器内容刷写到持久化存储。"""


class ReferenceContextPort(ABC):
    """参考文档上下文选择端口。"""

    @abstractmethod
    async def resolve(
        self,
        *,
        model: str,
        section_id: str,
        timeline_index: int | None,
        prompt: str,
        context_json: str,
    ) -> tuple[str, list[str], str]:
        """选择参考文档上下文，返回 (context_text, selected_files, selection_reason)。"""


class DocumentAssistantPort(ABC):
    """文档助手端口。"""

    @abstractmethod
    def get_default_prompt(self) -> str:
        """获取文档助手的默认提示词。"""


class AttachmentStore(ABC):
    """附件存储端口。"""

    @abstractmethod
    async def save_generated(
        self,
        *,
        source_path: Any,
        conversation_id: str,
        skill_id: str,
        output_name: str,
        mime_type: str,
    ) -> Any:
        """保存生成的附件，返回附件元数据。"""

    @abstractmethod
    async def resolve_path(self, attachment_id: str) -> tuple[Any, Any | None, bool]:
        """解析附件路径，返回 (metadata, path, is_expired)。"""
