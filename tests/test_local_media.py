from __future__ import annotations

from pathlib import Path

from aion import local_media


def test_camera_inventory_is_read_only(monkeypatch, tmp_path):
    fake_sysfs = tmp_path / "video4linux"
    video0 = fake_sysfs / "video0"
    video0.mkdir(parents=True)
    (video0 / "name").write_text("Test Camera\n", encoding="utf-8")

    real_glob = Path.glob

    def fake_glob(self: Path, pattern: str):
        if str(self) == "/sys/class/video4linux" and pattern == "video*":
            return iter([video0])
        return real_glob(self, pattern)

    monkeypatch.setattr(Path, "glob", fake_glob)

    data = local_media.camera_inventory()

    assert data["kind"] == "camera"
    assert data["capture_enabled"] is False
    assert data["count"] == 1
    assert data["devices"][0]["name"] == "Test Camera"


def test_audio_inventory_reports_sources_without_capture(monkeypatch):
    monkeypatch.setattr(
        local_media,
        "_pactl_sources",
        lambda: ([{"id": "1", "name": "test-source"}], None),
    )
    monkeypatch.setattr(local_media.shutil, "which", lambda _name: None)

    data = local_media.audio_inventory()

    assert data["kind"] == "audio-input"
    assert data["capture_enabled"] is False
    assert data["count"] == 1
    assert data["sources"][0]["name"] == "test-source"


def test_inventory_rejects_unknown_kind():
    try:
        local_media.inventory("screen")
    except ValueError as exc:
        assert "camera" in str(exc)
        assert "audio" in str(exc)
    else:
        raise AssertionError("unknown media kind should fail closed")
