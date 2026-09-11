"""内置写作标准（skill 资产）的单元测试。

这些文件是生成质量的载体：golden sample 定义"好报告"的颗粒度，
三个 body-section 文档把它翻译成模型可执行的标准。缺了就等于改动失效，
因此用测试把资产的存在性与结构锁住。
"""

from pathlib import Path

from doc_process_studio.incident_report.domain.values.constants import (
    INCIDENT_REPORT_REFERENCE_DIR,
)
from doc_process_studio.incident_report.infrastructure.adapters.reference_context import (
    _build_incident_reference_catalog,
    _select_references_by_heuristic,
)

BODY_SECTIONS_DIR = INCIDENT_REPORT_REFERENCE_DIR / "body-sections"
GOLDEN_SAMPLES_DIR = INCIDENT_REPORT_REFERENCE_DIR / "golden-samples"


def _read(path: Path) -> str:
    assert path.is_file(), f"missing reference file: {path}"
    return path.read_text(encoding="utf-8")


def test_golden_sample_exists() -> None:
    assert GOLDEN_SAMPLES_DIR.is_dir()
    text = _read(GOLDEN_SAMPLES_DIR / "CHT-20260312.md")
    # 好坏对照 + 写作规则 + 术语表 三部分缺一不可
    assert "✅" in text
    assert "❌" in text
    assert "写作规则" in text
    assert "术语" in text


def test_body_sections_have_good_bad_contrast() -> None:
    """三个文档都必须是：正向标准 + ✅好例子 + ❌坏例子 + 禁止表达清单。"""
    for name in ("impact.md", "root-cause.md", "follow-up.md"):
        text = _read(BODY_SECTIONS_DIR / name)
        assert "正向标准" in text, f"{name} 缺正向标准"
        assert "✅" in text, f"{name} 缺好例子"
        assert "❌" in text, f"{name} 缺坏例子"
        assert "禁止" in text, f"{name} 缺禁止表达清单"


def test_impact_doc_lists_banned_expressions() -> None:
    text = _read(BODY_SECTIONS_DIR / "impact.md").lower()
    for phrase in ("significantly", "to some extent", "degraded"):
        assert phrase in text, f"impact.md 缺禁止表达: {phrase}"


def test_root_cause_doc_lists_blackbox_labels() -> None:
    text = _read(BODY_SECTIONS_DIR / "root-cause.md").lower()
    for phrase in ("hardware issue", "unknown reason"):
        assert phrase in text, f"root-cause.md 缺黑箱标签: {phrase}"


def test_follow_up_doc_lists_banned_phrases() -> None:
    text = _read(BODY_SECTIONS_DIR / "follow-up.md").lower()
    for phrase in ("will follow up", "monitor the situation"):
        assert phrase in text, f"follow-up.md 缺套话: {phrase}"


def test_root_cause_doc_requires_minimum_chain_and_evidence_tiers() -> None:
    """回归：只写'缺证据就写 N/A'会让模型把链条压成一句话。"""
    text = _read(BODY_SECTIONS_DIR / "root-cause.md").lower()
    assert "至少 3 环" in text, "缺链条最少环数要求"
    assert "inferred" in text, "缺 inferred 分层标注"
    assert "confirmed" in text, "缺 confirmed 分层标注"
    assert "最后手段" in text, "未声明 N/A 是最后手段"
    assert "不足 3 环" in text, "禁止清单未覆盖链条过短"


def test_follow_up_doc_requires_both_action_types() -> None:
    """回归：整改清单被压到 2~3 条且只剩短期止血。"""
    text = _read(BODY_SECTIONS_DIR / "follow-up.md").lower()
    assert "短期止血" in text, "缺短期止血要求"
    assert "长期治理" in text, "缺长期治理要求"
    assert "不少于 4 条" in text, "缺条数下限"
    assert "少于 4 条" in text, "禁止清单未覆盖条数不足"


def test_body_sections_are_reachable_by_selector() -> None:
    """新写的标准必须真的能被选择器选中，否则不会进 prompt。"""
    catalog = [item["path"] for item in _build_incident_reference_catalog()]
    for section_id, expected in (
        ("impact", "body-sections/impact.md"),
        ("root_cause", "body-sections/root-cause.md"),
        ("follow_up", "body-sections/follow-up.md"),
    ):
        assert expected in catalog, f"{expected} 不在参考文档目录内"
        selected = _select_references_by_heuristic(section_id=section_id, available_paths=catalog)
        assert expected in selected, f"{section_id} 未选中 {expected}"


def test_golden_samples_dir_is_not_in_selector_catalog() -> None:
    """已知行为：selector 只扫描 body-sections，golden-samples 不自动注入。

    锁定这个事实，避免有人以为放了文件就会自动生效。
    若要让整份范例进 prompt，需显式改造加载逻辑。
    """
    catalog = [item["path"] for item in _build_incident_reference_catalog()]
    assert not any("golden" in path for path in catalog)
