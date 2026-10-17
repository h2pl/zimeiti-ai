"""pg-data-layer 单元测试（PG 数据层）。

覆盖验收点：
- A5 导入脚本幂等（test_import_*）
- A7 schema 租户维度预留（test_user_id_dimension）
- A3 ideas/schedule CRUD 契约（字段与文件版一致）
- A9 会话删除清尽全部状态（test_session_delete_removes_all）
- HITL pending TTL 语义与文件版一致（test_pending_*）
"""

from __future__ import annotations

import json
import time
import uuid

from zimeiti_api.core import pg

# ---------- schema / 多租户预留（A7） ----------


def test_setup_idempotent():
    pg.setup()
    pg.setup()  # 第二次不报错、不丢数据


def test_user_id_dimension():
    """本变更新建的业务表都必须带 user_id 列且默认 'local'（A7）。"""
    tables = [
        "chat_sessions",
        "chat_messages",
        "hitl_pending",
        "ideas",
        "schedule_items",
    ]
    with pg.connect() as conn:
        for t in tables:
            row = conn.execute(
                """
                SELECT column_name, column_default, is_nullable
                FROM information_schema.columns
                WHERE table_name=%s AND column_name='user_id'
                """,
                (t,),
            ).fetchone()
            assert row is not None, f"{t} 缺少 user_id 列"
            assert row[1] and "'local'" in row[1], f"{t}.user_id 默认值应为 'local'，实际 {row[1]}"
            assert row[2] == "NO", f"{t}.user_id 应 NOT NULL"


# ---------- 会话历史 ----------


def test_messages_roundtrip_and_delete(uid):
    sk = f"sess-{uuid.uuid4().hex[:8]}"
    pg.messages_save(
        sk,
        [{"role": "user", "content": "你好"}, {"role": "assistant", "content": "在的"}],
        user_id=uid,
    )
    msgs = pg.messages_load(sk, user_id=uid)
    assert msgs == [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "在的"},
    ]
    # 整表替换语义：再保存两条覆盖为一条
    pg.messages_save(sk, [{"role": "user", "content": "第二条"}], user_id=uid)
    assert pg.messages_load(sk, user_id=uid) == [{"role": "user", "content": "第二条"}]
    # 空 content 不入库（与文件版过滤一致）
    pg.messages_save(sk, [{"role": "user", "content": ""}], user_id=uid)
    assert pg.messages_load(sk, user_id=uid) == []


def test_session_delete_removes_all(uid):
    """A9（pg 层）：session_delete 删消息行 + 会话行。
    pending/checkpoint 的联动清理由 agent_runtime.delete_session 负责，
    见 test_delete_session_wiring_clears_pending。"""
    sk = f"sess-{uuid.uuid4().hex[:8]}"
    pg.messages_save(sk, [{"role": "user", "content": "x"}], user_id=uid)
    assert pg.session_delete(sk, user_id=uid) is True
    assert pg.messages_load(sk, user_id=uid) == []
    assert pg.session_exists(sk, user_id=uid) is False
    # 再删返回 False（无状态可删）
    assert pg.session_delete(sk, user_id=uid) is False


def test_pending_delete_by_session_only_touches_that_session(uid):
    """session 级 pending 删除不影响其他 session 的行。"""
    sk1, sk2 = f"sess-{uuid.uuid4().hex[:8]}", f"sess-{uuid.uuid4().hex[:8]}"
    q1, q2 = uuid.uuid4().hex, uuid.uuid4().hex
    pg.pending_set(q1, sk1, {"id": q1, "thread_id": sk1}, user_id=uid)
    pg.pending_set(q2, sk2, {"id": q2, "thread_id": sk2}, user_id=uid)
    assert pg.pending_delete_by_session(sk1, user_id=uid) == 1
    assert pg.pending_get(q1, user_id=uid) is None
    assert pg.pending_get(q2, user_id=uid) is not None
    pg.pending_del(q2)


