"""Task 1.4 RED：/health 端点尚未实现，测试应失败。"""


def test_health_returns_ok():
    from fastapi.testclient import TestClient

    from zimeiti_api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
