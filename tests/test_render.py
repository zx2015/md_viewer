from md_viewer.render import render_markdown


def test_basic_paragraph():
    r = render_markdown("hello world")
    assert "<p>hello world</p>" in r["html"]


def test_h1_has_id():
    r = render_markdown("# Title")
    assert '<h1 id="title">Title</h1>' in r["html"]


def test_h2_has_id():
    r = render_markdown("## Sub")
    assert '<h2 id="sub">Sub</h2>' in r["html"]


def test_emphasis():
    r = render_markdown("**bold** *italic*")
    assert "<strong>bold</strong>" in r["html"]
    assert "<em>italic</em>" in r["html"]


def test_code_inline():
    r = render_markdown("`code`")
    assert "<code>code</code>" in r["html"]


def test_returns_required_keys():
    r = render_markdown("# X\nbody")
    assert "html" in r
    assert "toc" in r
    assert "title" in r
    assert isinstance(r["toc"], list)


def test_title_from_first_h1():
    r = render_markdown("# First\n## Second\n# Third")
    assert r["title"] == "First"


def test_toc_includes_levels_1_to_3():
    r = render_markdown("# H1\n## H2\n### H3\n#### H4")
    assert len(r["toc"]) == 3
    levels = [t["level"] for t in r["toc"]]
    assert levels == [1, 2, 3]


def test_gfm_table():
    md = "| a | b |\n|---|---|\n| 1 | 2 |"
    r = render_markdown(md)
    assert "<table>" in r["html"]
    assert "<td>1</td>" in r["html"]


def test_gfm_task_checked():
    md = "- [x] done\n- [ ] todo"
    r = render_markdown(md)
    assert 'type="checkbox"' in r["html"]
    assert "checked" in r["html"]


def test_gfm_strikethrough():
    r = render_markdown("~~gone~~")
    assert "<s>gone</s>" in r["html"]


def test_gfm_autolink():
    r = render_markdown("Visit https://example.com today")
    assert '<a href="https://example.com"' in r["html"]


def test_gfm_task_uses_tasklists_class():
    md = "- [x] done"
    r = render_markdown(md)
    # tasklists plugin emits a checkbox + class
    assert 'type="checkbox"' in r["html"]
    assert "task-list-item" in r["html"]


def test_wikilink_basic():
    r = render_markdown("see [[Other]] for more")
    assert 'href="/api/file?path=/Other.md' in r["html"]
    assert ">Other</a>" in r["html"]


def test_wikilink_with_alias():
    r = render_markdown("see [[Other|display text]] here")
    assert ">display text</a>" in r["html"]
    assert 'href="/api/file?path=/Other.md' in r["html"]


def test_wikilink_explicit_md():
    r = render_markdown("see [[other.md]] here")
    assert 'href="/api/file?path=/other.md' in r["html"]


def test_wikilink_inside_paragraph():
    r = render_markdown("text [[Note]] more text")
    assert "<p>" in r["html"]
    assert "/api/file?path=/Note.md" in r["html"]


def test_wikilink_in_heading():
    r = render_markdown("# Title [[Link]]")
    assert "/api/file?path=/Link.md" in r["html"]


def test_code_block_highlighted():
    md = "```python\ndef f():\n    pass\n```"
    r = render_markdown(md)
    assert "<pre" in r["html"]
    assert "<code" in r["html"]
    assert "python" in r["html"]


def test_code_block_copyable_class():
    md = "```\nplain\n```"
    r = render_markdown(md)
    # we add a class to make the JS code-copy button able to find it
    assert "copyable-code" in r["html"]


def test_script_tag_stripped():
    md = "<script>alert(1)</script>"
    r = render_markdown(md)
    assert "<script>" not in r["html"]
    assert "alert" not in r["html"]


def test_img_preserved_with_safe_attrs():
    md = '<img src="x.png" alt="a" onerror="bad()">'
    r = render_markdown(md)
    assert "<img" in r["html"]
    assert 'src="x.png"' in r["html"]
    # onerror handler should be stripped
    assert "onerror" not in r["html"]


def test_external_link_gets_rel_and_target():
    md = "[g](https://example.com)"
    r = render_markdown(md)
    assert 'target="_blank"' in r["html"]
    assert 'rel="noopener noreferrer"' in r["html"]  
