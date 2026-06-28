# md-viewer 设计文档

> 日期：2026-06-28
> 状态：草案 v1（待用户审阅）

## 1. 概述

**项目目标**：在 Docker 容器中运行一个轻量、本地、个人使用的 Markdown 浏览服务。把任意目录（read-only 挂载）暴露为可在桌面浏览器中浏览的 Web 应用。

**v1 范围**：单用户、桌面浏览器、只读观看、不做编辑、不做协作。

## 2. 使用场景

| 场景 | 描述 |
|------|------|
| S1 — 个人知识库浏览 | 本地存有大量笔记（Obsidian/Logseq 风格），需快速翻阅、跳转 |
| S2 — 项目文档查阅 | 临时 clone 了一个 GitHub repo 的 docs 目录，不想装 IDE，只想顺着目录树看 |
| S3 — 离线阅读 | 无网/弱网环境，容器内启动即用 |

**非场景**（v1 不做）：多用户/权限隔离、在线编辑、协同、移动端、全文搜索。

## 3. 功能需求

### 3.1 核心

| # | 需求 |
|---|------|
| F1 | 容器化部署：单镜像 `python:3.12-slim`，单进程，监听 8000 端口 |
| F2 | 只读挂载：`-v <host_path>:/data:ro`；应用运行时禁止任何写操作 |
| F3 | 文件树懒加载：根节点响应只含一层；展开文件夹时调 `/api/children` |
| F4 | 文件名过滤：顶部搜索框，键入时 debounce（300ms）调 `/api/search`，返回排序后的命中列表 |
| F5 | 文件树折叠/隐藏：工具栏"全部折叠/全部展开"；侧栏隐藏按钮 |
| F6 | Markdown 渲染：默认渲染；支持 GFM（表格/任务列表/自动链接）、YAML frontmatter（按 markdown 文本渲染，不特别处理）、代码块语法高亮 |
| F7 | Raw/Rendered 切换：顶部按钮；默认渲染；切到 raw 显示源代码（带语法高亮） |
| F8 | 右侧 TOC：从 H1-H3 自动生成；点击平滑滚动；滚动时高亮当前标题 |
| F9 | 上下文件快捷键：`J`/`K` 在"全局所有 .md 按路径字典序"序列中跳到上/下一个；不影响文件树本身的展开状态 |
| F10 | 主题：Light/Dark/跟随系统；持久化到 localStorage |
| F11 | 状态持久化：选中文件路径、侧栏可见性、侧栏宽度、主题存 localStorage；刷新后恢复 |
| F12 | 跨文件链接：拦截 `<a href="*.md">`，SPA 内部跳转，不刷新页面 |
| F13 | 本地图片：`![alt](image.png)` 走 `/api/image?path=...` 代理；带 ETag；加载失败显示占位 |
| F14 | Wikilinks：`[[note]]` 与 `[[path\|alias]]` 渲染为内部链接；解析规则：大小写不敏感；`note` 不带 `.md` 后缀时自动补 `.md`；先在当前目录查找，再回退到根目录；未命中渲染为带删除线的灰色死链 |
| F15 | 代码块复制按钮：每个 fenced code 块右上角出现 "Copy" 按钮，点击复制内容到剪贴板 |
| F16 | Deep link：`?p=/path/to/file.md` 直接打开指定文件（不带则用 localStorage 中上次选择的） |
| F17 | 手动刷新：`Ctrl+R` 重新拉取当前文件内容（外部编辑器修改后可即时查看） |
| F18 | 编码容错：UTF-8 → 失败回退 GB18030 → 仍失败回退 latin-1；均失败返回错误 |
| F19 | 文件元信息显示：主区顶部一行小字，显示文件名、大小（人类可读）、修改时间（本地时区 `YYYY-MM-DD HH:MM`） |
| F20 | 显示全部文件（包括 `.` 开头）：不做默认过滤；点文件由用户选择 |

### 3.2 辅助交互

| # | 需求 |
|---|------|
| F21 | 快捷键聚焦搜索框：`Ctrl+K` |
| F22 | 快捷键切换侧栏可见：`Ctrl+B` |
| F23 | 快捷键切换主题：`Ctrl+Shift+L` |
| F24 | 快捷键面板：`?` 弹出所有快捷键说明 |

### 3.3 数学与图表（前端增强）

