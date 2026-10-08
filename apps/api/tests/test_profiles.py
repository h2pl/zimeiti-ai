"""Task 3.1/3.2 验收：画像 schema 校验、加载、创作注入与多账号隔离。"""

import pytest

from zimeiti_api.profiles import (
    build_profile_context,
    load_profile,
    validate_profile,
)

VALID = {
    "account": "xhs-main",
    "positioning": "职场干货分享",
    "style": "轻松、有梗、短句",
    "audience": "25-35 岁互联网从业者",
    "platform_rules": "标题 ≤20 字，正文 ≤1000 字，带 3-5 个标签",
    "preferences": "不碰政治，不夸大收益",
}


def test_validate_passes_and_rejects_missing_fields():
    assert validate_profile(VALID) is True
    with pytest.raises(ValueError) as exc:
        validate_profile({k: v for k, v in VALID.items() if k != "preferences"})
    assert "preferences" in str(exc.value)  # 红线字段缺失必须点名


def test_load_profile_from_file(tmp_path):
    import yaml

    f = tmp_path / "xhs-main" / "profile.yaml"
    f.parent.mkdir()
    f.write_text(yaml.dump(VALID, allow_unicode=True), encoding="utf-8")
    profile = load_profile("xhs-main", base_dir=tmp_path)
    assert profile["account"] == "xhs-main"


def test_creation_context_isolation():
    ctx_a = build_profile_context(VALID)
    other = {**VALID, "account": "gzh-main", "positioning": "母婴育儿"}
    ctx_b = build_profile_context(other)
    # 账号 A 的上下文不含账号 B 的画像内容
    assert "职场干货分享" in ctx_a
    assert "母婴育儿" not in ctx_a
    assert "母婴育儿" in ctx_b
