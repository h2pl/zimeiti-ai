"""content 域路由测试：ideas / schedule / outputs（TestClient，PG 用 local 租户自清理）。"""

from __future__ import annotations

import json
import shutil

import pytest

from zimeiti_api.content import outputs as outputs_mod
from zimeiti_api.content import trends as trends_mod
from zimeiti_api.content import uploads as uploads_mod
from zimeiti_api.core import paths as paths_mod

# ---------- ideas ----------


def test_ideas_crud(client):
    # 创建
    r = client.post("/api/ideas", json={"title": "测试选题A", "note": "n", "source": "test"})
    assert r.status_code == 200
    item = r.json()
    iid = item["id"]
    assert item["status"] == "pending" and item["title"] == "测试选题A"
    try:
        # 非法状态回退 pending
        r2 = client.post("/api/ideas", json={"title": "x", "status": "bogus"})
        assert r2.json()["status"] == "pending"
        client.delete(f"/api/ideas/{r2.json()['id']}")

        # 列表含新条目且最新在前
        lst = client.get("/api/ideas").json()
        assert any(i["id"] == iid for i in lst)
        assert lst[0]["id"] == iid

        # 更新
        r3 = client.put(
            f"/api/ideas/{iid}", json={"title": "改名", "status": "doing", "note": "", "source": ""}
        )
        assert r3.json()["status"] == "doing" and r3.json()["title"] == "改名"
        # 非法状态保持原值
        r4 = client.put(
            f"/api/ideas/{iid}", json={"title": "改名", "status": "bogus", "note": "", "source": ""}
        )
        assert r4.json()["status"] == "doing"
    finally:
        client.delete(f"/api/ideas/{iid}")

    # 404 分支
    assert (
        client.put("/api/ideas/nope", json={"title": "x", "note": "", "source": ""}).status_code
        == 404
    )
    assert client.delete("/api/ideas/nope").status_code == 404
    empty = client.post("/api/ideas", json={"title": "   "}).json()  # 空标题回退分支
    assert empty["title"] == "未命名选题"
    client.delete(f"/api/ideas/{empty['id']}")  # 用后即清（曾污染 local 租户 18 条）


# ---------- schedule ----------


def test_schedule_crud(client):
    r = client.post(
        "/api/schedule", json={"title": "测试排期", "date": "2030-01-01", "platform": "xhs"}
    )
    assert r.status_code == 200
    sid = r.json()["id"]
    try:
        assert r.json()["kind"] == "content" and r.json()["source"] == "manual"
        # event 类型 + 非法 kind/source 回退
        r2 = client.post(
            "/api/schedule",
            json={
                "title": "",
                "date": "2030-02-02",
                "kind": "event",
                "source": "bogus",
                "status": "bogus",
            },
        )
        assert r2.json()["kind"] == "event" and r2.json()["status"] == "idea"
        assert r2.json()["title"] == "未命名活动" and r2.json()["source"] == "manual"
        client.delete(f"/api/schedule/{r2.json()['id']}")

        lst = client.get("/api/schedule").json()
        assert any(i["id"] == sid for i in lst)

        r3 = client.put(
            f"/api/schedule/{sid}",
            json={"title": "改期", "date": "2030-01-02", "status": "scheduled"},
        )
        assert r3.json()["date"] == "2030-01-02" and r3.json()["status"] == "scheduled"
    finally:
        client.delete(f"/api/schedule/{sid}")

    assert client.put("/api/schedule/nope", json={"title": "x", "date": "d"}).status_code == 404
    assert client.delete("/api/schedule/nope").status_code == 404


def test_schedule_context(client):
    r = client.get("/api/schedule/context", params={"days": 3})
    assert r.status_code == 200  # 失败也返回 {}，不抛错
    assert isinstance(r.json(), dict)
    # days 越界钳制
    r2 = client.get("/api/schedule/context", params={"days": 999})
    assert r2.status_code == 200


# ---------- outputs ----------


