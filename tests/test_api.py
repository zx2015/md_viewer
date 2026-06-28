def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "ok"
    assert "root" in data
    assert "md_count" in data


def test_tree_root(client, sample_tree):
    r = client.get("/api/tree")
    assert r.status_code == 200
    data = r.get_json()
    assert data["type"] == "dir"
    names = [c["name"] for c in data["children"]]
    assert "a.md" in names
    assert "docs" in names


def test_children_valid(client, sample_tree):
    r = client.get("/api/children?path=/docs")
    assert r.status_code == 200
    data = r.get_json()
    names = [c["name"] for c in data["children"]]
    assert "c.md" in names
    assert "sub" in names


def test_children_blocks_path_traversal(client, sample_tree):
    r = client.get("/api/children?path=/../etc")
    assert r.status_code in (400, 403)


def test_children_missing_dir(client, sample_tree):
    r = client.get("/api/children?path=/nope")
    assert r.status_code == 404


def test_tree_root_includes_size(client, sample_tree):
    r = client.get("/api/tree")
    data = r.get_json()
    a = next(c for c in data["children"] if c["name"] == "a.md")
    assert "size" in a
    assert a["size"] == 0  # file was written empty
