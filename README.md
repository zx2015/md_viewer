# md-viewer

一个轻量、本地、单用户的 Markdown 阅读器，以 Docker 容器方式运行，
挂载只读卷即可直接浏览你的笔记库。

- 文件树（懒加载）+ 文件名搜索
- GFM 渲染（表格、任务列表、删除线、自动链接）
- Wikilinks `[[name]]` 与 `[[name|alias]]`
- 代码块语法高亮 + 复制按钮
- 图片渲染 + 加载失败占位
- 右侧 TOC + 滚动联动高亮
- 浅色 / 深色 / 跟随系统 三套主题
- 本地图片代理（只读挂载）
- HTML 清洗（nh3）— 防 XSS
- **侧栏顶部刷新按钮（`Ctrl+Shift+R` / `F5`）**：重新拉取文件树并重载当前文件
- **自动展开到当前文件**：刷新页面 / J-K 跳转 / 打开新文件时，文件树自动展开到目标位置
- **`.py` / `.json` / `.html` 文件支持**：源码高亮（`.py`/`.json`）、JSON 校验提示、HTML 沙盒预览（`<iframe sandbox>`）+ 源码切换

## 快速开始（Docker）

```bash
docker run -d --name md-viewer -p 8000:8000 \
  -v /path/to/your/notes:/data:ro \
  md-viewer:latest
```

浏览器访问 http://localhost:8000。

> 先构建镜像：`docker build -t md-viewer:latest .`
> 或使用 compose：编辑 `docker-compose.yml` 指向你的笔记路径，再 `docker compose up -d`。

挂载目录**必须是只读**（`:ro`）。应用同时对所有路径做白名单校验，阻止 `../` 越权。

## 快速开始（开发模式，不使用 Docker）

```bash
# 使用共享虚拟环境
/media/data/venv/bin/pip install -e ".[dev]"

# 启动服务并以本地 samples 作为根目录
MDV_ROOT=./samples /media/data/venv/bin/python -m md_viewer serve

# 运行测试
/media/data/venv/bin/pytest
```

## 配置

所有配置通过环境变量（或 `--root`、`--port`、`--host` 参数）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MDV_ROOT` | `/data` | 要服务的目录 |
| `MDV_HOST` | `0.0.0.0` | 绑定主机 |
| `MDV_PORT` | `8000` | 绑定端口 |
| `MDV_MAX_FILE_SIZE` | `5242880`（5 MB） | 单文件大小上限（字节） |

CLI 用法：`python -m md_viewer serve --root ~/notes --port 9000`。

## 支持的文件类型

| 扩展名 | 渲染方式 |
|--------|----------|
| `.md` / `.markdown` / `.mdx` | Markdown 完整渲染（GFM + 任务列表 + 删除线 + 自动链接）+ Wikilinks + TOC |
| `.py` | Pygments Python 语法高亮的源码；不可"切换 Raw" |
| `.json` | Pygments JSON 语法高亮；JSON 语法错误时顶部显示警告条，仍展示源码 |
| `.html` / `.htm` | 默认 `<iframe sandbox="" srcdoc=...>` 沙盒预览（无脚本权限），点击顶栏 `Source` 切换到高亮源码 |
| `.png` / `.jpg` / `.jpeg` / `.gif` / `.webp` / `.svg` | 本地图片代理，ETag 条件请求，加载失败显示占位 |

其他扩展名的文件**不会**出现在文件树中（白名单过滤）。

## 键盘快捷键

| 按键 | 动作 |
|------|------|
| `J` / `K` | 上一/下一个 `.md`（自动展开到目标目录） |
| `Alt+↓` / `Alt+↑` | 同上（备选键位） |
| `Ctrl+K` | 聚焦搜索框 |
| `Ctrl+B` | 切换侧栏可见性 |
| `Ctrl+Shift+L` | 切换主题（auto → dark → light） |
| `Ctrl+R` | 重新加载当前打开的文件（**不**刷新文件树） |
| `Ctrl+Shift+R` / `F5` | **刷新文件树 + 重新加载当前文件** |
| `R` | Markdown 文件：切换 Raw / Rendered；HTML 文件：切换 Preview / Source；代码文件：无操作 |
| `Esc` | 清空搜索 / 失焦输入框 |

## 主题与代码高亮

- 三套主题：浅色 / 深色 / 跟随系统。状态持久化到 `localStorage`。
- 代码高亮（`.py` / `.json` / `.html` 源码 + Markdown 围栏代码块）由 Pygments 提供：
  - 浅色主题：`default` 配色
  - 深色主题：`monokai` 配色
- 主题切换时自动重新加载对应的 Pygments CSS（通过 `GET /api/code-style?theme=light|dark`）。

## 架构

```
浏览器 (vanilla JS)
   ↕ HTTP (JSON + 图片)
Flask（单进程）
   ↕ 只读系统调用
挂载目录 (/data)
```

- 后端：Flask 3 + markdown-it-py + nh3（XSS 清洗）+ pygments
- 前端：零构建 vanilla JS + CSS 变量做主题切换
- 安全：路径白名单 + 扩展名白名单 + HTML 清洗 + 只读挂载（纵深防御）

完整设计见 [`docs/2026-06-28-md-viewer-design.md`](docs/2026-06-28-md-viewer-design.md)，
实现计划见 [`docs/2026-06-28-md-viewer-impl-plan.md`](docs/2026-06-28-md-viewer-impl-plan.md)。
v2 增量特性设计见 [`docs/superpowers/specs/2026-07-06-md-viewer-v2-features-design.md`](docs/superpowers/specs/2026-07-06-md-viewer-v2-features-design.md)。

## 项目结构

```
src/md_viewer/
  __init__.py      包标记
  __main__.py      python -m md_viewer 入口
  cli.py           argparse 子命令
  config.py        基于环境变量的 Config dataclass
  security.py      路径 / 扩展名校验
  encoding.py      UTF-8 → GB18030 → latin-1 编码回退
  tree.py          目录列表 + 文件名搜索
  render.py        markdown → HTML（含 .py/.json/.html 多格式分发）
  server.py        Flask app factory
  api.py           /api/* 路由（tree/children/search/file/image/health/code-style）
  templates/       Jinja2 模板
  static/          CSS、JS
tests/             pytest
samples/           .md / .py / .json / .html 样本
docs/              设计 + 实现计划 + 增量规格
```

## 测试

```bash
# 全部测试
/media/data/venv/bin/pytest

# 单个文件
/media/data/venv/bin/pytest tests/test_render.py -v

# 按关键字过滤
/media/data/venv/bin/pytest -k "double_escape" -v
```

当前状态：**109 / 109 通过**。

## 版本范围

**v1（在范围内）**：文件树、文件名搜索、Markdown 渲染（GFM + Wikilinks + TOC）、主题、图片代理、代码高亮、HTML 清洗、多格式文件支持、文件树刷新、自动展开。

**已 deferred（不在范围内）**：全文搜索、标签 / 分类聚合、反向链接、移动端布局、HTTPS、编辑 / 预览所见即所得、多卷合并挂载。