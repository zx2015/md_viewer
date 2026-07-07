# md-viewer v2 增量特性 — 需求规格

**状态**：已实现并与代码同步（2026-07-07）
**作者**：基于用户需求整理
**日期**：2026-07-06
**基于版本**：commit `01a23d9`（含 branding 改动、multi-root healthcheck 优化）

## 1. 背景与目标

当前 md-viewer v1 已完整覆盖 Markdown 浏览核心场景（设计文档 `docs/2026-06-28-md-viewer-design.md`）。在实际使用中暴露三个体验缺口，本次增量特性针对这些缺口：

1. **文件树无法手动刷新**：外部新增/删除/重命名文件后，浏览器侧已懒加载的文件树不会自动感知。`Ctrl+R` 当前只重载**当前打开的文件**，不重载文件树。
2. **刷新页面后丢失当前文件在树中的位置**：刷新页面（Ctrl+R/F5）或重开标签时，虽然文件内容能从 localStorage 恢复，但文件树回到折叠状态，用户必须手动展开多个层级才能看到当前文件高亮在哪个目录中。
3. **代码/数据/网页源文件无法查看**：仓库中常并存 `.py` / `.json` / `.html` 文件（脚本、配置、生成的 HTML），但当前仅 `.md/.markdown/.mdx` 是可点击的"内容文件"，其他文件类型要么被文件树过滤掉，要么点击后会被后端 400 拒绝（扩展名不在白名单）。

## 2. 范围

### 2.1 本次新增

| ID | 特性 |
|----|------|
| F-R1 | 侧栏顶部文件树刷新按钮：刷新文件树 + 重新加载当前打开的文件 |
| F-R2 | 自动展开到当前文件：刷新页面 / 打开新文件时，文件树自动从根展开到当前文件所在目录，并将当前文件滚动到可视区 |
| F-R3 | `.py` / `.json` / `.html` 三个新扩展名加入 `content_exts`，允许在文件树中点击 |
| F-R4 | `.py` 文件：渲染为带 Pygments Python 语法高亮的源码（默认格式） |
| F-R5 | `.json` 文件：渲染为带 Pygments JSON 语法高亮的源码；JSON 无效时降级为纯文本 + 顶部错误条 |
| F-R6 | `.html` 文件：默认渲染为**沙盒预览**（`<iframe sandbox>`），顶部提供"查看源码"切换 |
| F-R7 | `.html` 源码查看：使用 Pygments HTML/XML lexer 高亮显示源码 |
| F-R8 | 新格式的快捷键行为与 `.md` 一致：`R` 切换原始/渲染（仅 .html 实际有效：preview ↔ source），`Ctrl+R` 仅重载当前文件 |
| F-R9 | J/K 跳转目标若位于未展开目录，自动展开路径并 scrollIntoView（与 F-R2 复用同一套机制） |
| F-R10 | Markdown 普通相对链接按“当前文件目录”解析：后端渲染期重写 + 前端点击时兜底解析 |
| F-R11 | Mermaid 流程图渲染：`pre.mermaid` 在前端 hydrate 为 SVG 图，主题切换时保持风格同步 |
| F-R12 | Mermaid 图缩放控件：每个 Mermaid 图支持 `+` 放大、`-` 缩小、`100%` 重置 |

### 2.2 明确不做

- **不做**对 `.css` / `.js` / `.yaml` / `.toml` / `.txt` 等其他扩展名的支持（留待后续）
- **不做**HTML 文件渲染后再做 Markdown 内嵌（`<iframe>` 内只是 HTML 本身，不做额外转译）
- **不做**代码文件的"编辑"或"复制到剪贴板按钮"（仅靠浏览器默认文本选择）
- **不做**对文件树的自动轮询监听（保持 v1 设计 §5 "外部修改感知靠手动"）
- **不做**`.html` 沙盒内的 `<script>` 权限——`sandbox` 属性不包含 `allow-scripts`，最大化安全
- **不修改**设计文档 §3 中已经实现的 F1-F28 任何条款

## 3. 详细设计

### 3.1 文件树刷新按钮（F-R1）

#### 3.1.1 位置

**侧栏顶部，搜索框右侧**，与搜索框同行。

