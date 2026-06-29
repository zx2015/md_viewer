# md-viewer 品牌 UI 改动实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 md-viewer 页面添加 favicon、更新页面标题为 "Markdown Viewer"、重写顶栏品牌名为 "图标 + Markdown Viewer"，消除 `/favicon.ico` 的 404 日志噪音。

**Architecture:**
- 新增一个独立 SVG 文件作为 favicon
- 在 HTML `<head>` 加 `<link rel="icon" type="image/svg+xml">` 指向 SVG
- 在 HTML 顶栏中复用同一 SVG（缩小为 20x20）
- CSS 中为 `.brand` 加颜色，`.brand-icon` 加上 flex 行为

**Tech Stack:** Jinja2 模板（已有）、SVG（无依赖）、CSS（无依赖）、setuptools package-data（已有）。

---

## File Structure

| 文件 | 类型 | 职责 |
|---|---|---|
| `src/md_viewer/static/favicon.svg` | 新建 | 浏览器 favicon；顶栏 brand-icon 复用 |
| `src/md_viewer/templates/index.html` | 改 | 加 favicon link、改 title、插入 brand-icon SVG、改 brand 文字 |
| `src/md_viewer/static/style.css` | 改 | 加 `.brand` 颜色 + `.brand-icon` 尺寸/共享 SVG 类 |
| `pyproject.toml` | **不动** | 上一阶段（`TemplateNotFound: index.html` 修复）已把 `package-data` 扩为 `["templates/*", "static/*"]`，已覆盖 `static/favicon.svg` |

---

## Task 1: 创建 favicon.svg

**Files:**
- Create: `src/md_viewer/static/favicon.svg`

- [ ] **Step 1: 创建 SVG 文件**

将以下完整内容写入 `src/md_viewer/static/favicon.svg`：

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect class="icon-bg" width="64" height="64" rx="8"/>
  <path d="M14 18 L14 46 M24 18 L24 46 M14 32 L20 32 M24 18 L34 18 L34 46"/>
  <line x1="40" y1="22" x2="50" y2="42"/>
</svg>
```

- [ ] **Step 2: 验证 SVG 文件**

Run: `cat src/md_viewer/static/favicon.svg`
Expected: 输出上述 XML 内容，第一行包含 `<svg xmlns=...viewBox="0 0 64 64">`。

- [ ] **Step 3: 提交**

```bash
cd /media/data/git/md-viewer
git add src/md_viewer/static/favicon.svg
git commit -m "feat(static): add Markdown badge favicon.svg"
```

---

## Task 2: 修改 templates/index.html

**Files:**
- Modify: `src/md_viewer/templates/index.html:6`（改 title）
- Modify: `src/md_viewer/templates/index.html:7`（加 favicon link）
- Modify: `src/md_viewer/templates/index.html:12`（插入 brand-icon SVG + 改 brand 文字）

- [ ] **Step 1: 改 title**

当前第 6 行：
```html
  <title>md-viewer</title>
```

改为：
```html
  <title>Markdown Viewer</title>
```

- [ ] **Step 2: 在 title 之后加 favicon link**

当前第 7 行（紧接 title 之后）：
```html
  <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
```

将第 7 行替换为两行（先 favicon link，再 stylesheet）：
```html
  <link rel="icon" type="image/svg+xml" href="{{ url_for('static', filename='favicon.svg') }}">
  <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
```

- [ ] **Step 3: 插入 brand-icon SVG 并改 brand 文字**

当前第 12 行：
```html
  <span class="brand">md-viewer</span>
```

替换为（含 brand-icon SVG + 更新文字）：
```html
  <svg class="brand-icon" viewBox="0 0 64 64"><rect class="icon-bg" width="64" height="64" rx="8"/><path d="M14 18 L14 46 M24 18 L24 46 M14 32 L20 32 M24 18 L34 18 L34 46"/><line x1="40" y1="22" x2="50" y2="42"/></svg>
  <span class="brand">Markdown Viewer</span>
```

- [ ] **Step 4: 验证最终模板**

Run: `cat src/md_viewer/templates/index.html`
Expected: 输出包含三处关键修改：
- `<title>Markdown Viewer</title>`
- `<link rel="icon" type="image/svg+xml" href="{{ url_for('static', filename='favicon.svg') }}">`
- `<span class="brand">Markdown Viewer</span>`

- [ ] **Step 5: 提交**

```bash
cd /media/data/git/md-viewer
git add src/md_viewer/templates/index.html
git commit -m "feat(templates): update title to 'Markdown Viewer' and add favicon