| # | 需求 |
|---|------|
| F25 | KaTeX：渲染 `$...$` 与 `$$...$$`（本地打包，不走 CDN） |
| F26 | Mermaid：渲染 ```` ```mermaid ```` 代码块（本地打包） |

### 3.4 目录与构建约定

| # | 需求 |
|---|------|
| F27 | 源码目录 `src/md_viewer/`，测试 `tests/`，样本 `samples/`，设计文档 `docs/`，Docker 资源仓库根 |
| F28 | Python 包管理：`pip` + `requirements.txt`（v1 不引入 poetry/uv） |

## 4. 非功能需求

| # | 需求 |
|---|------|
| NF1 | **安全纵深防御**：挂载只读 + 应用路径白名单 + 渲染 HTML 清洗（nh3） |
| NF2 | **路径越权防护**：所有 `path` 参数走 `Path(...).resolve()` 后断言 `is_relative_to(ROOT)` |
| NF3 | **扩展名白名单**：内容 `.md/.markdown/.mdx`；图片 `.png/.jpg/.jpeg/.gif/.webp/.svg` |
| NF4 | **资源限制**：单文件 ≤ 5 MB；超过返回 413 |
| NF5 | **性能**：根树响应 ≤ 200 KB（千级文件）；单文件渲染 ≤ 100 ms（< 100 KB 输入） |
| NF6 | **容器安全**：以非 root 用户运行；HEALTHCHECK `/api/health` |
| NF7 | **测试覆盖**：`pytest` 覆盖 `tree`/`render`/`security`/`api` 关键路径 |
| NF8 | **跨平台**：macOS/Linux 通过 `docker run`；Windows 通过 Docker Desktop |

## 5. 架构

```
┌──────────────────────────────────────────┐
│  浏览器 (vanilla JS + KaTeX + Mermaid)  │
│                                          │
│  - 侧栏（文件树 + 搜索）                 │
│  - 主区（Markdown 渲染 / Raw 切换）      │
│  - 右侧 TOC                              │
│  - 状态：localStorage + URL ?p=          │
└────────────────┬─────────────────────────┘
                 │ HTTP (JSON + 二进制图片)
                 ▼
┌──────────────────────────────────────────┐
│  Flask 进程 (容器内, 非 root)           │
│                                          │
│  ┌─────────┬─────────┬─────────┬─────┐  │
│  │ api.py  │ tree.py │render.py│ sec │  │
│  └─────────┴─────────┴─────────┴─────┘  │
│  ┌─────────────────────────┐            │
│  │ encoding.py (UTF-8/GBK) │            │
│  └─────────────────────────┘            │
└────────────────┬─────────────────────────┘
                 │ 只读 syscall
                 ▼
            /data  (挂载卷)
```

**关键设计决策**：
- 单进程 Flask；开发服务器即可，不引入 gunicorn（个人本地、流量小）
- 文件树懒构建：`tree.py` 首次访问某节点时扫描其直接子节点并缓存
- 缓存策略：内存 `dict`，无失效机制（外部修改文件 → 下次访问重新 `iterdir()`，无显式 invalidate 逻辑）；重启容器即重建
- 前端零构建：单 HTML + 单 JS + 单 CSS + 本地打包 KaTeX/Mermaid

## 6. 组件拆分

| 模块 | 责任 | 主要依赖 |
|------|------|----------|
| `src/md_viewer/server.py` | Flask app factory，注册路由 | Flask |
| `src/md_viewer/api.py` | 路由处理（tree/children/search/file/image/health） | tree, render, security, encoding |
| `src/md_viewer/tree.py` | 目录扫描、子节点查询、缓存 | pathlib |
| `src/md_viewer/render.py` | markdown → HTML（GFM、TOC、anchor、attrs、wikilink 预处理）；含 KaTeX/Mermaid 客户端钩子 | markdown-it-py, mdit-py-plugins, nh3, pygments |
| `src/md_viewer/security.py` | 路径解析、扩展名白名单、越权检查 | pathlib |
| `src/md_viewer/encoding.py` | 编码探测：UTF-8 → GB18030 → latin-1 | — |
| `src/md_viewer/config.py` | 配置（端口、根目录路径、最大文件大小） | — |
| `src/md_viewer/__main__.py` | `python -m md_viewer` 入口 | server, cli |
| `src/md_viewer/cli.py` | argparse 子命令（v1 仅 `serve`） | argparse |
| `src/md_viewer/templates/index.html` | 主页面骨架（侧栏 + 主区 + TOC 栏） | — |
| `src/md_viewer/static/app.js` | 前端：fetch + DOM 更新 + 事件 + 快捷键 | — |
| `src/md_viewer/static/style.css` | 主题 CSS 变量 | — |
| `src/md_viewer/static/vendor/` | KaTeX、Mermaid 本地打包 | katex, mermaid |
| `tests/` | 单元测试 | pytest |
| `samples/` | 渲染回归测试用 .md 样本 | — |
| `Dockerfile`, `docker-compose.yml`, `requirements.txt`, `README.md` | 构建/部署 | — |

## 7. API 设计

### 7.1 端点

```
GET /api/health
  → 200 {"status":"ok","root":"/data","file_count":1234,"md_count":1180}