```
┌──────────────────────────────────┐
│  [🔍 搜索文件名… (Ctrl+K)]  [🔄] │
├──────────────────────────────────┤
│  ▾ docs/                         │
│    ▸ api/                        │
└──────────────────────────────────┘
```

理由（用户已确认）：与文件树空间关联最强；侧栏隐藏时仍可通过键盘快捷键触发（见 3.1.3）。

#### 3.1.2 行为

点击后按顺序执行：

1. **重新拉取根目录**：`GET /api/tree` 覆盖 `state.tree`，并重置所有已懒加载子节点缓存（`childrenWrap.dataset.loaded` 全部清空）
2. **重新渲染整个树**：`$("#tree").innerHTML = ""` 后重新挂载
3. **重新加载当前打开的文件**：如果 `state.selectedFile` 非空，调一次 `openFile(state.selectedFile, { format: state.renderedFormat })`
4. **恢复展开状态**：复用 F-R2 的"展开到当前文件"机制（见 3.2）

按钮在拉取过程中显示旋转动画 + 禁用态，避免重复点击。

#### 3.1.3 快捷键

新增快捷键 **`Ctrl+Shift+R`**（或 **`F5`**，两者均可）触发同样的"刷新文件树 + 重载当前文件"。不和现有 `Ctrl+R` 冲突——`Ctrl+R` 仍只重载当前文件内容（v1 行为不变）。

> 备选：`Ctrl+R` 改为做"刷新文件树 + 重载当前文件"。**默认采用 `Ctrl+Shift+R` + `F5` 双绑**，保留 `Ctrl+R` 的现有语义，避免破坏用户已习惯的快捷键。

#### 3.1.4 视觉

- 20×20 SVG 图标（与品牌图标风格一致：灰底圆角矩形 + 白色循环箭头）
- 顶栏按钮同样风格：与 `Raw`/`☀` 同高、边框、字号
- hover 时按钮背景轻微变深
- 旋转动画使用 CSS `@keyframes spin`（0.6s linear infinite）

### 3.2 自动展开到当前文件（F-R2 + F-R9）

#### 3.2.1 触发时机

| 触发源 | 何时执行 |
|--------|----------|
| 页面初次加载（`?p=` 或 localStorage） | `loadTree().then(...)` 中 openFile 之后 |
| 用户点击文件（openFile） | openFile 主体内，API 返回成功后 |
| 用户按 J/K 跳转 | openFile 被内部调用，复用同一逻辑 |
| 刷新文件树（F-R1） | refreshTree 完成后 |
| Ctrl+Shift+R / F5 | 复用 refreshTree |

#### 3.2.2 算法

伪代码（前端 `app.js`）：

```js
async function revealSelectedInTree() {
  const path = state.selectedFile;
  if (!path) return;

  // 1. 找到路径上所有需要展开的目录（不含文件本身）
  const parts = path.split("/").filter(Boolean);  // ["docs", "api", "auth.md"]
  if (parts.length < 2) return;  // 根级文件无需展开

  const dirSegments = parts.slice(0, -1);  // ["docs", "api"]
  let curPath = "";

  for (const seg of dirSegments) {
    curPath += "/" + seg;
    // 2. 找到当前层对应目录节点
    const dirRow = document.querySelector(
      `.tree .node.dir[data-path="${cssEscape(curPath)}"]`
    );
    if (!dirRow) return;  // 树中不存在（可能搜索结果状态），跳过
    // 3. 展开它（必要时先 lazy load）
    const wrap = dirRow.nextElementSibling;  // .children div
    if (wrap && wrap.classList.contains("children") && wrap.hidden) {
      if (!wrap.dataset.loaded) {
        const data = await fetchJSON(
          `/api/children?path=${encodeURIComponent(curPath)}`
        );
        wrap.innerHTML = "";
        for (const child of data.children) {
          wrap.appendChild(renderNode(child, depth + 1));
        }
        wrap.dataset.loaded = "1";
      }
      wrap.hidden = false;
      const twist = dirRow.querySelector(".twist");
      if (twist) twist.textContent = "\u25BE ";
    }
  }

  // 4. 滚动到当前文件行
  const fileRow = document.querySelector(
    `.tree .node.file[data-path="${cssEscape(path)}"]`
  );
  if (fileRow) fileRow.scrollIntoView({ block: "center", behavior: "smooth" });
}
```