@pytest.fixture
def fake_outputs(tmp_path, monkeypatch):
    """临时 outputs 树 + 双模块 OUTPUTS_DIR 重定向（outputs 自持引用 + paths 安全函数）。"""
    proj = tmp_path / "proj1"
    proj.mkdir()
    (proj / "readme.txt").write_text("hello 文本", encoding="utf-8")
    (proj / "cover.png").write_bytes(b"\x89PNG fake")
    (proj / "clip.mp4").write_bytes(b"fake video")
    (proj / ".hidden.txt").write_text("hide", encoding="utf-8")
    (proj / ".easel.json").write_text(
        json.dumps(
            {
                "title": "项目一",
                "summary": "s",
                "platform": "xhs",
                "deliverables": ["clip.mp4"],
                "cover": "cover.png",
            }
        ),
        encoding="utf-8",
    )
    sys_dir = tmp_path / "_login"
    sys_dir.mkdir()
    (sys_dir / "state.json").write_text("{}", encoding="utf-8")
    (tmp_path / "analytics").mkdir()
    (tmp_path / "loose.txt").write_text("loose", encoding="utf-8")
    monkeypatch.setattr(paths_mod, "OUTPUTS_DIR", tmp_path)
    monkeypatch.setattr(outputs_mod, "OUTPUTS_DIR", tmp_path)
    return tmp_path


def test_outputs_tree(fake_outputs, client):
    tree = client.get("/api/outputs").json()
    names = [n["name"] for n in tree]
    assert names == ["proj1"]  # 系统/隐藏/散文件被过滤
    node = tree[0]
    assert node["type"] == "dir" and node["fileCount"] == 3  # 隐藏文件不计
    kids = {c["name"]: c for c in node["children"]}
    assert kids["readme.txt"]["kind"] == "text"
    assert kids["cover.png"]["kind"] == "image"
    assert kids["clip.mp4"]["kind"] == "video"
    assert ".hidden.txt" not in kids
    meta = node["meta"]
    assert meta["title"] == "项目一" and meta["platform"] == "xhs"
    assert meta["cover"] == "proj1/cover.png"  # 声明封面优先
    assert meta["deliverablePaths"] == ["proj1/clip.mp4"]


def test_outputs_tree_meta_broken_json(fake_outputs, client):
    (fake_outputs / "proj1" / ".easel.json").write_text("{broken", encoding="utf-8")
    tree = client.get("/api/outputs").json()
    assert "meta" not in tree[0]
    (fake_outputs / "proj1" / ".easel.json").write_text(
        json.dumps({"title": "ok"}), encoding="utf-8"
    )
    tree2 = client.get("/api/outputs").json()
    assert tree2[0]["meta"]["title"] == "ok"
    assert "cover" not in tree2[0]["meta"]  # 无封面声明且 deliverables 空


def test_output_file_content(fake_outputs, client):
    r = client.get("/api/output/proj1/readme.txt")
    assert r.json() == {
        "path": "proj1/readme.txt",
        "content": "hello 文本",
        "kind": "text",
        "isBinary": False,
    }
    r2 = client.get("/api/output/proj1/cover.png")
    assert r2.json()["isBinary"] is True and r2.json()["kind"] == "image"
    # GBK 不可解码的文本 → binary 兜底
    (fake_outputs / "proj1" / "bin.txt").write_bytes(b"\xff\xfe\x81\x81")
    r3 = client.get("/api/output/proj1/bin.txt")
    assert r3.json()["isBinary"] is True and r3.json()["kind"] == "binary"
    # 穿越与缺失
    assert client.get("/api/output/../secret.txt").status_code in (403, 404)
    assert client.get("/api/output/proj1/nope.txt").status_code == 404


def test_media_headers(fake_outputs, client):
    (fake_outputs / "proj1" / "page.html").write_text("<html></html>", encoding="utf-8")
    r = client.get("/api/media/proj1/page.html")
    assert r.status_code == 200
    assert "no-cache" in r.headers["cache-control"]
    r2 = client.get("/api/media/proj1/cover.png")
    assert r2.status_code == 200
    assert "cache-control" not in r2.headers or "no-cache" not in r2.headers.get(
        "cache-control", ""
    )


