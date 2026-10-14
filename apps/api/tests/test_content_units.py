"""content 域单元测试：personas / persona_core / skills。"""

from __future__ import annotations

import json
import time

import pytest

from zimeiti_api.content import persona_core, personas, skills
from zimeiti_api.core import settings


@pytest.fixture
def fake_profiles(tmp_path, monkeypatch):
    """临时 profiles 目录（personas 与 persona_core 双模块重定向）。"""
    pd = tmp_path / "profiles"
    bd = tmp_path / "profile_build"
    pd.mkdir()
    monkeypatch.setattr(personas, "PROFILES_DIR", pd)
    monkeypatch.setattr(personas, "PROFILE_BUILD_DIR", bd)
    monkeypatch.setattr(persona_core, "PROFILES_DIR", pd)
    return pd


def _mk_profile(pd, name, files=None):
    d = pd / name
    d.mkdir(parents=True, exist_ok=True)
    for fn, text in (files or {}).items():
        (d / fn).write_text(text, encoding="utf-8")
    return d


# ---------- personas ----------


def test_list_personas_desc_and_skip(fake_profiles):
    _mk_profile(
        fake_profiles,
        "alice",
        {"identity.md": "# 身份\n\n第一行描述这里是简介\n第二行", "extra.md": "x"},
    )
    _mk_profile(fake_profiles, "_internal", {"identity.md": "hide"})
    (fake_profiles / "empty_dir").mkdir()
    lst = personas.list_personas()
    names = [p["name"] for p in lst]
    assert names == ["alice", "empty_dir"]  # _internal 跳过
    assert lst[0]["description"].startswith("第一行描述")
    assert lst[0]["description"][:80] == lst[0]["description"]


def test_persona_routes(fake_profiles, client):
    # 404
    assert client.get("/api/persona/ghost").status_code == 404
    assert client.get("/api/persona/ghost/files").status_code == 404
    assert (
        client.put("/api/persona/ghost/file", json={"filename": "a.md", "content": "x"}).status_code
        == 404
    )

    _mk_profile(fake_profiles, "bob", {"identity.md": "内容", "notes.md": "附注"})
    r = client.get("/api/persona/bob")
    assert r.json()["name"] == "bob" and "内容" in r.json()["content"]

    r2 = client.get("/api/persona/bob/files")
    files = r2.json()["files"]
    names = [f["filename"] for f in files]
    assert names[:6] == persona_core._FILE_ORDER  # 固定顺序在前
    assert names[-1] == "notes.md"  # 其余 .md 追加在后
    assert next(f for f in files if f["filename"] == "style.md")["content"] == ""

    # 保存（原子写）
    r3 = client.put("/api/persona/bob/file", json={"filename": "style.md", "content": "新风格"})
    assert r3.json() == {"ok": True, "filename": "style.md"}
    assert (fake_profiles / "bob" / "style.md").read_text(encoding="utf-8") == "新风格"

    # 非法文件名/画像名（profile_exists 先于名字校验 → 不存在的画像 404）
    assert (
        client.put(
            "/api/persona/bob/file", json={"filename": "../x.md", "content": "x"}
        ).status_code
        == 400
    )
    assert (
        client.put("/api/persona/bob/file", json={"filename": "a.txt", "content": "x"}).status_code
        == 400
    )
    assert (
        client.put(
            "/api/persona/.hidden/file", json={"filename": "a.md", "content": "x"}
        ).status_code
        == 404
    )

    # 删除
    r4 = client.request("DELETE", "/api/persona/.bad")
    assert r4.status_code == 400
    assert client.request("DELETE", "/api/persona/ghost").status_code == 404
    r5 = client.request("DELETE", "/api/persona/bob")
    assert r5.json() == {"ok": True, "deleted": "bob"}
    assert not (fake_profiles / "bob").exists()