GET /api/tree
  → 200 {
      "name":"data","path":"/","type":"dir",
      "children":[
        {"name":"docs","path":"/docs","type":"dir","has_children":true,"child_count":42},
        {"name":"README.md","path":"/README.md","type":"file","size":1234}
      ]
    }
  (只返回一层；子目录用 has_children=true 标记，含子节点数 child_count 用于显示)

GET /api/children?path=/docs
  → 200 {"path":"/docs","children":[...同上结构...]}
  (400: path 不合法；403: 越权；404: 目录不存在)

GET /api/search?q=readme&limit=50
  → 200 {"query":"readme","matches":[
        {"name":"README.md","path":"/README.md","type":"file","size":1234}
      ]}
  (大小写不敏感；空格分词；按相关性命中数排序；limit 上限 200)

GET /api/file?path=/README.md&format=rendered
  → 200 {
      "meta": {"name":"README.md","size":1234,"mtime":1719560000.0},
      "title":"README",                       # H1 或文件名
      "html":"<h1 id=\"...\">...</h1>...",
      "toc":[{"level":1,"text":"...","id":"..."}],
      "encoding":"utf-8"
    }

GET /api/file?path=/README.md&format=raw
  → 200 {"meta":{...},"text":"# ...","encoding":"utf-8"}

GET /api/image?path=/assets/diagram.png
  → 200 image/png  (二进制流，带 ETag)
  (404: 不存在；403: 越权；400: 扩展名不在白名单)
```

### 7.2 错误约定

| 状态码 | 含义 |
|--------|------|
| 200 | 成功 |
| 400 | 参数错误（path 非法、扩展名不在白名单） |
| 403 | 越权（resolve 后不在白名单根目录内） |
| 404 | 文件/目录不存在 |
| 413 | 文件过大（> 5 MB） |
| 500 | 渲染失败（同时返回原始 text 字段供查看） |

## 8. 安全模型（纵深防御）

### 8.1 挂载层
- `-v <host_path>:/data:ro`：任何写操作均失败

### 8.2 应用层
- 所有 `path` 参数：先 `Path(path).resolve()`，再断言 `is_relative_to(ROOT)`
- 拒绝符号链接指向根外的文件（`Path.resolve()` 默认解引用 symlink，已隐式覆盖）
- 扩展名白名单按路由分类：内容 vs 图片

### 8.3 渲染层
- `markdown-it-py` `html: True`（允许 `<img>` 等合法 HTML 标签）
- 输出走 `nh3.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS)`
- 外链强制 `rel="noopener noreferrer"` + `target="_blank"`
- `<script>`、事件处理器（`onclick` 等）、`<style>` 全部拦截

## 9. 前端结构

### 9.1 布局

```
┌─────────────────────────────────────────────────────┐
│  [≡] md-viewer          [/path/to/file.md] [R] [☀] │
├──────────────┬──────────────────────────┬───────────┤
│              │                          │           │
│  [🔍 搜索]   │   <Markdown 渲染区>      │   TOC    │
│              │                          │           │
│  ▾ docs/     │                          │  # Sec 1  │
│    ▾ api/    │                          │    ## ... │
│      a.md    │                          │    ## ... │
│      b.md    │                          │  # Sec 2  │
│    ▸ notes/  │                          │           │
│              │                          │           │
└──────────────┴──────────────────────────┴───────────┘
[≡] 切换侧栏   [R] Raw/Rendered 切换   [☀] 主题
```

### 9.2 状态管理

- 全局状态对象：当前文件路径、侧栏可见、TOC 数据、主题
- localStorage keys：`mdv:selectedFile`、`mdv:sidebarVisible`、`mdv:sidebarWidth`、`mdv:theme`
- URL 查询：`?p=/path/to/file.md`（覆盖 localStorage）

### 9.3 关键交互流程

- **打开文件**：URL `?p=` 优先 → 否则 localStorage → 否则空主区
- **侧栏搜索**：输入 → debounce 300ms → `/api/search?q=...` → 覆盖侧栏列表为搜索结果
- **清除搜索**：`Esc` 或删除输入 → 恢复文件树
- **TOC 高亮**：滚动时观察所有 heading 节点，计算最靠近顶部的 heading → 高亮对应 TOC 项
- **Wikilink/跨文件链接**：渲染后拦截 `a[href]` 中 `.md` 结尾的，点击时阻止默认行为 + 切换主区
- **图片加载失败**：`<img onerror>` 替换为占位 DOM（含文件名 + 错误图标）
- **外部修改感知**：每次切换文件或 Ctrl+R 时重新请求 `/api/file`；不在前台时不做轮询

### 9.4 快捷键清单

| 键 | 动作 |
|----|------|
| `J` / `K` | 上/下一个 .md |
| `Alt+↓` / `Alt+↑` | 同上（备选） |
| `Ctrl+K` | 聚焦搜索框 |
| `Ctrl+B` | 切换侧栏 |
| `Ctrl+Shift+L` | 切换主题 |
| `Ctrl+R` | 刷新当前文件 |
| `R` | 切换 Raw/Rendered（仅当主区聚焦时） |
| `?` | 打开快捷键面板 |
| `Esc` | 清空搜索 / 关闭面板 |

## 10. Docker 部署

### 10.1 Dockerfile

```dockerfile
FROM python:3.12-slim