**性能考量**：路径最深 `~10` 层，每层一次 `GET /api/children`，最坏 10 次请求。可接受——文件树单次扫描非常快，且用户实际操作中很少在最深路径。

**并发安全**：每次 reveal 触发前用一个递增 token (`revealSeq`) 避免过期请求污染 DOM。

#### 3.2.3 与现有 `.active` 高亮的关系

openFile 已经设置 `.tree .node.active`。本次不改动该逻辑——`revealSelectedInTree` 只负责"展开 + 滚动"，不重复设置 active。

#### 3.2.4 文件树状态持久化

**不持久化**展开状态。理由：v1 设计 §3.1-F11 明确"侧栏可见性、侧栏宽度、主题"才进 localStorage；展开层级是高频操作，持久化会让"刷新文件树"按钮的功能价值被部分抵消（用户希望主动刷新时看到的是"干净状态 + 跳到当前文件"，而不是"上次手动展开留下的状态"）。

> 可调：若用户后续希望记忆展开路径，再独立提一个 `mdv:treeExpandedPaths` 增量特性。

### 3.3 多格式文件支持（F-R3 — F-R8）

#### 3.3.1 扩展名白名单扩展

`src/md_viewer/config.py`：

```python
content_exts: frozenset[str] = frozenset({
    ".md", ".markdown", ".mdx",
    ".py", ".json", ".html", ".htm",
})
```

`.htm` 视作 `.html` 同等处理（合并为同一渲染分支）。

#### 3.3.2 渲染分发

`src/md_viewer/render.py` 提供 `render_viewable(filename: str, text: str, current_file_path: str | None = None) -> dict`，按扩展名分支：

| 扩展名 | 分支 | 输出 |
|--------|------|------|
| `.md` / `.markdown` / `.mdx` | 现有 `render_markdown` | `{html, toc, title}` |
| `.py` | `render_code_view` + lexer `python` | `{html, toc: [], title, kind: "code"}` |
| `.json` | `render_code_view` + lexer `json`；先 `json.loads` 校验，无效走 `kind: "code-error"` | `{html, toc: [], title, kind, json_valid}` |
| `.html` / `.htm` | `render_html_view` | `{kind: "html", html: <iframe srcdoc sandbox>, source: 高亮后源码字符串}` |

**统一返回结构**：

```python
{
    "kind": "markdown" | "code" | "code-error" | "html",
    "html": str,          # 主区域要渲染的 HTML
    "toc": list[dict],    # 仅 markdown 有内容，其他 []
    "title": str | None,
    "raw": str | None,    # 仅 html：原始源码（用于切到源码视图）
    "source_html": str | None,  # 仅 html：高亮后的源码 HTML
}
```

> `.py` 和 `.json` 没有"切到 Raw"的概念：它们本身就是源码。`openFile` 的 `format=raw` 对它们退化为 `format=rendered`，前端通过 `kind !== "html"` 检测后禁用 Raw 按钮（或自动隐藏 Raw 切换按钮）。

#### 3.3.3 代码高亮方案（`.py` / `.json`）

复用现有 `_highlight` 函数（`render.py`）：

```python
def render_code_view(text: str, lang: str) -> str:
    return _highlight(text, lang)
```

输出包一层 `.content pre`，与现有代码块视觉一致：

```html
<pre class="copyable-code language-{lang}"><code class="highlight">...</code></pre>
```

**JSON 校验失败处理**：尝试 `json.loads(text)`；失败时返回的 `kind="code-error"`，额外字段 `error` 包含校验错误信息；前端在该 `.kind` 下在文件元信息条下方渲染一行黄色警告：

```
⚠ JSON 语法错误：Expecting ',' delimiter: line 5 column 12 (char 87)
```

下方仍展示高亮源码（按纯文本高亮，不抛错）。

#### 3.3.4 HTML 沙盒预览（`.html`）

前端拿到 `kind: "html"` 后：

```html
<iframe class="html-preview"
        sandbox=""
        srcdoc="{escaped_source}"
        referrerpolicy="no-referrer"></iframe>
```

- `sandbox=""`（空值）= 最严格：无 scripts、无同源、无 top-level navigation、无 forms、无 popups、无 pointer lock
- `srcdoc` 而非 `src` + `/api/html?path=...`：避免污染 URL 历史栈；源文档完全可控
- 注意：`srcdoc` 内容需要正确 HTML 转义，避免 attribute 注入（前端用 `escapeHtml` 双层转义）