- <title>: 'md-viewer' -> 'Markdown Viewer'
- <link rel='icon' type='image/svg+xml'> for /static/favicon.svg
- inline brand-icon SVG in topbar
- <span class='brand'>: 'md-viewer' -> 'Markdown Viewer'"
```

---

## Task 3: 修改 static/style.css

**Files:**
- Modify: `src/md_viewer/static/style.css`（在 .topbar 区块附近添加新样式）

- [ ] **Step 1: 定位 .topbar 样式块**

Run: `grep -n "^\.topbar" src/md_viewer/static/style.css`
Expected: 输出形如 `30:.topbar {`、`34:.topbar .spacer`、`35:.topbar button` 等行号。

- [ ] **Step 2: 在 .topbar 区块之后插入新样式**

在 `.topbar button:disabled`（第 39 行）之后，`.meta`（第 40 行）之前，插入以下内容：

```css
.brand { color: #1f2937; font-weight: 600; }
.brand-icon { width: 20px; height: 20px; flex-shrink: 0; }
.icon-bg { fill: #6b7280; }
.brand-icon path { stroke: white; stroke-width: 3.5; fill: none; }
.brand-icon line { stroke: white; stroke-width: 2.5; }
```

> **说明**：
> - `.brand` 加颜色 #1f2937（深灰）和字重 600
> - `.brand-icon` 20x20，flex-shrink 防止在窄屏时被压扁
> - `.icon-bg` 类作用于 SVG 中 `<rect class="icon-bg">`，统一两个位置的灰色填充
> - `.brand-icon path` / `.brand-icon line` 用 CSS 选择器特异性（`.brand-icon` 后代选择器）只影响顶栏内的 SVG 副本，不影响 favicon.svg（因为 favicon 在 `<link>` 标签里，没有 DOM 上下文）

- [ ] **Step 3: 验证新样式已添加**

Run: `grep -n "^\.brand\|^\.icon-bg" src/md_viewer/static/style.css`
Expected: 至少 5 行匹配，`.brand` 和 `.icon-bg` 行都存在。

- [ ] **Step 4: 提交**

```bash
cd /media/data/git/md-viewer
git add src/md_viewer/static/style.css
git commit -m "feat(css): add .brand color and .brand-icon styles

- .brand: color #1f2937, font-weight 600
- .brand-icon: 20x20, flex-shrink 0
- .icon-bg: fill #6b7280
- .brand-icon path/line: white stroke 3.5/2.5"
```

---

## Task 4: 重建 Docker 镜像并验证

**Files:**
- 无（仅 Docker 操作）

- [ ] **Step 1: 重新构建并启动**

Run:
```bash
cd /media/data/git/md-viewer
docker compose up -d --build
```

Expected: 构建完成后输出 `Container md-viewer Recreated` 和 `Container md-viewer Started`，最终 `docker compose ps` 显示 `Up ... (healthy)`。

- [ ] **Step 2: 验证 title 变更**

Run:
```bash
curl -s http://localhost:8000/ | grep '<title>'
```

Expected: 输出 `<title>Markdown Viewer</title>`。

- [ ] **Step 3: 验证 favicon 可访问**

Run:
```bash
curl -sI http://localhost:8000/static/favicon.svg | head -3
```

Expected: 输出包含 `HTTP/1.1 200 OK` 和 `content-type: image/svg+xml`。

- [ ] **Step 4: 验证无 /favicon.ico 404 日志**

Run:
```bash
docker compose logs --tail 30 | grep -i "favicon.ico.*404" || echo "✓ 无 /favicon.ico 404"
```

Expected: 输出 `✓ 无 /favicon.ico 404`。

- [ ] **Step 5: 浏览器实测（描述）**

在浏览器中访问 `http://192.168.2.100:8000/`。预期看到：
- 浏览器标签页 favicon 为灰底文档图标
- 标签页标题为 "Markdown Viewer"
- 顶栏左侧：☰ → 灰色文档图标 → "Markdown Viewer" 文字
- 整体功能保持原样

---

## Notes

- **没有自动化测试**：本任务纯 UI 改动（HTML 模板、CSS、静态资源），无 Python 逻辑变更。验证靠 HTTP 响应和浏览器目视检查。
- **CD 友好**：所有改动都已 staged 并 commit，无需再 commit。
- **回退方案**：`git revert HEAD~3..HEAD` 可回退全部 3 个 feature commit。
- **没有 `app.js` 改动**：现有 JS 不需要任何变更（`brand` 类样式会自动通过 CSS 应用，brand-icon SVG 已在 HTML 中静态存在）。