RUN useradd -m -u 1000 mdv

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY README.md ./

USER mdv

ENV MDV_ROOT=/data MDV_PORT=8000 MDV_HOST=0.0.0.0
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"

CMD ["python", "-m", "md_viewer", "serve"]
```

### 10.2 docker-compose.yml

```yaml
services:
  md-viewer:
    build: .
    image: md-viewer:latest
    ports:
      - "8000:8000"
    volumes:
      - ~/notes:/data:ro
    restart: unless-stopped
```

### 10.3 启动命令

```bash
docker run -d --name mdv -p 8000:8000 \
  -v /path/to/notes:/data:ro \
  md-viewer:latest

# 或
docker compose up -d
```

## 11. 测试策略

| 层 | 测试 | 工具 |
|----|------|------|
| `security.py` | 路径越权、扩展名白名单、符号链接 | pytest |
| `tree.py` | 排序（目录优先、字母序）、隐藏文件包含、`has_children` 正确性 | pytest + tmp_path |
| `render.py` | GFM 表格、任务列表、TOC、wikilink、anchor、代码高亮、nh3 清洗 | pytest + samples/ 回归 |
| `encoding.py` | UTF-8、GB18030、latin-1 fallback 顺序 | pytest + 字节 fixture |
| `api.py` | 各端点状态码、错误约定、`?format=raw|rendered` 分支 | pytest + Flask test client |
| 端到端 | 启动容器 + curl `/api/health` + 浏览 samples/ | shell + docker |

## 12. 范围外（明确不做）

- 全文搜索（v1 仅文件名搜索）
- 标签 / 分类聚合
- 反向链接（哪些文件链向我）
- 多卷挂载（v1 单根 `/data`）
- 国际化（v1 中文 + 英文 UI 文案硬编码）
- 移动端布局
- 编辑 / 预览所见即所得
- 文件变更实时推送（仅手动 Ctrl+R）
- HTTPS / 反向代理（v1 假定本机访问）

## 13. 风险与权衡

| 风险 | 影响 | 缓解 |
|------|------|------|
| KaTeX/Mermaid 本地打包增加镜像体积 | 镜像约 +3 MB（KaTeX ~280KB + Mermaid ~2.5MB + 字体） | 接受；如需瘦身再考虑按需加载或外置到 host volume |
| 文件树懒加载与搜索体验冲突 | 用户搜索时只看到已展开的内容 | 搜索走服务端全量扫描，独立于懒加载（已在 §5 决策中明确） |
| nh3 对 `<svg>` 渲染的限制 | inline SVG 可能被清洗 | 图片白名单支持 `.svg`，但 SVG 内的 JS 会被剥离（安全优先） |
| 中等规模（千级）首请求根节点时扫一次根目录 | 首请求慢 0.5-1s | 可接受；缓存后稳态无开销；非"启动时"扫描 |
| 单进程 Flask 不抗并发 | 多人同时打开多个 tab 时排队 | 目标单用户，可接受 |
