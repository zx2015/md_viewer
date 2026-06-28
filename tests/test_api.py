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


def test_search_finds(client, sample_tree):
    r = client.get("/api/search?q=e")
    assert r.status_code == 200
    paths = [m["path"] for m in r.get_json()["matches"]]
    assert "/docs/sub/e.md" in paths


def test_search_empty_query(client, sample_tree):
    r = client.get("/api/search?q=")
    assert r.status_code == 200
    assert r.get_json()["matches"] == []


def test_search_limit_clamped(client, sample_tree):
    for i in range(5):
        (sample_tree / f"x{i}.md").write_text("")
    r = client.get("/api/search?q=x&limit=99999")
    assert r.status_code == 200
    # limit clamped to 200 server-side
    assert len(r.get_json()["matches"]) <= 200


def test_search_returns_size(client, sample_tree):
    (sample_tree / "sized.md").write_text("hello")
    r = client.get("/api/search?q=sized")
    matches = r.get_json()["matches"]
    assert len(matches) == 1
    assert "size" in matches[0]


def test_file_rendered(client, sample_tree):
    (sample_tree / "a.md").write_text("# Hi\nbody")
    r = client.get("/api/file?path=/a.md&format=rendered")
    assert r.status_code == 200
    data = r.get_json()
    assert "<h1" in data["html"]
    assert data["title"] == "Hi"
    assert data["meta"]["name"] == "a.md"


def test_file_raw(client, sample_tree):
    (sample_tree / "a.md").write_text("# Hi")
    r = client.get("/api/file?path=/a.md&format=raw")
    assert r.status_code == 200
    data = r.get_json()
    assert data["text"] == "# Hi"


def test_file_default_format_is_rendered(client, sample_tree):
    (sample_tree / "a.md").write_text("# Hi")
    r = client.get("/api/file?path=/a.md")
    assert r.status_code == 200
    assert "html" in r.get_json()


def test_file_too_large(client, sample_tree, monkeypatch):
    cfg_override = client.application.config["MDV_CONFIG"]
    from md_viewer.config import Config
    client.application.config["MDV_CONFIG"] = Config(
        root=cfg_override.root, max_file_size=10
    )
    (sample_tree / "big.md").write_text("x" * 100)
    r = client.get("/api/file?path=/big.md")
    assert r.status_code == 413


def test_file_extension_blocked(client, sample_tree):
    (sample_tree / "a.exe").write_text("nope")
    r = client.get("/api/file?path=/a.exe")
    assert r.status_code in (400, 403)


def test_file_path_traversal(client, sample_tree):
    r = client.get("/api/file?path=/../etc/passwd")
    assert r.status_code in (400, 403)


def test_file_encoding_reported(client, sample_tree):
    (sample_tree / "a.md").write_bytes("# Hi".encode("utf-8"))
    r = client.get("/api/file?path=/a.md&format=raw")
    assert r.get_json()["encoding"] == "utf-8"


def test_image_served(client, sample_tree):
    import base64
    # 1x1 transparent PNG
    png_bytes = base64.b64decode(
        b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    )
    (sample_tree / "assets").mkdir()
    (sample_tree / "assets" / "p.png").write_bytes(png_bytes)
    r = client.get("/api/image?path=/assets/p.png")
    assert r.status_code == 200
    assert r.content_type == "image/png"
    assert r.content_length == len(png_bytes)


def test_image_etag(client, sample_tree):
    (sample_tree / "a.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    r1 = client.get("/api/image?path=/a.png")
    etag = r1.headers.get("ETag")
    assert etag is not None
    r2 = client.get("/api/image?path=/a.png", headers={"If-None-Match": etag})
    assert r2.status_code == 304


def test_image_extension_blocked(client, sample_tree):
    (sample_tree / "x.exe").write_bytes(b"x")
    r = client.get("/api/image?path=/x.exe")
    assert r.status_code in (400, 403)


def test_image_path_traversal(client, sample_tree):
    r = client.get("/api/image?path=/../etc/passwd")
    assert r.status_code in (400, 403)