def test_output_delete_rules(fake_outputs, client):
    # 受保护：顶层 _ 目录 / analytics / 根散文件
    assert client.delete("/api/output/_login/state.json").status_code == 403
    assert client.delete("/api/output/analytics").status_code == 403
    # 正常删除文件与目录
    (fake_outputs / "proj1" / "del.txt").write_text("x", encoding="utf-8")
    r = client.delete("/api/output/proj1/del.txt")
    assert r.json() == {"ok": True, "deleted": "proj1/del.txt", "kind": "file"}
    r2 = client.request("DELETE", "/api/output/proj1/cover.png")
    assert r2.json()["kind"] == "file"
    assert client.delete("/api/output/proj1").json()["kind"] == "dir"
    assert not (fake_outputs / "proj1").exists()
    assert client.delete("/api/output/proj1").status_code == 404


def test_file_kind_and_meta():
    assert outputs_mod._file_kind("a.MP4") == "video"
    assert outputs_mod._file_kind("a.md") == "text"
    assert outputs_mod._file_kind("a.mp3") == "audio"
    assert outputs_mod._file_kind("a.weird") == "binary"
    m = outputs_mod._file_meta(paths_mod.OUTPUTS_DIR / "__nope__.txt", "x")
    assert m["mtime"] == 0 and m["size"] == 0  # OSError 兜底


def test_outputs_dir_missing(monkeypatch, client):
    import pathlib

    monkeypatch.setattr(outputs_mod, "OUTPUTS_DIR", pathlib.Path("__definitely_missing_dir__"))
    assert client.get("/api/outputs").json() == []


# ---------- uploads ----------


@pytest.fixture
def fake_upload_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(uploads_mod, "OUTPUTS_DIR", tmp_path)
    yield tmp_path
    shutil.rmtree(tmp_path / "_inbox", ignore_errors=True)


def test_attachment_scope_and_id():
    s = uploads_mod._attachment_scope("sess-1")
    assert len(s) == 20 and uploads_mod._attachment_scope(" sess-1 ") == s
    assert uploads_mod._attachment_id(s, "p") == uploads_mod._attachment_id(s, "p")
    assert uploads_mod._attachment_id(s, "p") != uploads_mod._attachment_id(s, "q")
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        uploads_mod._attachment_scope("   ")
    with pytest.raises(HTTPException):
        uploads_mod._attachment_scope("x" * 257)


def test_unique_upload_path(fake_upload_dir):
    d = fake_upload_dir / "b"
    d.mkdir()
    f1 = uploads_mod._unique_upload_path(d, "a.png")
    f1.write_bytes(b"x")
    f2 = uploads_mod._unique_upload_path(d, "a.png")
    f2.write_bytes(b"y")
    f3 = uploads_mod._unique_upload_path(d, "a.png")
    assert [p.name for p in (f1, f2, f3)] == ["a.png", "a (2).png", "a (3).png"]


def test_upload_roundtrip(fake_upload_dir, client):
    r = client.post(
        "/api/upload",
        files=[
            ("files", ("a.png", b"\x89PNG", "image/png")),
            ("files", ("b.md", b"# h", "text/markdown")),
        ],
        data={"sessionId": "sess-9"},
    )
    assert r.status_code == 200 and r.json()["ok"] is True
    files = r.json()["files"]
    assert files[0]["name"] == "a.png"
    assert files[0]["path"].startswith("_inbox/")
    # 落盘真实存在
    saved = fake_upload_dir / files[0]["path"]
    assert saved.read_bytes() == b"\x89PNG"
    # limits 端点
    assert client.get("/api/upload/limits").json() == {"ok": True, "max_mb": 50}