def test_delete_session_wiring_clears_pending(uid):
    """A9 接线：agent_runtime.delete_session 真的联动清 pending（不只是 pg 层）。"""
    import asyncio

    from zimeiti_harness.runtime import agent_runtime as ar

    sk = f"sess-{uuid.uuid4().hex[:8]}"
    qid = uuid.uuid4().hex
    pg.messages_save(sk, [{"role": "user", "content": "x"}], user_id=uid)
    pg.pending_set(qid, sk, {"id": qid, "thread_id": sk}, user_id=uid)

    deleted = asyncio.run(ar.delete_session(sk, user_id=uid))
    assert deleted is True
    assert pg.messages_load(sk, user_id=uid) == []
    assert pg.pending_get(qid, user_id=uid) is None


def test_session_tenant_isolation(uid):
    """同一 session_key 在不同 user_id 下互相隔离（多租户预留）。"""
    sk = f"sess-{uuid.uuid4().hex[:8]}"
    other = uid + "-b"
    pg.messages_save(sk, [{"role": "user", "content": "A"}], user_id=uid)
    pg.messages_save(sk, [{"role": "user", "content": "B"}], user_id=other)
    assert pg.messages_load(sk, user_id=uid) == [{"role": "user", "content": "A"}]
    assert pg.messages_load(sk, user_id=other) == [{"role": "user", "content": "B"}]
    pg.session_delete(sk, user_id=other)


# ---------- HITL pending（TTL 语义与文件版一致） ----------


def test_pending_lifecycle(uid):
    qid = uuid.uuid4().hex
    sk = f"sess-{uuid.uuid4().hex[:8]}"
    payload = {"id": qid, "thread_id": sk, "created_at": time.time()}
    pg.pending_set(qid, sk, payload, user_id=uid)
    assert pg.pending_get(qid, user_id=uid) == payload
    assert pg.pending_status([qid], user_id=uid) == {qid: {"status": "pending"}}
    assert pg.pending_load(user_id=uid).get(qid) == payload
    pg.pending_del(qid)
    assert pg.pending_get(qid, user_id=uid) is None
    assert pg.pending_status([qid], user_id=uid) == {qid: {"status": "not_found"}}


def test_pending_ttl_expired(uid):
    """超 30 分钟未答的 pending 自动失效（与文件版 TTL_SECONDS 一致）。

    TTL 以数据库服务器时间判（比客户端时钟稳）；直接插一条 40 分钟前的行
    模拟「写入很久未答」的真实场景。
    """
    qid = uuid.uuid4().hex
    sk = f"sess-{uuid.uuid4().hex[:8]}"
    with pg.connect() as conn:
        conn.execute(
            """
            INSERT INTO hitl_pending (question_id, user_id, session_key, payload, created_at)
            VALUES (%s,%s,%s,%s, now() - interval '40 minutes')
            """,
            (
                qid,
                uid,
                sk,
                json.dumps({"id": qid, "thread_id": sk}, ensure_ascii=False),
            ),
        )
        conn.commit()
    assert pg.pending_get(qid, user_id=uid) is None
    assert pg.pending_status([qid], user_id=uid) == {qid: {"status": "not_found"}}
    assert qid not in pg.pending_load(user_id=uid)
    pg.pending_del(qid)


# ---------- ideas / schedule（A3 字段与文件版一致） ----------


def test_ideas_order_and_crud(uid):
    """ideas 展示序=最新在前；replace_all 保序；粒度 CRUD 可用。"""
    older = {
        "id": uuid.uuid4().hex[:12],
        "title": "旧选题",
        "note": "",
        "source": "",
        "status": "done",
        "created": int(time.time()) - 100,
    }
    newer = {
        "id": uuid.uuid4().hex[:12],
        "title": "新选题",
        "note": "n",
        "source": "chat",
        "status": "pending",
        "created": int(time.time()),
    }
    pg.ideas_replace_all([newer, older], user_id=uid)  # 调用方传入展示序
    items = pg.ideas_list(user_id=uid)
    assert [i["title"] for i in items] == ["新选题", "旧选题"]  # 最新在前不回退
    assert set(items[0]) == {"id", "title", "note", "source", "status", "created"}

    row = pg.ideas_insert({"title": "插入的", "status": "doing"}, user_id=uid)
    assert row["title"] == "插入的" and len(row["id"]) == 12
    assert pg.ideas_list(user_id=uid)[0]["title"] == "插入的"  # 插在最前

    updated = pg.ideas_update(row["id"], {"title": "改过的", "status": "done"}, user_id=uid)
    assert updated["title"] == "改过的" and updated["status"] == "done"
    assert pg.ideas_update(row["id"], {"note": "x"}, user_id=uid)["note"] == "x"

    assert pg.ideas_delete(row["id"], user_id=uid) is True
    assert pg.ideas_delete(row["id"], user_id=uid) is False