预览区尺寸：宽 100%、高 calc(100vh - 顶栏 - 元信息条)，`border: 1px solid var(--border)`，圆角与代码块一致。

#### 3.3.5 HTML 源码切换（F-R7 + F-R8）

顶栏 `Raw` 按钮对 `.html` 文件实际切换的是 **Preview ↔ Source**：

- Preview（默认）：`<iframe srcdoc>`
- Source：高亮的 HTML/XML 源码（同 code-view）

按钮文本相应变为 `Source` / `Preview`。其他文件类型下按钮隐藏或禁用。

实现：openFile 根据 `state.selectedFile` 的扩展名决定按钮可见性 + 文案：

```js
const ext = state.selectedFile.split(".").pop().toLowerCase();
if (ext === "html" || ext === "htm") {
  $("#toggle-raw").disabled = false;
  $("#toggle-raw").textContent = state.renderedFormat === "raw" ? "Preview" : "Source";
} else if (ext === "py" || ext === "json") {
  $("#toggle-raw").hidden = true;  // 代码文件无切换意义
} else {
  $("#toggle-raw").hidden = false;
  $("#toggle-raw").textContent = state.renderedFormat === "raw" ? "Rendered" : "Raw";
}
```

### 3.4 后端 API 变更

#### 3.4.1 `/api/file`

现有签名不变，但 `format` 参数对非 md 扩展名有特殊处理：

| 扩展名 | `format=rendered`（默认） | `format=raw` |
|--------|---------------------------|---------------|
| `.md` 等 | 现有渲染 | 原始文本 |
| `.py` | 高亮源码 HTML（仍走 JSON 通道） | **同 rendered**（无差异；后端等价返回） |
| `.json` | 同上 | 同上 |
| `.html` | `{kind: "html", html: "<iframe srcdoc=...>"}` | `{kind: "html", html: "<pre>源码高亮</pre>", raw: "..."}` |

> 关键：**仍然返回 JSON，不返回 `text/plain`**。原因：保持与现有 `.md` 调用路径完全一致；前端 `fetchJSON` 不用分支处理 Response 类型。`.html` 源码嵌在 `srcdoc` 属性里需要正确转义，前端拿到后再赋值。

#### 3.4.2 `/api/tree` 和 `/api/search`

无需改动——`tree.py` 已经在 `_build_node` 中按 `cfg.content_exts` 过滤文件，扩 ext 后自动生效。

### 3.4.3 Markdown 相对链接解析（F-R10）

当前实现采用“双保险”：

1. **后端重写（主路径）**：`render.py` 在渲染后处理 `<a href="...">`，将本地相对内容链接（`.md/.markdown/.mdx/.py/.json/.html/.htm`）按 `current_file_path` 归一化后改写为 `/api/file?path=...`。
2. **前端兜底（兼容路径）**：`app.js` 的 `hydrateContent()` 对 `a[href]` 统一拦截，若链接仍是本地相对路径，则按 `state.selectedFile` 解析为绝对仓内路径并 `openFile()`。

处理规则：

- 外链（`http/https//mailto/tel`）保持默认行为；
- 锚点（`#...`）和纯查询（`?...`）不改写；
- 保留 fragment（如 `guide.md#intro`）；
- 最终访问仍走 `/api/file`，由后端 `resolve_safe` 统一做越权校验。

### 3.4.4 Mermaid 流程图渲染（F-R11）

当前实现为“后端保留 + 前端渲染”：

1. 后端 `render.py` 对 ```mermaid``` 代码块输出 `<pre class="mermaid">...</pre>`；
2. 模板 `index.html` 引入 Mermaid 运行时脚本；
3. 前端 `app.js` 在 Markdown 内容注入后执行 `hydrateMermaid()`，对 `pre.mermaid` 调 `mermaid.run()` 渲染为 SVG；
4. 主题切换（含 `auto` 跟随系统变更）后，若当前是 Markdown 渲染态，则重新加载当前文件以触发 Mermaid 重新渲染，保证图表主题同步。

安全与回退：

- Mermaid 使用 `securityLevel: "strict"`；
- Mermaid 脚本加载失败时，页面保持原始 `<pre class="mermaid">` 文本，不阻断文档阅读。

