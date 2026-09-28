"""参考上下文装配测试。

验证 ``get_reference_context()`` 的**装配形状恒定**：永远返回 ``CompositeReferenceContext``，
与任何环境变量无关。

历史背景（别退回旧写法）：这里曾经有一道 ``settings.ragflow_enabled`` 的结构门禁 ——
``False`` 时返回 ``SkillReferenceContext``。它和库里的 ``ragflow.enabled`` 构成两套语义：
env 为 ``false`` 时管理员在设置页打开开关，知识库模块生效、报告侧检索却不生效。
现在统一到运行期解析，「是否真的用 RAGFlow」由 ``RagflowConfigProvider`` 决定；
RAGFLOW 配置已全面页面化、库内持久化，不再读任何环境变量。

关闭状态下的等价行为由 ``test_composite_reference.py::test_no_hits_keeps_base_with_reason``
覆盖（召回为空时输出与纯本地上下文一致，仅 reason 多一个 ``ragflow:no_hits`` 标记）。
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from doc_process_studio.incident_report.infrastructure.adapters.reference_context import (
    CompositeReferenceContext,
)
from doc_process_studio.incident_report.infrastructure.dependencies import get_reference_context


@pytest.fixture(autouse=True)
def _clear_wiring_cache() -> Iterator[None]:
    """装配函数带 @lru_cache，用例之间必须清，否则前一条会污染后面所有用例。"""
    get_reference_context.cache_clear()
    yield
    get_reference_context.cache_clear()


def test_wiring_shape_is_constant() -> None:
    """无论系统设置如何，装配出来的都是 Composite —— 它不再参与形状决策。"""
    assert isinstance(get_reference_context(), CompositeReferenceContext)


def test_wiring_does_not_pin_credentials() -> None:
    """没有任何 RAGFLOW 配置时也能装配出 Composite。

    说明凭据不是在装配期固化的，而是每次 ``retrieve()`` 向 provider 现取，
    "管理员改完立即生效"靠的是运行期解析而非重启。
    """
    assert isinstance(get_reference_context(), CompositeReferenceContext)
