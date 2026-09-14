"""参考上下文装配（开关）测试。

验证 dependencies.get_reference_context 在 ragflow_enabled 开关切换时返回正确的实现。
"""

from __future__ import annotations

import pytest

from doc_process_studio.common.infrastructure.config import settings
from doc_process_studio.incident_report.infrastructure.adapters.reference_context import (
    CompositeReferenceContext,
    SkillReferenceContext,
)
from doc_process_studio.incident_report.infrastructure.dependencies import get_reference_context


async def test_wiring_default_disabled_returns_skill_context(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ragflow_enabled", False)
    get_reference_context.cache_clear()
    ctx = get_reference_context()
    assert isinstance(ctx, SkillReferenceContext)
    get_reference_context.cache_clear()


async def test_wiring_enabled_returns_composite(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ragflow_enabled", True)
    monkeypatch.setattr(settings, "ragflow_base_url", "http://ragflow.test")
    monkeypatch.setattr(settings, "ragflow_api_key", "k")
    monkeypatch.setattr(settings, "ragflow_datasets_json", '{"history":["d1"]}')
    get_reference_context.cache_clear()
    ctx = get_reference_context()
    assert isinstance(ctx, CompositeReferenceContext)
    get_reference_context.cache_clear()