def test_persona_build_flow(fake_profiles, monkeypatch, client):
    calls = []

    def fake_ask(session_key, msg):
        calls.append((session_key, msg))
        return "增强完成日志"

    monkeypatch.setattr(personas, "_enhance_runtime", fake_ask)
    form = {
        "platforms": ["xhs"],
        "links": {"xhs": "https://xhs.example/u"},
        "direction": "美妆测评",
        "goal": "涨粉",
        "tone": "轻松",
        "likes": ["某博主"],
        "avoid": "医疗夸大",
    }
    r = client.post("/api/profile/build", json={"name": "  carol  ", "form": form})
    body = r.json()
    assert body["created"] is True and body["name"] == "carol" and body["status"] == "running"
    pd = fake_profiles / "carol"
    for fn in (
        "identity.md",
        "style.md",
        "audience.md",
        "platforms.md",
        "preferences.md",
        "memory.md",
    ):
        assert (pd / fn).is_file()
    ident = (pd / "identity.md").read_text(encoding="utf-8")
    assert "美妆测评" in ident and "涨粉" in ident
    plat = (pd / "platforms.md").read_text(encoding="utf-8")
    assert "## xhs" in plat and "https://xhs.example/u" in plat
    assert "医疗夸大" in (pd / "preferences.md").read_text(encoding="utf-8")

    # 增强线程很快完成（fake 同步写状态）
    for _ in range(50):
        st = client.get("/api/profile/build/status/carol").json()
        if st["state"] == "done":
            break
        time.sleep(0.02)
    assert st["state"] == "done" and st["log"] == "增强完成日志"
    assert calls and calls[0][0] == "enhance:carol"

    # 重复创建 409 / 非法名 400 / 空名 400
    assert client.post("/api/profile/build", json={"name": "carol", "form": {}}).status_code == 409
    assert client.post("/api/profile/build", json={"name": "a/b", "form": {}}).status_code == 400
    assert client.post("/api/profile/build", json={"name": "_x", "form": {}}).status_code == 400
    assert client.post("/api/profile/build", json={"name": "   ", "form": {}}).status_code == 400

    # 增强线程异常 → failed 状态（不抛）
    monkeypatch.setattr(personas, "_enhance_runtime", None)
    client.post("/api/profile/build", json={"name": "dave", "form": {}})
    for _ in range(50):
        st = client.get("/api/profile/build/status/dave").json()
        if st["state"] == "failed":
            break
        time.sleep(0.02)
    assert st["state"] == "failed" and "未接线" in st["log"]
    # 状态文件损坏/不存在 → unknown
    assert client.get("/api/profile/build/status/nobody").json() == {"state": "unknown", "log": ""}


def test_form_to_instruction():
    ins = personas._form_to_instruction(
        "n", {"links": {"xhs": "", "wb": "http://w"}, "direction": ["a", "b"]}
    )
    assert "画像名：n" in ins
    assert (
        "wb: http://w" in ins
        and "xhs:" not in ins.split("社媒主页链接")[1].split("\n想做的方向")[0]
    )
    assert "a、b" in ins
    assert "（未填）" in ins  # 缺省字段


# ---------- persona_core ----------


def test_persona_core_helpers(fake_profiles):
    _mk_profile(
        fake_profiles,
        "eve",
        {"memory.md": "记性内容", "identity.md": "身份", "other.md": "其他"},
    )
    assert persona_core.profile_exists("eve") and not persona_core.profile_exists("")
    text = persona_core.load_profile_text("eve")
    assert text.index("身份") < text.index("记性内容") < text.index("其他")  # 固定顺序 + 追加
    assert persona_core.load_profile_text("ghost") == ""
    # 前缀与拼装
    assert persona_core.persona_prefix("eve").startswith("我当前使用的画像是「eve」")
    assert persona_core.persona_prefix("ghost") == ""
    assert persona_core.persona_prefix(None) == ""
    msg = persona_core.chat_turn_message("你好", "eve")
    assert msg.startswith("我当前使用的画像") and msg.endswith(persona_core.TURN_REMINDER)
    msg2 = persona_core.chat_turn_message("你好", None)
    assert msg2 == f"你好\n\n{persona_core.TURN_REMINDER}"
    assert persona_core.turn_reminder() == persona_core.TURN_REMINDER
    # 空文件跳过
    (fake_profiles / "eve" / "identity.md").write_text("  \n", encoding="utf-8")
    assert "身份" not in persona_core.load_profile_text("eve")


