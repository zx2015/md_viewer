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


def test_mermaid_block_preserved():
    md = "```mermaid\ngraph TD; A-->B;\n```"
    r = render_markdown(md)
    assert 'class="mermaid"' in r["html"]
    assert "graph TD" in r["html"]
    assert "<pre" in r["html"]


def test_mermaid_not_sanitized_away():
    # make sure mermaid pre tag survives nh3
    md = "```mermaid\ngraph LR; X-->Y;\n```"
    r = render_markdown(md)
    # if mermaid pre is stripped, the content would be missing or replaced
    assert "graph LR" in r["html"]
    assert "X" in r["html"] and "Y" in r["html"]


# === render_viewable dispatcher ===

from md_viewer.render import render_viewable


def test_render_viewable_python():
    r = render_viewable("hello.py", "def f():\n    return 1\n")
    assert r["kind"] == "code"
    assert r["toc"] == []
    # Pygments token classes are present
    assert "<span" in r["html"]
    # Wrapped in a content <pre>
    assert "<pre" in r["html"]


def test_render_viewable_json_valid():
    r = render_viewable("a.json", '{"x": 1, "y": [1,2]}\n')
    assert r["kind"] == "code"
    assert r["json_valid"] is True
    assert "<pre" in r["html"]


def test_render_viewable_json_invalid_still_highlights():
    r = render_viewable("a.json", "{x: not valid}\n")
    assert r["kind"] == "code-error"
    assert r["json_valid"] is False
    assert "error" in r and r["error"]
    # Source still shown
    assert "<pre" in r["html"]


def test_render_viewable_html_sandbox_preview():
    src = "<!doctype html><html><body><h1>Hi</h1></body></html>"
    r = render_viewable("page.html", src)
    assert r["kind"] == "html"
    # Front-end will receive an <iframe srcdoc=...> fragment
    assert "<iframe" in r["html"]
    assert 'sandbox=""' in r["html"]
    assert "srcdoc=" in r["html"]
    # Raw source kept for "Source" toggle
    assert r.get("raw") == src


def test_render_viewable_md_delegates():
    r = render_viewable("a.md", "# Title\n\nbody\n")
    assert r["kind"] == "markdown"
    assert r["title"] == "Title"
    assert "<h1" in r["html"]


# === Pygments CSS provider ===

def test_pygments_css_light_nonempty():
    from md_viewer.render import get_pygments_css
    css = get_pygments_css("light")
    assert css
    # Should include token class selectors
    assert ".kn" in css or ".k" in css or ".highlight" in css


def test_pygments_css_dark_nonempty():
    from md_viewer.render import get_pygments_css
    css = get_pygments_css("dark")
    assert css
    assert ".kn" in css or ".k" in css or ".highlight" in css


def test_pygments_css_dark_differs_from_light():
    from md_viewer.render import get_pygments_css
    light = get_pygments_css("light")
    dark = get_pygments_css("dark")
    # The two themes should produce different color values
    assert light != dark


# === Regression: double-escape bug ===
# Prior version passed pre-escaped text to Pygments, which caused
# ``"`` → ``&quot;`` → ``&amp;quot;`` and similar double-escapes.
# See render.py `_highlight` / `_render_fence` / `_render_code_view`.

def test_render_viewable_python_no_double_escape_in_docstring():
    src = '"""Triple-quoted docstring with "quotes" inside."""\n'
    r = render_viewable("a.py", src)
    # Bug would render &quot; as &amp;quot;
    assert "&amp;quot;" not in r["html"], f"double-escape detected: {r['html']!r}"
    # And the resulting text should contain a properly-escaped &quot; (single escape)
    assert "&quot;" in r["html"]


def test_render_viewable_python_ampersand_not_double_escaped():
    src = "x = a & b\n"  # a single '&' in source
    r = render_viewable("a.py", src)
    assert "&amp;amp;" not in r["html"], f"double-escape detected: {r['html']!r}"
    assert "&amp;" in r["html"]


def test_markdown_fence_python_no_double_escape():
    from md_viewer.render import render_markdown
    md = '```python\n"""Doc with "quotes".""\"\n```\n'
    r = render_markdown(md)
    # The bug rendered &quot; as &amp;quot;
    assert "&amp;quot;" not in r["html"], f"double-escape detected: {r['html']!r}"
    # Either a properly-escaped &quot; or the raw character inside a span is fine —
    # what matters is no double-escape, and that the original text is preserved.
    assert "Doc with" in r["html"]
    assert "quotes" in r["html"]