### 3.4.5 Mermaid 图缩放控件（F-R12）

在 Mermaid 渲染完成后，前端将每个 Mermaid 节点包裹为独立图表容器，并注入工具栏按钮：

- `-`：缩小 10%
- `100%`：显示当前缩放比例，点击重置为 100%
- `+`：放大 10%

约束与交互：

- 缩放范围限制为 `50% ~ 250%`，达到边界时对应按钮禁用；
- 缩放仅作用于当前图，不影响其他 Mermaid 图；
- 图表区域启用 `overflow:auto`，放大后可滚动查看完整内容。

### 3.5 文件树显示细节

#### 3.5.1 新文件类型的图标（可选增强）

当前文件树所有文件都是同一 `.node.file` 样式，无差异化。如果用户希望区分：

| 扩展名 | 在文件名后追加的角标 |
|--------|---------------------|
| `.py` | `[py]` |
| `.json` | `[json]` |
| `.html` / `.htm` | `[html]` |

> **默认不做**——保持极简。如用户后续要求再加。

### 3.6 快捷键总览（v2 后）

| 键 | 动作 | 备注 |
|----|------|------|
| `J` / `K` | 上/下一个文件 | 自动展开目录 |
| `Alt+↓` / `Alt+↑` | 同上（备选） | 自动展开目录 |
| `Ctrl+K` | 聚焦搜索框 | 不变 |
| `Ctrl+B` | 切换侧栏 | 不变 |
| `Ctrl+Shift+L` | 切换主题 | 不变 |
| `Ctrl+R` | **重载当前文件** | 不变（行为保持向后兼容） |
| **`Ctrl+Shift+R`** / **`F5`** | **刷新文件树 + 重载当前文件** | 新增 |
| `R` | 切换 Raw/Rendered（仅 markdown） | 不变 |
| `R`（html 文件） | 切换 Preview/Source | 新增 |
| `Esc` | 清空搜索 / 失焦输入 | 不变 |

## 4. 错误处理

| 场景 | 表现 |
|------|------|
| `.py` 文件读取失败（权限、I/O） | 后端 4xx/5xx，前端复用现有 `加载失败: ...` 提示 |
| `.json` 解析失败 | 顶部黄色警告条 + 下方仍展示高亮源码（按 plain text 高亮） |
| `.html` 沙盒内脚本/外部资源被浏览器拦截 | 不提示——预期行为；用户可切换到 Source 查看完整标签 |
| 刷新按钮按下后 `/api/tree` 失败 | 按钮停止旋转，恢复可用；`console.error`；不重置 `state.tree`（保留旧树） |
| 自动展开过程中某层目录 404 | 静默停止后续展开；`console.warn`；当前文件仍高亮 |
| J/K 跳转到树中不存在的文件（外部删除） | 静默打开并展示错误信息；不打断快捷键序列 |

## 5. 测试策略

### 5.1 后端

| 测试 | 文件 | 用例 |
|------|------|------|
| `test_render.py` | 新增 | `render_viewable(.py)` 输出含 `<span class="n">def</span>` 等 Pygments 类名；`render_viewable(.json)` 合法/非法都返回 200；`render_viewable(.html)` 输出含 `<iframe` + `sandbox=""` + `srcdoc=` |
| `test_api.py` | 新增 | `/api/file?path=a.py` 返回 `{kind: "code", html: "..."}`；`?format=raw` 对 `.py`/`.json` 返回 `{kind: "code", ...}`（无 text 字段或等价内容）；`?format=raw` 对 `.html` 返回 `{kind: "html", raw: "..."}` |
| `test_security.py` | 新增（可选） | `check_extension` 对新扩展名 `.py/.json/.html/.htm` 通过 |
| `test_tree.py` | 不变 | 现有 fixture 已用 `.md`；新增 fixture 含 `.py` 文件，验证 `list_children` 把它列为可见文件 |

### 5.2 前端

无自动化测试（项目无前端测试框架）。验证靠手动 + 浏览器 DevTools：

- 浏览器 console 无新增 error
- `app.js` 中关键函数可断点调试：`revealSelectedInTree`、`refreshTree`、`openFile` 的 `kind` 分支
- 检查 DOM：刷新后 `.tree .node.active` 对应当前文件且其祖先目录 `.children` 均 `hidden=false`