# ---------- skills ----------

SKILL_MD = """---
name: foo
layer: direct
description: >-
  多行块描述第一句
  第二句
---

# 正文标题

正文内容。
"""


@pytest.fixture
def fake_skills(tmp_path, monkeypatch):
    sd = tmp_path / "skills" / "builtin"
    sd.mkdir(parents=True)
    (sd / "skill-foo").mkdir()
    (sd / "skill-foo" / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
    (sd / "plain").mkdir()
    (sd / "plain" / "SKILL.md").write_text("# 无 frontmatter\n正文", encoding="utf-8")
    monkeypatch.setattr(skills, "SKILLS_DIR", tmp_path / "skills")
    return sd


def test_find_skill(fake_skills):
    assert skills.find_skill("foo") == "skill-foo"
    assert skills.find_skill("skill-foo") == "skill-foo"
    assert skills.find_skill("nope") is None


def test_parse_skill_md(fake_skills):
    desc, layer, body = skills._parse_skill_md(fake_skills / "skill-foo" / "SKILL.md")
    assert desc == "多行块描述第一句 第二句"
    assert layer == "direct"
    assert body.startswith("# 正文标题")
    # 无 frontmatter
    desc2, layer2, body2 = skills._parse_skill_md(fake_skills / "plain" / "SKILL.md")
    assert (desc2, layer2) == ("", "")
    assert body2.startswith("# 无 frontmatter")
    # 未闭合 frontmatter
    p = fake_skills / "skill-foo" / "broken.md"
    p.write_text("---\ndescription: x\n没有闭合\n", encoding="utf-8")
    assert skills._parse_skill_md(p) == ("", "", "---\ndescription: x\n没有闭合\n")
    # 行内 description
    p.write_text("---\nlayer: produce\ndescription: '单行描述'\n---\nbody", encoding="utf-8")
    d, lay, b = skills._parse_skill_md(p)
    assert (d, lay, b) == ("单行描述", "produce", "body")


def test_get_skills_route(fake_skills, client):
    lst = client.get("/api/skills").json()
    by = {s["name"]: s for s in lst}
    assert "skill-foo" in by and "plain" in by
    assert by["skill-foo"]["layer"] == "direct" and by["skill-foo"]["needsApi"] is False
    assert by["skill-foo"]["apiConfigured"] is True  # 不需要 API 的默认已配置
    assert "needsApi" in by["skill-foo"]


def test_skill_detail_needs_api(fake_skills, monkeypatch, client):
    # 注册表中的 skill（ai-image-gen）→ apiSpec 脱敏输出
    monkeypatch.setitem(
        settings.SKILL_API_REQUIREMENTS,
        "skill-foo",
        settings.SKILL_API_REQUIREMENTS["ai-image-gen"],
    )
    r = client.get("/api/skill/foo")
    body = r.json()
    assert body["needsApi"] is True and body["apiSpec"] is not None
    keys = body["apiSpec"]["providers"][0]["keys"]
    assert all("masked" in k and "configured" in k for k in keys)
    assert all("sk-secret" not in json.dumps(body) for _ in [1])  # 不回明文
    assert client.get("/api/skill/ghost").status_code == 404


def test_api_spec_status_masking(fake_skills):
    env = {"IMG_API_KEY": "sk-secret-12345678", "IMG_BASE_URL": "https://x"}
    st = skills._api_spec_status("ai-image-gen", env)
    all_keys = [k for p in st["providers"] for k in p["keys"]] + st["settings"]
    k = next(k for k in all_keys if k["env"] == "IMG_API_KEY")
    assert k["masked"] == "••••5678" and k["configured"] is True
    assert "sk-secret" not in json.dumps(st)  # 全响应无明文
    # 非必填未配置不算缺失
    assert any(kk["env"] == "IMG_MODEL" and kk["configured"] is False for kk in all_keys)
    # 短 secret 全遮
    st2 = skills._api_spec_status("ai-image-gen", {"IMG_API_KEY": "ab"})
    k2 = next(k for p in st2["providers"] for k in p["keys"] if k["env"] == "IMG_API_KEY")
    assert k2["masked"] == "••••"
