def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.get_json()
    # Lightweight liveness probe — must be cheap and must not leak
    # internal state (root path, file count).
    assert data == {"status": "ok"}


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


def test_file_markdown_relative_links_use_current_file_directory(client, sample_tree):
    docs = sample_tree / "docs" / "requirements"
    docs.mkdir(parents=True)
    (docs / "00-overview.md").write_text("[open](09-open-questions.md)")
    (docs / "09-open-questions.md").write_text("# q")

    r = client.get("/api/file?path=/docs/requirements/00-overview.md&format=rendered")
    assert r.status_code == 200
    data = r.get_json()
    assert 'href="/api/file?path=/docs/requirements/09-open-questions.md"' in data["html"]


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


# === render_viewable dispatch (v2) ===

def test_api_file_python_returns_kind_code(client, sample_tree):
    from pathlib import Path
    Path(sample_tree, "a.py").write_text("def f():\n    return 1\n")
    r = client.get(f"/api/file?path=/a.py&format=rendered")
    assert r.status_code == 200
    data = r.get_json()
    assert data["kind"] == "code"
    assert "<pre" in data["html"]


def test_api_file_json_valid(client, sample_tree):
    from pathlib import Path
    Path(sample_tree, "a.json").write_text('{"x": 1}\n')
    r = client.get("/api/file?path=/a.json&format=rendered")
    assert r.status_code == 200
    data = r.get_json()
    assert data["kind"] == "code"
    assert data["json_valid"] is True


def test_api_file_json_invalid(client, sample_tree):
    from pathlib import Path
    Path(sample_tree, "bad.json").write_text("{not valid}\n")
    r = client.get("/api/file?path=/bad.json&format=rendered")
    assert r.status_code == 200
    data = r.get_json()
    assert data["kind"] == "code-error"
    assert data["json_valid"] is False
    assert data["error"]


def test_api_file_html_default_is_sandbox(client, sample_tree):
    from pathlib import Path
    Path(sample_tree, "page.html").write_text("<h1>Hi</h1>")
    r = client.get("/api/file?path=/page.html&format=rendered")
    assert r.status_code == 200
    data = r.get_json()
    assert data["kind"] == "html"
    assert "<iframe" in data["html"]
    assert data["raw"] == "<h1>Hi</h1>"


def test_api_file_html_raw_returns_source(client, sample_tree):
    from pathlib import Path
    Path(sample_tree, "page.html").write_text("<h1>Hi</h1>")
    r = client.get("/api/file?path=/page.html&format=raw")
    assert r.status_code == 200
    data = r.get_json()
    assert data["kind"] == "html"
    assert data["raw"] == "<h1>Hi</h1>"
    # When raw is requested for html, the response uses the highlighted source
    assert "<pre" in data["html"]


def test_api_file_python_raw_same_as_rendered(client, sample_tree):
    from pathlib import Path
    Path(sample_tree, "a.py").write_text("x = 1\n")
    rendered = client.get("/api/file?path=/a.py&format=rendered").get_json()
    raw = client.get("/api/file?path=/a.py&format=raw").get_json()
    # For code files, both formats return the highlighted code
    assert raw["kind"] == "code"
    assert rendered["html"] == raw["html"]


# === Pygments CSS endpoint ===

def test_api_code_style_light(client):
    r = client.get("/api/code-style?theme=light")
    assert r.status_code == 200
    assert r.content_type.startswith("text/css")
    css = r.get_data(as_text=True)
    assert css
    # Pygments wraps output in <div class="highlight">, so scope targets .highlight
    assert ".content .highlight" in css


def test_api_code_style_dark(client):
    r = client.get("/api/code-style?theme=dark")
    assert r.status_code == 200
    css = r.get_data(as_text=True)
    assert css
    # monokai has a distinctive background color near #272822
    assert "272822" in css or ".content .highlight" in css


def test_api_code_style_defaults_to_light(client):
    r = client.get("/api/code-style")
    assert r.status_code == 200
    css = r.get_data(as_text=True)
    assert css


def test_api_code_style_invalid_theme_falls_back_to_light(client):
    r = client.get("/api/code-style?theme=banana")
    assert r.status_code == 200
    css = r.get_data(as_text=True)
    assert css
