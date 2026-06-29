# md-viewer 品牌 UI 改动设计

**状态**：已批准（2026-06-29）
**作者**：通过 brainstorming 与用户协作产出

## 1. 背景与目标

md-viewer 是一个本地 Markdown 阅读器，已经通过 Docker 部署。当前页面在浏览器标签页、顶栏中显示的都是 "md-viewer"，过于朴素，且没有 favicon 导致每次访问都会触发 404（`/favicon.ico`）。

本次改动的目标：

- **提升品牌感**：让页面在浏览器标签页、书签、顶栏中都有清晰的视觉识别
- **消除 404 日志噪音**：通过提供 favicon 阻止浏览器对 `/favicon.ico` 的默认 404 请求
- **保持代码极简**：改动应该最小化、易于理解和维护

## 2. 改动文件

| 文件 | 状态 | 说明 |
|---|---|---|
| `src/md_viewer/templates/index.html` | 改 | 更新 `<title>`、brand 文字、内联 brand-icon SVG、加 favicon 引用 |
| `src/md_viewer/static/favicon.svg` | 新建 | 独立 SVG favicon 文件 |
| `src/md_viewer/static/style.css` | 改 | 加 `.brand` 颜色和 `.brand-icon` 样式 |
| `pyproject.toml` | 改 | 扩展 package-data 包含 `favicon.svg` |

## 3. 设计决策

### 3.1 Favicon 风格：Markdown 徽章

**形态**：灰底（`#6b7280`）+ 圆角矩形 + 白色 "M" 字 + 白色下划线 + 白色斜线（折角），表示一个折叠的 Markdown 文档。

**尺寸**：64×64 viewBox，渲染时自适应大小（16×16 favicon、32×32、64×64、Apple touch icon）。

**选择理由**：
- 直接表达工具本质（Markdown 文档阅读器）
- 现代感强但不过于花哨
- 灰底 + 白线在浅色 / 深色浏览器主题中都能清晰识别
- 单一灰度配色，与 md-viewer 现有"朴素文档"风格统一

### 3.2 顶栏 brand 布局：图标 + "Markdown Viewer" 完整文字

```
[☰]  [📝] Markdown Viewer                /wikilinks.md · 309 B  [Raw] [☀]
 ↑    ↑       ↑                              ↑                ↑     ↑
侧栏  20x20   品牌名 (深灰 #1f2937)         文件元信息         按钮
切换  SVG
```

**选择理由**：
- 与 favicon 视觉一致（同一 SVG，在不同尺寸下复用）
- "Markdown Viewer" 完整文字清晰传达工具用途
- 顺序：☰ → 📝 → Markdown Viewer → spacer → 元信息 → 按钮，逻辑流畅

### 3.3 品牌文字颜色：深灰 #1f2937

**选择理由**：
- 与 favicon 灰底（#6b7280）形成层次但不冲突（深灰字 + 中灰图标 = 视觉舒适）
- 不引入品牌色（蓝色），保持 md-viewer 朴素的"文档工具"定位
- 在浅色和深色主题下都易读

### 3.4 Favicon 格式：独立 .svg 文件（不内联）

**理由**：
- 浏览器会**自动**请求 `/favicon.ico` —— 通过 `<link rel="icon">` 让浏览器请求 `/static/favicon.svg`，浏览器**不会**再请求 `/favicon.ico`，404 噪音消失
- 独立文件可被浏览器缓存，HTML 页面体积小
- 未来如需支持老旧浏览器，再补充 `favicon.ico` 即可

**权衡**：IE 11 不支持 SVG favicon（但现代浏览器都支持）。如目标用户含 IE 11，需要后续补充 .ico。

## 4. 实现细节

### 4.1 `src/md_viewer/static/favicon.svg`（新建）

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect class="icon-bg" width="64" height="64" rx="8"/>
  <!-- M 形 -->
  <path d="M14 18 L14 46 M24 18 L24 46 M14 32 L20 32 M24 18 L34 18 L34 46"/>
  <!-- 折角斜线 -->
  <line x1="40" y1="22" x2="50" y2="42"/>
