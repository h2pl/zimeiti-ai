"""ExecTool 白名单命令执行器（agent-shell-exec）。

TDD RED：exec_tool 模块尚不存在；实现后 GREEN。
"""

import pytest

MOD = "zimeiti_harness.runtime.exec_tool"


@pytest.fixture()
def reg(monkeypatch):
    """把注册表替换为测试专用（不依赖真实技能脚本）。"""
    from zimeiti_harness.runtime import exec_tool as et

    monkeypatch.setattr(
        et,
        "SCRIPT_REGISTRY",
        {
            "probe-ok": {
                "path": "skills/shared/scripts/__exec_probe.py",
                "params": {"--n": "int", "--text": "str"},
                "desc": "测试用回显脚本",
            },
        },
        raising=False,
    )
    return et


def test_runs_registered_script(reg, tmp_path, monkeypatch):
    probe = tmp_path / "probe.py"
    probe.write_text(
        "import sys; print('OUT:' + ' '.join(sys.argv[1:])); sys.stderr.write('E1')",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        reg,
        "SCRIPT_REGISTRY",
        {
            "probe-ok": {
                "path": str(probe),
                "params": {"--n": "int", "--text": "str"},
                "desc": "probe",
            }
        },
        raising=False,
    )
    r = reg.exec_script("probe-ok", {"--n": "3", "--text": "hello"})
    assert r["exit_code"] == 0
    assert "OUT:--n 3 --text hello" in r["stdout"]
    assert "E1" in r["stderr"]


def test_rejects_unregistered(reg):
    r = reg.exec_script("rm-rf", {"--x": "1"})
    assert r["exit_code"] != 0
    assert "白名单" in r["stderr"] or "未注册" in r["stderr"]


@pytest.mark.parametrize(
    "bad",
    ["../etc/passwd", "/abs/path", "a;rm -rf", "a$(id)", "a`id`", "a|b", "a&&b"],
)
def test_rejects_path_injection(reg, tmp_path, monkeypatch, bad):
    probe = tmp_path / "probe.py"
    probe.write_text("import sys; print(sys.argv[1])", encoding="utf-8")
    monkeypatch.setattr(
        reg,
        "SCRIPT_REGISTRY",
        {"probe-ok": {"path": str(probe), "params": {"--p": "str"}, "desc": "probe"}},
        raising=False,
    )
    r = reg.exec_script("probe-ok", {"--p": bad})
    assert r["exit_code"] != 0
    assert "拒绝" in r["stderr"] or "非法" in r["stderr"]


def test_rejects_unknown_param(reg, tmp_path, monkeypatch):
    probe = tmp_path / "probe.py"
    probe.write_text("print('x')", encoding="utf-8")
    monkeypatch.setattr(
        reg,
        "SCRIPT_REGISTRY",
        {"probe-ok": {"path": str(probe), "params": {"--p": "str"}, "desc": "probe"}},
        raising=False,
    )
    r = reg.exec_script("probe-ok", {"--evil": "x"})
    assert r["exit_code"] != 0
    assert "参数" in r["stderr"]


def test_timeout_terminates(reg, tmp_path, monkeypatch):
    probe = tmp_path / "slow.py"
    probe.write_text("import time; time.sleep(30)", encoding="utf-8")
    monkeypatch.setattr(
        reg,
        "SCRIPT_REGISTRY",
        {"probe-slow": {"path": str(probe), "params": {}, "desc": "slow"}},
        raising=False,
    )
    monkeypatch.setattr(reg, "DEFAULT_TIMEOUT", 1, raising=False)
    t0 = __import__("time").monotonic()
    r = reg.exec_script("probe-slow", {})
    assert r["exit_code"] != 0
    assert "超时" in r["stderr"]
    assert __import__("time").monotonic() - t0 < 15


def test_output_truncated(reg, tmp_path, monkeypatch):
    probe = tmp_path / "big.py"
    probe.write_text("print('x' * 50000)", encoding="utf-8")
    monkeypatch.setattr(
        reg,
        "SCRIPT_REGISTRY",
        {"probe-big": {"path": str(probe), "params": {}, "desc": "big"}},
        raising=False,
    )
    r = reg.exec_script("probe-big", {})
    assert r["exit_code"] == 0
    assert len(r["stdout"]) < 9000
    assert r["truncated"] is True


def test_registry_lists_available(reg):
    names = [s["name"] for s in reg.available_scripts()]
    assert "probe-ok" in names
