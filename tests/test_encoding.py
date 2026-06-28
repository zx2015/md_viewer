from md_viewer.encoding import read_text_safe


def test_utf8(tmp_path):
    f = tmp_path / "a.md"
    f.write_bytes("你好 world".encode("utf-8"))
    text, enc = read_text_safe(f)
    assert text == "你好 world"
    assert enc == "utf-8"


def test_gb18030_fallback(tmp_path):
    f = tmp_path / "a.md"
    f.write_bytes("你好".encode("gb18030"))
    text, enc = read_text_safe(f)
    assert text == "你好"
    assert enc == "gb18030"


def test_latin1_fallback(tmp_path):
    f = tmp_path / "a.md"
    f.write_bytes(b"\xe9\xe8")  # invalid utf-8, valid latin-1 ('é','è')
    text, enc = read_text_safe(f)
    assert text == "éè"
    assert enc == "latin-1"


def test_full_byte_range(tmp_path):
    f = tmp_path / "a.md"
    f.write_bytes(bytes(range(256)))
    text, enc = read_text_safe(f)
    assert enc == "latin-1"
    assert len(text) == 256