### 5.3 视觉/交互验收清单

- [x] 刷新页面后文件树自动展开到上次选中文件
- [x] 刷新按钮点击后旋转动画、列表更新、当前文件重新加载
- [x] `Ctrl+Shift+R` 等同于点击刷新按钮
- [x] 文件树中能看到 `.py` / `.json` / `.html` 文件并点击
- [x] `.py` 文件显示带颜色高亮的源码
- [x] 非法 `.json` 文件顶部显示错误条 + 仍展示源码
- [x] `.html` 文件默认显示 `<iframe sandbox>` 预览
- [x] `.html` 文件下点 `Source` 切到高亮源码
- [x] `.html` 文件下点 `Preview` 切回沙盒
- [x] `.py` / `.json` 文件下不显示 Raw/Source 按钮（或按钮禁用）
- [x] J/K 跳到深层目录时自动展开并 scrollIntoView
- [x] Mermaid 代码块（`graph TD`、`sequenceDiagram`）渲染为 SVG 而非源码文本
- [x] Mermaid 图支持 `+/-/100%` 缩放控件

## 6. 风险与权衡

| 风险 | 严重度 | 缓解 |
|------|--------|------|
| 自动展开对深层路径触发多次 `/api/children` | 低 | 单层扫描快；最坏 10 层约 10 次请求；用户体验远胜手动展开 |
| HTML 沙盒预览可能与图片/CSS 路径冲突 | 低 | 沙盒最严格，原 HTML 内的 `<script>` 自动失效；如 HTML 用相对路径引用图片，会显示空白——但符合"安全预览"目标 |
| JSON 校验增加一次解析开销 | 极低 | 5MB 上限下，5MB JSON 解析 < 100ms；只在 `/api/file` 路径触发 |
| `.py` 文件含敏感信息（如 `SECRET_KEY = "..."`） | 中 | 不引入新风险——本身就是 read-only 浏览；但考虑在 v2 后续加"敏感文件后缀默认折叠"功能 |
| Markdown 相对链接历史文档使用旧行为 | 低 | 已补充 F-R10：后端重写 + 前端兜底，避免相对链接失效 |
| Mermaid 运行时脚本不可达（CDN/网络受限） | 中 | 回退为源码文本显示；后续可切换为本地 vendored 资源 |
| Mermaid 图过大导致阅读区域受限 | 低 | 缩放 + 容器滚动条组合，确保可达性 |

## 7. 不在本次范围（明确 deferred）

- `.css` / `.js` / `.yaml` / `.toml` / `.txt` / `.sh` 等其他扩展名
- 文件树展开状态持久化（`mdv:treeExpandedPaths`）
- 文件修改自动监听（`watchfiles`）
- HTML 文件内嵌资源（图片/CSS）的本地代理
- 代码差异对比（diff view）
- 文件夹右键菜单（新建/删除/重命名）

## 8. 已落地实现摘要

1. 后端：`render_viewable` 多格式分发已落地，`content_exts` 扩展已生效，`/api/file` 已按 `kind` 返回。
2. 前端：`refreshTree`、`revealSelectedInTree`、多格式 `openFile` 分支、主题代码样式切换均已落地。
3. 链接：Markdown 相对链接采用“后端重写 + 前端兜底”双保险（F-R10）。
4. Mermaid：Markdown 渲染后前端 hydrate，主题切换时可重渲染（F-R11）。
5. Mermaid 交互：每图独立 `+/-/100%` 缩放控件与滚动容器（F-R12）。
6. 测试：`test_render.py`、`test_api.py` 已覆盖核心分支（含相对链接解析场景）。

## 9. 相关文档

- 现有设计：`docs/2026-06-28-md-viewer-design.md` §3.1（F3-F12）、§6、§7
- 现有实现计划：`docs/2026-06-28-md-viewer-impl-plan.md`
- 品牌 UI 设计：`docs/superpowers/specs/2026-06-29-md-viewer-branding-design.md`
- 用户偏好（侧栏默认隐藏）：`.learnings/preference/default-hidden-sidebar-preference.md`

## Related

- [现有设计文档](../2026-06-28-md-viewer-design.md)
- [现有实现计划](../2026-06-28-md-viewer-impl-plan.md)
- [品牌 UI 改动设计](2026-06-29-md-viewer-branding-design.md)