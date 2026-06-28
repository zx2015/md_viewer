import pytest

from md_viewer.config import Config
from md_viewer.server import create_app


@pytest.fixture
def cfg(tmp_path):
    return Config(root=tmp_path.resolve())


@pytest.fixture
def sample_tree(tmp_path):
    """Build a small directory tree:

    /a.md
    /b.txt          (non-content, not listed)
    /docs/c.md
    /docs/d.md
    /docs/sub/e.md
    /empty/         (empty dir)
    """
    (tmp_path / "a.md").write_text("")
    (tmp_path / "b.txt").write_text("")
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "c.md").write_text("")
    (docs / "d.md").write_text("")
    sub = docs / "sub"
    sub.mkdir()
    (sub / "e.md").write_text("")
    (tmp_path / "empty").mkdir()
    return tmp_path


@pytest.fixture
def root_path(sample_tree):
    return sample_tree.resolve()


@pytest.fixture
def app(sample_tree, monkeypatch):
    monkeypatch.setenv("MDV_ROOT", str(sample_tree.resolve()))
    return create_app(Config(root=sample_tree.resolve()))


@pytest.fixture
def client(app):
    return app.test_client()