</svg>
```

> 注：SVG 中只包含 path 形状，颜色通过 CSS 类 `.icon-bg` 应用，便于顶栏复用同一图形。

### 4.2 `src/md_viewer/templates/index.html`（改）

在 `<head>` 中加 favicon 引用：

```html
<title>Markdown Viewer</title>
<link rel="icon" type="image/svg+xml" href="{{ url_for('static', filename='favicon.svg') }}">
```

在 `<header class="topbar">` 中加 brand-icon SVG、修改 brand 文字：

```html
<header class="topbar">
  <button id="toggle-sidebar" ...>☰</button>
  <svg class="brand-icon" viewBox="0 0 64 64">
    <rect class="icon-bg" width="64" height="64" rx="8"/>
    <path d="M14 18 L14 46 M24 18 L24 46 M14 32 L20 32 M24 18 L34 18 L34 46"/>
    <line x1="40" y1="22" x2="50" y2="42"/>
  </svg>
  <span class="brand">Markdown Viewer</span>
  <span class="meta" id="file-meta"></span>
  <span class="spacer"></span>
  <button id="toggle-raw" ...>Raw</button>
  <button id="toggle-theme" ...>☀</button>
</header>
```

### 4.3 `src/md_viewer/static/style.css`（改）

在现有 `.topbar` 相关样式附近添加：

```css
.brand { color: #1f2937; font-weight: 600; }
.brand-icon { width: 20px; height: 20px; flex-shrink: 0; }
.icon-bg { fill: #6b7280; }
.brand-icon path { stroke: white; stroke-width: 3.5; fill: none; }
.brand-icon line { stroke: white; stroke-width: 2.5; }
```

### 4.4 `pyproject.toml`（改）

```toml
[tool.setuptools.package-data]
"md_viewer" = ["templates/*", "static/*"]
```

`static/*` 改为支持整个 `static/` 目录（包括 favicon.svg）。

## 5. 验证

部署后测试以下场景：

| 测试 | 命令 / 工具 | 预期 |
|---|---|---|
| 页面 `<title>` | `curl -s http://192.168.2.100:8000/ \| grep '<title>'` | `<title>Markdown Viewer</title>` |
| Favicon 加载 | `curl -I http://192.168.2.100:8000/static/favicon.svg` | HTTP 200，`content-type: image/svg+xml` |
| 顶栏渲染 | 浏览器访问 `http://192.168.2.100:8000/`，查看顶栏 | ☰ → 灰色文档图标 → "Markdown Viewer"（深灰） |
| 404 消失 | `docker compose logs --tail 50` | 不再有 `/favicon.ico` 的 404 错误 |
| 容器健康 | `docker compose ps` | `Up ... (healthy)` |

## 6. 不在本次范围

- **IE 11 / 极老浏览器支持**：如需，提供一个 `favicon.ico` 即可（可从 `favicon.svg` 转换得到）
- **Apple touch icon**（`apple-touch-icon.png`）：本次不提供
- **深色主题适配**：当前 `brand` 文字用深灰 #1f2937 在浅色背景上已经清晰可读，深色主题下需要进一步调整（favicon 灰底在深色背景下也足够突出）。本次不展开。
- **`服务器端 favicon.ico 路由`**：现代浏览器识别 `<link rel="icon" type="image/svg+xml">` 后不再请求 `.ico`，404 自然消失，无需后端兜底。

## 7. 风险与回退

| 风险 | 严重度 | 缓解 |
|---|---|---|
| SVG favicon 不被某浏览器支持 | 低 | 绝大多数主流浏览器（Chrome 80+、Firefox 41+、Safari 16+、Edge 79+）支持 |
| 部署后 wheel 包未含 `static/favicon.svg` → 404 | 中 | 重建镜像（`docker compose up -d --build`），验证 `/static/favicon.svg` 返回 200 |
| Brand 文字颜色在不同主题下可读性差 | 低 | 当前浅色主题下深灰清晰；如未来加深色主题支持，单独调整 |