def test_schedule_order_and_crud(uid):
    """schedule 展示序=追加序；replace_all 保序；字段与文件版 ScheduleItem 一致。"""
    first = {
        "id": uuid.uuid4().hex[:12],
        "title": "周一发",
        "date": "2026-10-19",
        "platform": "小红书",
        "time": "09:00",
        "status": "scheduled",
        "note": "",
        "kind": "content",
        "url": "",
        "source": "manual",
        "event_type": "",
        "end_date": "",
    }
    second = {
        "id": uuid.uuid4().hex[:12],
        "title": "活动",
        "date": "2026-10-20",
        "kind": "event",
        "status": "idea",
        "event_type": "平台活动",
    }
    pg.schedule_replace_all([first, second], user_id=uid)
    items = pg.schedule_list(user_id=uid)
    assert [i["title"] for i in items] == ["周一发", "活动"]  # 追加序不回退
    assert set(items[0]) == {
        "id",
        "title",
        "date",
        "platform",
        "time",
        "status",
        "note",
        "kind",
        "url",
        "source",
        "event_type",
        "end_date",
    }
    assert items[1]["kind"] == "event" and items[1]["event_type"] == "平台活动"

    updated = pg.schedule_update(first["id"], {"status": "published"}, user_id=uid)
    assert updated["status"] == "published"
    assert pg.schedule_delete(second["id"], user_id=uid) is True
    assert pg.schedule_delete(second["id"], user_id=uid) is False


# ---------- 一次性导入脚本幂等（A5） ----------


def _write_fixture(root, sk="sess-abc123", qid="q-abc123"):
    (root / "sessions").mkdir(parents=True, exist_ok=True)
    (root / "outputs").mkdir(parents=True, exist_ok=True)
    (root / "sessions" / f"{sk}.json").write_text(
        json.dumps(
            {
                "messages": [
                    {"role": "user", "content": "历史1"},
                    {"role": "assistant", "content": "回复1"},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (root / "sessions" / "pending_questions.json").write_text(
        json.dumps(
            {qid: {"id": qid, "thread_id": sk, "created_at": time.time()}},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (root / "outputs" / "_ideas.json").write_text(
        json.dumps(
            [
                {
                    "id": "idea-1",
                    "title": "导入选题",
                    "note": "",
                    "source": "",
                    "status": "pending",
                    "created": 1,
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (root / "outputs" / "_schedule.json").write_text(
        json.dumps(
            [{"id": "sch-1", "title": "导入排期", "date": "2026-10-14"}],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return sk, qid


def test_import_idempotent(tmp_path, uid):
    """A5：导入脚本跑两次——第二次全部跳过、不产生重复记录。"""
    import importlib.util
    from pathlib import Path

    script = Path(__file__).resolve().parents[2] / "scripts" / "migrate_files_to_pg.py"
    spec = importlib.util.spec_from_file_location("migrate_files_to_pg", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    sk, qid = _write_fixture(tmp_path)

    first = mod.migrate(tmp_path, user_id=uid)
    assert first["imported"]["sessions"] == 1
    assert first["imported"]["messages"] == 2
    assert first["imported"]["pending"] == 1
    assert first["imported"]["ideas"] == 1
    assert first["imported"]["schedule"] == 1

    second = mod.migrate(tmp_path, user_id=uid)
    assert second["imported"] == {
        "sessions": 0,
        "messages": 0,
        "pending": 0,
        "ideas": 0,
        "schedule": 0,
    }
    assert second["skipped"] == {"sessions": 1, "pending": 1, "ideas": 1, "schedule": 1}

    # 落库内容与文件一致
    assert pg.messages_load(sk, user_id=uid) == [
        {"role": "user", "content": "历史1"},
        {"role": "assistant", "content": "回复1"},
    ]
    assert pg.pending_get(qid, user_id=uid) is not None
    assert [i["title"] for i in pg.ideas_list(user_id=uid)] == ["导入选题"]
    assert [i["title"] for i in pg.schedule_list(user_id=uid)] == ["导入排期"]
    # pending 行归测试租户，fixture 清理会收尾