def test_upload_rejects_bad_ext_and_duplicate_names(fake_upload_dir, client):
    r = client.post(
        "/api/upload",
        files=[("files", ("evil.exe", b"MZ", "application/octet-stream"))],
        data={"sessionId": "sess-9"},
    )
    assert r.status_code == 400
    # 同名文件保留全部（不覆盖）
    r2 = client.post(
        "/api/upload",
        files=[("files", ("a.txt", b"1", "text/plain")), ("files", ("a.txt", b"2", "text/plain"))],
        data={"sessionId": "sess-9"},
    )
    names = [f["name"] for f in r2.json()["files"]]
    assert names == ["a.txt", "a (2).txt"]


def test_upload_local_channel(fake_upload_dir, client):
    big = b"x" * (1024 * 1024 + 11)  # >1MB，走分块路径
    r = client.post(
        "/api/upload/local",
        files=[("files", ("big.bin.txt", big, "text/plain"))],
        data={"sessionId": "sess-9"},
    )
    assert r.status_code == 200
    saved = fake_upload_dir / r.json()["files"][0]["path"]
    assert saved.read_bytes() == big


# ---------- trends ----------


def test_parse_hot_variants():
    assert trends_mod._parse_hot({"data": {"data": [{"title": "t1", "hot": 99, "url": "u"}]}}) == [
        {"title": "t1", "hot": "99", "url": "u"}
    ]
    assert (
        trends_mod._parse_hot({"data": [{"word": "w", "hot_value": 1, "link": "l"}]})[0]["title"]
        == "w"
    )
    assert trends_mod._parse_hot({"data": [{"name": "n", "num": 2, "mobil_url": "m"}]})[0] == {
        "title": "n",
        "hot": "2",
        "url": "m",
    }
    assert trends_mod._parse_hot({"data": ["not-dict", {}, ""]}) == []
    assert trends_mod._parse_hot({}) == []


def test_fetch_platform_fallback(monkeypatch):
    calls = []

    def fake_get(url, timeout=8):
        calls.append(url)
        if "60s.viki.moe" in url:
            raise OSError("primary down")
        return {"data": [{"title": "backup-hit"}]}

    monkeypatch.setattr(trends_mod, "_http_get_json", fake_get)
    items = trends_mod._fetch_platform("weibo")
    assert items and items[0]["title"] == "backup-hit"
    assert len(calls) == 2  # primary 失败 → backup

    # 无 backup 的平台失败返回空
    monkeypatch.setattr(
        trends_mod, "_http_get_json", lambda url, timeout=8: (_ for _ in ()).throw(OSError())
    )
    assert trends_mod._fetch_platform("zhihu") == []


def test_trends_endpoint_cache(monkeypatch, client):
    trends_mod._TREND_CACHE.clear()
    monkeypatch.setattr(
        trends_mod,
        "_http_get_json",
        lambda url, timeout=8: {"data": [{"title": f"hot-{url.split('/')[-1]}", "hot": 1}]},
    )
    r = client.get("/api/trends", params={"platforms": "weibo,unknown,zhihu", "limit": 5})
    data = r.json()
    assert [t["platform"] for t in data["trends"]] == ["weibo", "zhihu"]  # 未知平台被过滤
    assert data["trends"][0]["label"] == "微博"
    assert len(data["trends"][0]["items"]) == 1
    # 缓存生效：第二次不再打网
    monkeypatch.setattr(
        trends_mod, "_http_get_json", lambda url, timeout=8: (_ for _ in ()).throw(OSError())
    )
    r2 = client.get("/api/trends", params={"platforms": "weibo"})
    assert r2.json()["trends"][0]["items"][0]["title"].startswith("hot-")
    # 缓存过期后源失效 → 回退旧缓存
    pf, (ts, items) = next(iter(trends_mod._TREND_CACHE.items()))
    trends_mod._TREND_CACHE[pf] = (ts - 400, items)
    r3 = client.get("/api/trends", params={"platforms": pf})
    assert r3.json()["trends"][0]["items"]  # 旧缓存兜底
    trends_mod._TREND_CACHE.clear()
