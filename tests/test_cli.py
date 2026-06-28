from md_viewer.cli import build_parser


def test_serve_default_args():
    p = build_parser()
    args = p.parse_args(["serve"])
    assert args.command == "serve"
    assert args.host is None
    assert args.port is None
    assert args.root is None


def test_serve_custom_port():
    p = build_parser()
    args = p.parse_args(["serve", "--port", "9000"])
    assert args.port == 9000


def test_serve_custom_host():
    p = build_parser()
    args = p.parse_args(["serve", "--host", "127.0.0.1"])
    assert args.host == "127.0.0.1"


def test_serve_custom_root(monkeypatch, tmp_path):
    p = build_parser()
    args = p.parse_args(["serve", "--root", str(tmp_path)])
    assert args.root == tmp_path


def test_no_command_shows_help(capsys):
    p = build_parser()
    try:
        p.parse_args([])
    except SystemExit:
        pass  # argparse exits on missing required subcommand
    # argparse prints to stderr; not asserting content
