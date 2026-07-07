(function () {
  "use strict";

  const LS = {
    selectedFile: "mdv:selectedFile",
    sidebarVisible: "mdv:sidebarVisible",
    theme: "mdv:theme",
  };

  const state = {
    selectedFile: null,
    renderedFormat: "rendered",
    theme: "auto",
    sidebarVisible: false,
    tree: { children: [] },
    flatSortedMds: [],
  };

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));

  function loadLS() {
    state.selectedFile = localStorage.getItem(LS.selectedFile) || null;
    state.theme = localStorage.getItem(LS.theme) || "auto";
    state.sidebarVisible = localStorage.getItem(LS.sidebarVisible) === "true";
  }

  function saveLS() {
    if (state.selectedFile) localStorage.setItem(LS.selectedFile, state.selectedFile);
    localStorage.setItem(LS.theme, state.theme);
    localStorage.setItem(LS.sidebarVisible, state.sidebarVisible ? "true" : "false");
  }

  function applyTheme() {
    const t = state.theme;
    if (t === "auto") {
      document.body.dataset.theme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    } else {
      document.body.dataset.theme = t;
    }
    // Re-fetch Pygments CSS for the resolved theme; fire-and-forget.
    loadCodeStyle(document.body.dataset.theme);
  }

  let codeStyleSeq = 0;
  async function loadCodeStyle(theme) {
    const seq = ++codeStyleSeq;
    let css;
    try {
      const r = await fetch(`/api/code-style?theme=${encodeURIComponent(theme)}`);
      if (!r.ok) throw new Error(`code-style -> ${r.status}`);
      css = await r.text();
    } catch (e) {
      console.warn("loadCodeStyle failed", e);
      return;
    }
    if (seq !== codeStyleSeq) return; // a newer load started
    let tag = document.getElementById("mdv-code-style");
    if (!tag) {
      tag = document.createElement("style");
      tag.id = "mdv-code-style";
      document.head.appendChild(tag);
    }
    tag.textContent = css;
  }

  function applySidebar() {
    document.body.classList.toggle("no-sidebar", !state.sidebarVisible);
  }

  async function fetchJSON(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`${url} -> ${r.status}`);
    return r.json();
  }

  function cssEscape(s) {
    return s.replace(/["\\]/g, "\\$&");
  }

  function escapeHtml(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function resolveLocalContentPath(href) {
    if (!href || href.startsWith("#") || href.startsWith("?")) return null;
    if (/^(https?:)?\/\//i.test(href) || /^(mailto|tel):/i.test(href)) return null;

    if (href.startsWith("/api/file?path=")) {
      try {
        const url = new URL(href, location.origin);
        return url.searchParams.get("path");
      } catch (_) {
        return null;
      }
    }

    const [pathPart] = href.split(/[?#]/, 1);
    if (!/\.(md|markdown|mdx|py|json|html|htm)$/i.test(pathPart || "")) return null;

    const base = state.selectedFile || "/";
    const baseDirParts = base.split("/").filter(Boolean);
    if (baseDirParts.length) baseDirParts.pop();
    const targetParts = pathPart.startsWith("/")
      ? pathPart.split("/").filter(Boolean)
      : baseDirParts.concat(pathPart.split("/").filter(Boolean));
    const stack = [];
    for (const part of targetParts) {
      if (!part || part === ".") continue;
      if (part === "..") {
        if (stack.length) stack.pop();
        continue;
      }
      stack.push(part);
    }
    return "/" + stack.join("/");
  }

  // ===== Tree rendering =====
  function renderNode(node, depth) {
    const wrap = document.createElement("div");
    const row = document.createElement("div");
    row.className = `node ${node.type}`;
    row.dataset.path = node.path;
    row.dataset.type = node.type;

    const twist = document.createElement("span");
    twist.className = "twist";
    twist.textContent = node.type === "dir" ? "\u25B8 " : "  ";
    row.appendChild(twist);

    const label = document.createElement("span");
    label.className = "label";
    label.textContent = node.name;
    row.appendChild(label);

    if (state.selectedFile === node.path) row.classList.add("active");
    wrap.appendChild(row);

    if (node.type === "dir") {
      const childrenWrap = document.createElement("div");
      childrenWrap.className = "children";
      childrenWrap.hidden = true;
      wrap.appendChild(childrenWrap);

      row.addEventListener("click", async () => {
        const isOpen = !childrenWrap.hidden;
        if (isOpen) {
          childrenWrap.hidden = true;
          twist.textContent = "\u25B8 ";
        } else {
          if (!childrenWrap.dataset.loaded) {
            try {
              const data = await fetchJSON(`/api/children?path=${encodeURIComponent(node.path)}`);
              for (const child of data.children) {
                childrenWrap.appendChild(renderNode(child, depth + 1));
              }
              childrenWrap.dataset.loaded = "1";
            } catch (e) {
              console.error(e);
            }
          }
          childrenWrap.hidden = false;
          twist.textContent = "\u25BE ";
        }
      });
    } else {
      row.addEventListener("click", () => openFile(node.path));
    }
    return wrap;
  }

  async function loadTree() {
    const data = await fetchJSON("/api/tree");
    state.tree = data;
    state.flatSortedMds = collectSortedMds(data);
    const root = $("#tree");
    root.innerHTML = "";
    for (const child of data.children) {
      root.appendChild(renderNode(child, 1));
    }
  }

  function collectSortedMds(node, acc) {
    acc = acc || [];
    if (node.type === "file" && node.path) acc.push(node.path);
    for (const c of node.children || []) collectSortedMds(c, acc);
    acc.sort();
    return acc;
  }

  // ===== File open / render =====
  const content = $("#content");

  function fmtSize(n) {
    if (n < 1024) return n + " B";
    if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
    return (n / 1024 / 1024).toFixed(2) + " MB";
  }

  function fmtMtime(t) {
    const d = new Date(t * 1000);
    const p = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
  }

  async function openFile(path, opts) {
    opts = opts || {};
    state.selectedFile = path;
    state.renderedFormat = opts.format || "rendered";
    saveLS();
    history.replaceState(null, "", `?p=${encodeURIComponent(path)}`);

    $$(".tree .node.active").forEach((n) => n.classList.remove("active"));
    const row = document.querySelector(`.tree .node[data-path="${cssEscape(path)}"]`);
    if (row) row.classList.add("active");

    let data;
    try {
      data = await fetchJSON(`/api/file?path=${encodeURIComponent(path)}&format=${state.renderedFormat}`);
    } catch (e) {
      content.innerHTML = `<div class="empty">加载失败: ${escapeHtml(e.message)}</div>`;
      return;
    }

    const meta = data.meta;
    const metaText = meta
      ? `${meta.path} \u00B7 ${fmtSize(meta.size)} \u00B7 ${fmtMtime(meta.mtime)}`
      : "";
    $("#file-meta").textContent = metaText;

    const kind = data.kind || "markdown";

    // Markdown + raw: render the raw markdown text in a <pre> (v1 behavior).
    if (kind === "markdown" && state.renderedFormat === "raw") {
      $("#toggle-raw").disabled = false;
      $("#toggle-raw").textContent = "Rendered";
      content.innerHTML = `<div class="meta">${metaText}</div><pre><code>${escapeHtml(data.text || "")}</code></pre>`;
      $("#toc").hidden = true;
      document.body.classList.add("no-toc");
      revealSelectedInTree();
      return;
    }

    document.body.classList.remove("no-toc");
    updateRawButton(kind, state.renderedFormat);

    // JSON parse error: show a banner above the highlighted source.
    const errorLine =
      kind === "code-error" && data.error
        ? `<div class="code-error">\u26A0 JSON \u8BED\u6CD5\u9519\u8BEF\uFF1A${escapeHtml(data.error)}</div>`
        : "";

    content.innerHTML = `<div class="meta">${metaText}</div>${errorLine}${data.html || ""}`;

    if (kind === "markdown") {
      hydrateContent();
      renderToc(data.toc || []);
    } else {
      // code / html: no cross-file links or TOC; code views still get copy buttons
      hydrateCopyButtons();
      renderToc([]);
    }

    // Reveal in tree (lazy-loads branches along the way)
    revealSelectedInTree();
  }

  function updateRawButton(kind, format) {
    const btn = $("#toggle-raw");
    if (!btn) return;
    if (kind === "code") {
      btn.hidden = true;
      return;
    }
    btn.hidden = false;
    if (kind === "html") {
      btn.disabled = false;
      btn.textContent = format === "raw" ? "Preview" : "Source";
    } else {
      btn.disabled = false;
      btn.textContent = format === "raw" ? "Rendered" : "Raw";
    }
  }

  function hydrateCopyButtons() {
    content.querySelectorAll("pre.copyable-code").forEach((pre) => {
      pre.addEventListener("click", (e) => {
        if (e.target !== pre && !e.target.matches("code")) return;
        const code = pre.querySelector("code");
        const text = code ? code.textContent : pre.textContent;
        if (navigator.clipboard) {
          navigator.clipboard.writeText(text).then(
            () => {
              pre.classList.add("copied");
              setTimeout(() => pre.classList.remove("copied"), 1200);
            },
            () => {}
          );
        }
      });
    });
  }

  let revealSeq = 0;
  function revealSelectedInTree() {
    const seq = ++revealSeq;
    const path = state.selectedFile;
    if (!path) return Promise.resolve();

    const parts = path.split("/").filter(Boolean);
    if (parts.length < 2) return Promise.resolve(); // root-level file → nothing to expand

    const dirSegments = parts.slice(0, -1);
    let curPath = "";

    return (async () => {
      for (const seg of dirSegments) {
        if (seq !== revealSeq) return;
        curPath += "/" + seg;
        const dirRow = document.querySelector(
          `.tree .node.dir[data-path="${cssEscape(curPath)}"]`
        );
        if (!dirRow) return; // not in tree (probably search-results state)
        const wrap = dirRow.nextElementSibling;
        if (!(wrap && wrap.classList.contains("children") && wrap.hidden)) continue;

        if (!wrap.dataset.loaded) {
          try {
            const data = await fetchJSON(
              `/api/children?path=${encodeURIComponent(curPath)}`
            );
            if (seq !== revealSeq) return;
            wrap.innerHTML = "";
            for (const child of data.children || []) {
              wrap.appendChild(renderNode(child, 1));
            }
            wrap.dataset.loaded = "1";
          } catch (e) {
            console.warn("reveal: failed to load", curPath, e);
            return;
          }
        }
        wrap.hidden = false;
        const twist = dirRow.querySelector(".twist");
        if (twist) twist.textContent = "\u25BE ";
      }

      if (seq !== revealSeq) return;
      const fileRow = document.querySelector(
        `.tree .node.file[data-path="${cssEscape(path)}"]`
      );
      if (fileRow) fileRow.scrollIntoView({ block: "center", behavior: "smooth" });
    })();
  }

  async function refreshTree() {
    const btn = $("#refresh-tree");
    if (!btn || btn.classList.contains("spinning")) return;
    btn.classList.add("spinning");
    btn.disabled = true;
    try {
      // 1. Re-fetch root tree and re-render
      const data = await fetchJSON("/api/tree");
      state.tree = data;
      state.flatSortedMds = collectSortedMds(data);
      const root = $("#tree");
      root.innerHTML = "";
      for (const child of data.children || []) {
        root.appendChild(renderNode(child, 1));
      }
      // 2. Re-load current file (if any)
      if (state.selectedFile) {
        await openFile(state.selectedFile, { format: state.renderedFormat });
      }
      // 3. Reveal current file in the fresh tree
      await revealSelectedInTree();
    } catch (e) {
      console.error("refreshTree failed", e);
    } finally {
      btn.classList.remove("spinning");
      btn.disabled = false;
    }
  }

  function hydrateContent() {
    // Internal markdown links: prefer server-rewritten /api/file links, with
    // a client-side fallback for unresolved relative hrefs.
    content.querySelectorAll("a[href]").forEach((a) => {
      const p = resolveLocalContentPath(a.getAttribute("href") || "");
      if (!p) return;
      a.addEventListener("click", (e) => {
        e.preventDefault();
        openFile(p);
      });
    });

    // Image error fallback
    content.querySelectorAll("img").forEach((img) => {
      img.addEventListener("error", () => {
        const alt = img.alt || img.src.split("/").pop();
        img.replaceWith(makeBrokenImage(alt));
      });
    });

    // Copy buttons on code blocks
    content.querySelectorAll("pre.copyable-code").forEach((pre) => {
      pre.addEventListener("click", (e) => {
        if (e.target !== pre && !e.target.matches("code")) return;
        const code = pre.querySelector("code");
        const text = code ? code.textContent : pre.textContent;
        if (navigator.clipboard) {
          navigator.clipboard.writeText(text).then(
            () => {
              pre.classList.add("copied");
              setTimeout(() => pre.classList.remove("copied"), 1200);
            },
            () => {}
          );
        }
      });
    });
  }

  function makeBrokenImage(alt) {
    const span = document.createElement("span");
    span.className = "img broken";
    span.textContent = `[图片加载失败: ${alt}]`;
    return span;
  }

  // ===== TOC =====
  function renderToc(toc) {
    const list = $("#toc-list");
    list.innerHTML = "";
    if (!toc || !toc.length) {
      $("#toc").hidden = true;
      document.body.classList.add("no-toc");
      return;
    }
    $("#toc").hidden = false;
    document.body.classList.remove("no-toc");
    for (const item of toc) {
      const li = document.createElement("li");
      li.className = `lv-${item.level}`;
      const a = document.createElement("a");
      a.href = `#${item.id}`;
      a.textContent = item.text;
      a.dataset.targetId = item.id;
      a.addEventListener("click", (e) => {
        e.preventDefault();
        const target = document.getElementById(item.id);
        if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
      });
      li.appendChild(a);
      list.appendChild(li);
    }
    setupScrollSpy();
  }

  let scrollSpyObserver = null;
  function setupScrollSpy() {
    if (scrollSpyObserver) scrollSpyObserver.disconnect();
    const headings = $$(".content h1, .content h2, .content h3");
    if (!headings.length) return;
    const linkById = new Map();
    $$("#toc-list a").forEach((a) => linkById.set(a.dataset.targetId, a));
    scrollSpyObserver = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        $$("#toc-list a.active").forEach((a) => a.classList.remove("active"));
        if (visible.length) {
          const id = visible[0].target.id;
          const link = linkById.get(id);
          if (link) link.classList.add("active");
        }
      },
      { rootMargin: "0px 0px -75% 0px", threshold: 0 }
    );
    headings.forEach((h) => scrollSpyObserver.observe(h));
  }

  // ===== Search =====
  let searchTimer = null;
  function onSearchInput(e) {
    const q = e.target.value.trim();
    clearTimeout(searchTimer);
    if (!q) {
      clearSearch();
      return;
    }
    searchTimer = setTimeout(async () => {
      try {
        const data = await fetchJSON(`/api/search?q=${encodeURIComponent(q)}`);
        renderSearchResults(data.matches);
      } catch (err) {
        console.error(err);
      }
    }, 300);
  }

  function clearSearch() {
    const root = $("#tree");
    root.innerHTML = "";
    for (const child of state.tree.children || []) {
      root.appendChild(renderNode(child, 1));
    }
  }

  function renderSearchResults(matches) {
    const root = $("#tree");
    root.innerHTML = "";
    if (!matches.length) {
      root.innerHTML = '<div class="empty">无匹配</div>';
      return;
    }
    for (const m of matches) {
      const row = document.createElement("div");
      row.className = "node file";
      row.dataset.path = m.path;
      const twist = document.createElement("span");
      twist.className = "twist";
      twist.textContent = "  ";
      row.appendChild(twist);
      const label = document.createElement("span");
      label.className = "label";
      label.textContent = m.path;
      row.appendChild(label);
      row.addEventListener("click", () => openFile(m.path));
      root.appendChild(row);
    }
  }

  // ===== Keyboard =====
  function gotoSibling(delta) {
    if (!state.flatSortedMds.length) return;
    let i = state.selectedFile
      ? state.flatSortedMds.indexOf(state.selectedFile)
      : -1;
    i = i < 0 ? 0 : Math.max(0, Math.min(state.flatSortedMds.length - 1, i + delta));
    openFile(state.flatSortedMds[i]);
  }

  document.addEventListener("keydown", (e) => {
    // === Global: Escape blurs input / clears search ===
    if (e.key === "Escape") {
      if (e.target.matches("input, textarea")) {
        e.target.blur();
        if (e.target.id === "search") {
          e.target.value = "";
          clearSearch();
        }
      }
      return;
    }

    // === From here on, ignore keys when typing in an input ===
    if (e.target.matches("input, textarea")) return;

    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      $("#search").focus();
      return;
    }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "b") {
      e.preventDefault();
      state.sidebarVisible = !state.sidebarVisible;
      saveLS();
      applySidebar();
      return;
    }
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === "l") {
      e.preventDefault();
      state.theme = state.theme === "dark" ? "light" : state.theme === "light" ? "auto" : "dark";
      saveLS();
      applyTheme();
      return;
    }
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === "r") {
      e.preventDefault();
      refreshTree();
      return;
    }
    if (e.key === "F5") {
      e.preventDefault();
      refreshTree();
      return;
    }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "r") {
      e.preventDefault();
      if (state.selectedFile) openFile(state.selectedFile, { format: state.renderedFormat });
      return;
    }
    if (e.key === "j" || (e.altKey && e.key === "ArrowDown")) {
      e.preventDefault();
      gotoSibling(1);
      return;
    }
    if (e.key === "k" || (e.altKey && e.key === "ArrowUp")) {
      e.preventDefault();
      gotoSibling(-1);
      return;
    }
    if (e.key === "r") {
      if (!state.selectedFile) return;
      const ext = state.selectedFile.split(".").pop().toLowerCase();
      if (ext === "py" || ext === "json") return; // no toggle for code
      openFile(state.selectedFile, {
        format: state.renderedFormat === "raw" ? "rendered" : "raw",
      });
    }
  });

  // ===== Wiring =====
  $("#toggle-sidebar").addEventListener("click", () => {
    state.sidebarVisible = !state.sidebarVisible;
    saveLS();
    applySidebar();
  });
  $("#toggle-theme").addEventListener("click", () => {
    state.theme = state.theme === "dark" ? "light" : state.theme === "light" ? "auto" : "dark";
    saveLS();
    applyTheme();
  });
  $("#toggle-raw").addEventListener("click", () => {
    if (state.selectedFile)
      openFile(state.selectedFile, {
        format: state.renderedFormat === "raw" ? "rendered" : "raw",
      });
  });
  $("#refresh-tree").addEventListener("click", refreshTree);
  $("#search").addEventListener("input", onSearchInput);

  window
    .matchMedia("(prefers-color-scheme: dark)")
    .addEventListener("change", () => {
      if (state.theme === "auto") applyTheme();
    });

  // ===== Boot =====
  loadLS();
  applyTheme();
  applySidebar();
  loadTree().then(() => {
    const params = new URLSearchParams(location.search);
    const fromUrl = params.get("p");
    const initial = fromUrl || state.selectedFile;
    if (initial) {
      openFile(initial).then(() => revealSelectedInTree());
    }
  });
})();
