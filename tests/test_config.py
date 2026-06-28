from md_viewer.config import Config


def test_default_root(monkeypatch, tmp_path):
    monkeypatch.setenv("MDV_ROOT", str(tmp_path))
    cfg = Config.from_env()
    assert cfg.root == tmp_path.resolve()


def test_default_port(monkeypatch, tmp_path):
    monkeypatch.setenv("MDV_ROOT", str(tmp_path))
    monkeypatch.delenv("MDV_PORT", raising=False)
    cfg = Config.from_env()
    assert cfg.port == 8000


def test_custom_port(monkeypatch, tmp_path):
    monkeypatch.setenv("MDV_ROOT", str(tmp_path))
    monkeypatch.setenv("MDV_PORT", "9000")
    cfg = Config.from_env()
    assert cfg.port == 9000


def test_max_file_size_default(monkeypatch, tmp_path):
    monkeypatch.setenv("MDV_ROOT", str(tmp_path))
    cfg = Config.from_env()
    assert cfg.max_file_size == 5 * 1024 * 1024


def test_content_exts():
    assert ".md" in Config.content_exts
    assert ".markdown" in Config.content_exts
    assert ".mdx" in Config.content_exts


def test_image_exts():
    assert ".png" in Config.image_exts
    assert ".svg" in Config.image_exts
