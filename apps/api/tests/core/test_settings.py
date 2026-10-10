"""运行时设置验收（web-pages-batch T1）。"""

import pytest

from zimeiti_api.core import settings


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    f = tmp_path / "settings.json"
    monkeypatch.setattr(settings, "settings_path", lambda: f)
    return f


def test_roundtrip(isolated):
    settings.update_settings({"notify_webhook_url": "https://hook"})
    assert settings.get_setting("notify_webhook_url") == "https://hook"
    assert settings.get_settings() == {"notify_webhook_url": "https://hook"}


def test_unknown_key_rejected(isolated):
    with pytest.raises(ValueError, match="未知设置项"):
        settings.update_settings({"evil": "x"})


def test_corrupt_file_fails_open_empty(isolated):
    isolated.write_text("{broken", encoding="utf-8")
    assert settings.get_settings() == {}


def test_missing_file_empty(isolated):
    assert settings.get_settings() == {}
    assert settings.get_setting("notify_webhook_url") == ""
