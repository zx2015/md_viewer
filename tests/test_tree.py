import pytest

from md_viewer.tree import list_children, search, to_api_path


def test_to_api_path_root(root_path):
    assert to_api_path(root_path, root_path) == "/"


def test_to_api_path_subdir(root_path):
    sub = root_path / "docs"
    assert to_api_path(sub, root_path) == "/docs"


def test_list_children_root(sample_tree, cfg):
    node = list_children("/", cfg)
    assert node["path"] == "/"
    assert node["type"] == "dir"
    names = [c["name"] for c in node["children"]]
    assert "a.md" in names
    assert "b.txt" not in names
    assert "docs" in names
    assert "empty" in names


def test_list_children_dirs_first(sample_tree, cfg):
    node = list_children("/", cfg)
    types = [c["type"] for c in node["children"]]
    dir_indices = [i for i, t in enumerate(types) if t == "dir"]
    file_indices = [i for i, t in enumerate(types) if t == "file"]
    if dir_indices and file_indices:
        assert max(dir_indices) < min(file_indices)


def test_list_children_alphabetical_within_type(sample_tree, cfg):
    node = list_children("/", cfg)
    files = [c["name"] for c in node["children"] if c["type"] == "file"]
    assert files == sorted(files, key=str.lower)


def test_list_children_subdir(sample_tree, cfg):
    node = list_children("/docs", cfg)
    names = [c["name"] for c in node["children"]]
    # dirs first, then files alphabetical
    assert names == ["sub", "c.md", "d.md"]


def test_list_children_has_children(sample_tree, cfg):
    node = list_children("/", cfg)
    docs = next(c for c in node["children"] if c["name"] == "docs")
    assert docs["has_children"] is True
    assert docs["child_count"] == 3


def test_list_children_empty_dir_has_no_children(sample_tree, cfg):
    node = list_children("/", cfg)
    empty = next(c for c in node["children"] if c["name"] == "empty")
    assert empty["has_children"] is False
    assert empty["child_count"] == 0


def test_list_children_missing_dir_raises(sample_tree, cfg):
    with pytest.raises(FileNotFoundError):
        list_children("/nope", cfg)


# ===== search =====


def test_search_no_match(sample_tree, cfg):
    assert search("readme", cfg) == []


def test_search_finds_file(sample_tree, cfg):
    paths = [r["path"] for r in search("a", cfg)]
    assert "/a.md" in paths


def test_search_case_insensitive(sample_tree, cfg):
    paths = [r["path"] for r in search("A.MD", cfg)]
    assert "/a.md" in paths


def test_search_recursive(sample_tree, cfg):
    paths = [r["path"] for r in search("e", cfg)]
    assert "/docs/sub/e.md" in paths


def test_search_excludes_non_content(sample_tree, cfg):
    assert search("b", cfg) == []


def test_search_limit(sample_tree, cfg):
    for i in range(5):
        (sample_tree / f"x{i}.md").write_text("")
    assert len(search("x", cfg, limit=2)) == 2


def test_search_relevance(sample_tree, cfg):
    (sample_tree / "notes.md").write_text("")
    (sample_tree / "notes-extra.md").write_text("")
    results = search("notes.md", cfg)
    assert results[0]["name"] == "notes.md"


def test_list_children_includes_python_files(sample_tree, cfg):
    from pathlib import Path
    Path(sample_tree, "script.py").write_text("x = 1\n")
    node = list_children("/", cfg)
    names = [c["name"] for c in node["children"]]
    assert "script.py" in names
    py = next(c for c in node["children"] if c["name"] == "script.py")
    assert py["type"] == "file"


def test_search_finds_python_file(sample_tree, cfg):
    from pathlib import Path
    Path(sample_tree, "script.py").write_text("x = 1\n")
    paths = [r["path"] for r in search("script", cfg)]
    assert "/script.py" in paths
