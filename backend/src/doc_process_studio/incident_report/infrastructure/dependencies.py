"""基础设施依赖装配。

为 FastAPI Depends 提供应用服务实例，组装端口与实现。
"""

from functools import lru_cache

from ..application.analytics_service import AnalyticsService
from ..application.audit_query_service import AuditQueryService
from ..application.comment_service import CommentService
from ..application.generation_service import GenerationService
from ..application.preview_service import PreviewService
from ..application.report_service import ReportApplicationService
from ..application.role_service import RoleService
from .analytics_repository import SqlAnalyticsRepository
from .audit_event_sink import SqlAuditEventSink
from .audit_log_repository import SqlAuditLogRepository
from .comment_repository import SqlCommentRepository
from .permission_checker import RbacPermissionChecker
from .report_repository import (
    SequentialRefNoGenerator,
    SqlAlchemyReportRepository,
    SqlUserDirectory,
)
from .role_repository import SqlRoleRepository


@lru_cache(maxsize=1)
def get_user_directory() -> SqlUserDirectory:
    return SqlUserDirectory()


@lru_cache(maxsize=1)
def get_ref_no_generator() -> SequentialRefNoGenerator:
    return SequentialRefNoGenerator()


@lru_cache(maxsize=1)
def get_report_repository() -> SqlAlchemyReportRepository:
    return SqlAlchemyReportRepository(
        user_dir=get_user_directory(),
        ref_no_gen=get_ref_no_generator(),
    )


@lru_cache(maxsize=1)
def get_permission_checker() -> RbacPermissionChecker:
    return RbacPermissionChecker()


@lru_cache(maxsize=1)
def get_audit_event_sink() -> SqlAuditEventSink:
    return SqlAuditEventSink()


@lru_cache(maxsize=1)
def get_audit_log_repository() -> SqlAuditLogRepository:
    return SqlAuditLogRepository()


@lru_cache(maxsize=1)
def get_comment_repository() -> SqlCommentRepository:
    return SqlCommentRepository()


@lru_cache(maxsize=1)
def get_analytics_repository() -> SqlAnalyticsRepository:
    return SqlAnalyticsRepository()


@lru_cache(maxsize=1)
def get_role_repository() -> SqlRoleRepository:
    return SqlRoleRepository()


@lru_cache(maxsize=1)
def get_report_application_service() -> ReportApplicationService:
    """装配报告应用服务（单例）。"""
    return ReportApplicationService(
        repo=get_report_repository(),
        checker=get_permission_checker(),
        audit_sink=get_audit_event_sink(),
        user_dir=get_user_directory(),
        ref_no_gen=get_ref_no_generator(),
    )


@lru_cache(maxsize=1)
def get_audit_query_service() -> AuditQueryService:
    """装配审计日志查询服务（单例）。"""
    return AuditQueryService(
        report_repo=get_report_repository(),
        audit_repo=get_audit_log_repository(),
        checker=get_permission_checker(),
        user_dir=get_user_directory(),
    )


@lru_cache(maxsize=1)
def get_comment_service() -> CommentService:
    """装配评论服务（单例）。"""
    return CommentService(
        report_repo=get_report_repository(),
        comment_repo=get_comment_repository(),
        checker=get_permission_checker(),
        user_dir=get_user_directory(),
    )


@lru_cache(maxsize=1)
def get_analytics_service() -> AnalyticsService:
    """装配统计分析服务（单例）。"""
    return AnalyticsService(
        repo=get_analytics_repository(),
        checker=get_permission_checker(),
    )


@lru_cache(maxsize=1)
def get_role_service() -> RoleService:
    """装配角色管理服务（单例）。"""
    return RoleService(
        role_repo=get_role_repository(),
        checker=get_permission_checker(),
        user_dir=get_user_directory(),
    )


@lru_cache(maxsize=1)
def get_generation_service() -> GenerationService:
    """装配报告生成服务（单例）。"""
    return GenerationService()


@lru_cache(maxsize=1)
def get_preview_service() -> PreviewService:
    """装配报告预览服务（单例）。"""
    return PreviewService()
