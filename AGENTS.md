# AGENTS.md — md-viewer

本文件是本项目专属的代理指引。**全局行为基线**（`.learnings/` 知识沉淀、`TODO.md` 维护、"内容递增原则"、用户偏好等）见：

- `~/.config/opencode/AGENTS.md`（已随 OpenCode 全局加载；本文件不重复，仅在必要时引用）

> 仓库当前为空目录（也尚未初始化为 git repo）。下面是基于技术选型写出的"骨架版"约定，随实现推进同步增量更新——只追加/合并，不删除既有有效内容（参见全局"内容递增原则"）。

## 项目目标

- 定位：本地 Markdown 文件查看工具，Python 实现。
- v1 范围：单文件渲染、目录树浏览、GFM 语法、代码高亮、本地 Web 服务 + CLI 双形态。
- 非目标（v1 不做）：所见即所得编辑、在线协作、云同步、用户系统。

## 技术栈

- 语言：Python 3.12（已通过 `/media/data/venv` 验证）
- Web 框架：**Flask**（已定，见 `docs/2026-06-28-md-viewer-design.md` §6）
- Markdown 渲染：`markdown-it-py` + `mdit-py-plugins`（已定）
- 代码高亮：`pygments`（已定）
- HTML 清洗：`nh3`（已定，用于 XSS 防护）
- 前端：原生 HTML + 少量 JS + 本地打包的 KaTeX / Mermaid（已定）
- 包管理：`pip` + `requirements.txt`（已定，v1 不引入 poetry/uv）
- 测试：`pytest`

## Python 环境

- **必须**使用全局虚拟环境 `/media/data/venv`（来自全局记忆）。本项目根目录不再建 venv。
- 若 `/media/data/venv` 不可用或版本不符，**先停下向用户确认**，不要降级到系统 Python。
- 常用解释器路径：`/media/data/venv/bin/python`；包安装：`/media/data/venv/bin/pip install ...`。
- 切勿 `pip install` 到系统 `/usr/bin/python`。

## 目录约定（落地后的事实标准）

```
.
├── AGENTS.md
├── README.md
├── requirements.txt
├── .gitignore                # 必含：.learnings/、.OpenCode/、__pycache__/、*.pyc、.venv/
├── .learnings/               # 本地知识库（不入 git，全局约定）
├── TODO.md                   # 任务跟踪（入 git，全局约定）
├── src/
│   └── md_viewer/
│       ├── __init__.py
│       ├── __main__.py       # python -m md_viewer 入口
│       ├── cli.py            # CLI 子命令
│       ├── server.py         # Web 应用工厂
│       ├── render.py         # markdown -> HTML 渲染
│       └── templates/        # Jinja2 模板
├── tests/
│   ├── test_render.py
│   ├── test_cli.py
│   └── test_server.py
└── samples/                  # 渲染回归用 .md 样本
```

源码一律落 `src/md_viewer/`，测试一律落 `tests/`，**不要**在根目录散落 `.py` 脚本或 `app.py`。

## 命令（v1 计划；实际命令随实现微调）

| 用途 | 命令 |
|------|------|
| 安装依赖 | `/media/data/venv/bin/pip install -r requirements.txt` |
| 启动 Web 服务 | `/media/data/venv/bin/python -m md_viewer serve --root <dir>` |
| 启动 Web 服务（热重载） | `/media/data/venv/bin/python -m md_viewer serve --root <dir> --reload` |
| CLI 渲染到 stdout | `/media/data/venv/bin/python -m md_viewer render <file.md>` |
| CLI 导出 HTML | `/media/data/venv/bin/python -m md_viewer export <file.md> -o out.html` |
| 运行全部测试 | `/media/data/venv/bin/pytest` |
| 运行单个测试 | `/media/data/venv/bin/pytest tests/test_render.py::test_gfm_table -v` |
| Lint（如引入 ruff） | `/media/data/venv/bin/ruff check src tests` |
| 格式化（如引入 black） | `/media/data/venv/bin/black src tests` |

> 命令尚未落地，标注为"计划"。首次实现时若与上表冲突，**以实际代码为准**并增量回写本表。

## 工作流约定

- **新功能/修行为前**：先在 `TODO.md` 追加条目，再动手。
- **修改后验证顺序**：`lint → test → 手动 smoke（启服务打开 samples/ 下的 .md）`。
- **依赖变更**：同步更新 `requirements.txt` 与本文件"技术栈"段落。
- **首次 git 初始化**：在 `git init` 前先创建 `.gitignore`（含 `.learnings/`、`.OpenCode/`、`__pycache__/`、`*.pyc`），再 `git add`——遵循全局"知识库不纳入版本控制"硬性要求。

## 渲染与安全要点（Markdown 查看器常见坑）

- **XSS**：渲染外部 .md 时，**默认关闭内联 HTML**（`markdown-it-py` 的 `html: False`）。需要富 HTML 时另开白名单模式并加测试。
- **路径穿越**：用户提供的相对路径必须 `Path(...).resolve()` 后再校验是否在白名单根目录内，禁止把 `..` 透传给文件系统。
- **大文件**：单文件 > 1 MB 不要一次性 `read()`，分块读取并显示进度，避免 Web 服务卡死。
- **编码**：默认 `utf-8`；若检测到 BOM 改用 `utf-8-sig`。
- **目录列表**：列出目录内容时按 `Path.iterdir()` 排序，目录优先于文件，避免抖动。

## 待定项（落地前补齐，首次实现后转为已定项）

- [x] ~~Web 框架最终选 Flask 还是 FastAPI~~ → **Flask**（见 `docs/2026-06-28-md-viewer-design.md`）
- [x] ~~是否引入 `pygments`~~ → 是
- [x] ~~是否引入 `markdown-it-py`~~ → 是
- [ ] CLI 参数库：`argparse`（标准库，零依赖） / `click` / `typer`
- [ ] Lint/Format 工具：`ruff`（一站式，推荐） / `flake8 + black + isort`
- [ ] 是否需要目录监听（`watchfiles`）实现热重载
