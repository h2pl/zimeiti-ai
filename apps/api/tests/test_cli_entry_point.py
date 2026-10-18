"""cli-entry-point：HTTP 客户端与命令树（mock 传输，零网络）。

覆盖规格：
- 客户端错误翻译（4xx/5xx/连接失败 → 可行动中文错误）
- SSE 帧解析（token/activity/error/done）
- 命令树（chat/flows/runs/usage 存在、参数解析、退出码契约）
"""

from __future__ import annotations

import io
import sys
from unittest import mock

import pytest

from zimeiti_cli import cli as cli_mod
from zimeiti_cli import client as cl


# ── 1. 客户端错误翻译 ──────────────────────────────────────────────────────
def test_api_error_4xx_translates():
    raw = '{"detail":"流程不存在"}'.encode()
    with pytest.raises(cl.ApiError) as ei:
        cl._raise_for_status(404, raw, "GET", "/api/flows/x")
    msg = str(ei.value)
    assert "404" in msg and "流程不存在" in msg


def test_api_error_connection_refused_is_actionable():
    with mock.patch("urllib.request.urlopen", side_effect=OSError("refused")):
        with pytest.raises(cl.ApiError) as ei:
            cl.get("http://127.0.0.1:9", "/api/status")
    assert "make api" in str(ei.value) or "启动" in str(ei.value)


def test_sse_parses_frames():
    frames_raw = [
        "event: token",
        'data: "你好"',
        "",
        "event: activity",
        'data: "思考中"',
        "",
        "event: error",
        'data: "炸了"',
        "",
        "data: [DONE]",
        "",
    ]
    resp = io.BytesIO(("\n".join(frames_raw) + "\n").encode("utf-8"))
    frames = list(cl._iter_sse(resp))
    assert frames == [("token", "你好"), ("activity", "思考中"), ("error", "炸了")]


# ── 2. 命令树 ───────────────────────────────────────────────────────────────
def test_parser_has_all_subcommands():
    p = cli_mod.build_parser()
    sub = [a for a in p._subparsers._group_actions[0].choices]
    assert set(sub) >= {"chat", "flows", "runs", "usage"}


def test_chat_command_parses():
    p = cli_mod.build_parser()
    ns = p.parse_args(["chat", "你好", "--session", "s1", "--timeout", "5"])
    assert ns.message == "你好" and ns.session == "s1" and ns.timeout == 5


def test_flows_new_parses_steps():
    p = cli_mod.build_parser()
    ns = p.parse_args(
        ["flows", "new", "--name", "每日选题", "--steps", "discover,plan", "--schedule", "08:00"]
    )
    assert ns.name == "每日选题" and ns.steps == "discover,plan"


def test_base_accepts_both_positions():
    """--base 在子命令前后都能写（argparse 全局参数必须在子命令前——探针抓到的真 bug）。"""
    p = cli_mod.build_parser()
    assert p.parse_args(["--base", "http://a:1", "runs"]).base == "http://a:1"
    assert p.parse_args(["runs", "--base", "http://b:2"]).base == "http://b:2"
    assert p.parse_args(["runs"]).base == cl.DEFAULT_BASE


def test_exit_code_contract():
    """连接失败 → 退出码 1（ApiError→main 捕获），错误含行动指引（stderr）。"""
    out, err = io.StringIO(), io.StringIO()
    with (
        mock.patch.object(sys, "argv", ["zimeiti", "usage"]),
        mock.patch("urllib.request.urlopen", side_effect=OSError("refused")),
        mock.patch.object(sys, "stdout", out),
        mock.patch.object(sys, "stderr", err),
    ):
        rc = cli_mod.main()
    assert rc == 1
    assert "无法连接" in err.getvalue() and "make api" in err.getvalue()


def test_flows_list_prints_table():
    payload = {
        "flows": [
            {
                "id": "abc123",
                "name": "每日选题",
                "steps": ["discover", "plan"],
                "schedule": "08:00",
                "enabled": True,
                "config": {"draft_only": True},
            },
        ]
    }
    out = io.StringIO()
    with (
        mock.patch.object(cli_mod.cl, "get", return_value=payload),
        mock.patch.object(sys, "argv", ["zimeiti", "flows"]),
        mock.patch.object(sys, "stdout", out),
    ):
        rc = cli_mod.main()
    assert rc == 0
    text = out.getvalue()
    assert "每日选题" in text and "发现" in text and "选题" in text
