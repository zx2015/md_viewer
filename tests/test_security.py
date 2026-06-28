import pytest

from md_viewer.security import (
    resolve_safe,
    check_extension,
    PathError,
    ExtensionError,
)


def test_resolve_safe_relative(tmp_path):
    (tmp_path / "a.md").write_text("x")
    p = resolve_safe("/a.md", tmp_path)
    assert p == (tmp_path / "a.md").resolve()


def test_resolve_safe_without_leading_slash(tmp_path):
    (tmp_path / "a.md").write_text("x")
    p = resolve_safe("a.md", tmp_path)
    assert p == (tmp_path / "a.md").resolve()


def test_resolve_safe_blocks_parent_escape(tmp_path):
    outside = tmp_path.parent / "secret.md"
    outside.write_text("secret")
    with pytest.raises(PathError):
        resolve_safe(f"../{outside.name}", tmp_path)


def test_resolve_safe_blocks_dotdot_in_middle(tmp_path):
    (tmp_path / "sub").mkdir()
    with pytest.raises(PathError):
        resolve_safe("/sub/../../escape", tmp_path)


def test_resolve_safe_empty_path(tmp_path):
    with pytest.raises(PathError):
        resolve_safe("", tmp_path)


def test_check_extension_allowed(tmp_path):
    f = tmp_path / "a.md"
    f.write_text("")
    check_extension(f, {".md", ".markdown"})


def test_check_extension_rejected(tmp_path):
    f = tmp_path / "a.exe"
    f.write_text("")
    with pytest.raises(ExtensionError):
        check_extension(f, {".md"})


def test_check_extension_case_insensitive(tmp_path):
    f = tmp_path / "A.MD"
    f.write_text("")
    check_extension(f, {".md"})
