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
    sidebarVisible: true,
    tree: { children: [] },
    flatSortedMds: [],
  };

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));

  function loadLS() {
    state.selectedFile = localStorage.getItem(LS.selectedFile) || null;
    state.theme = localStorage.getItem(LS.theme) || "auto";
    state.sidebarVisible = localStorage.getItem(LS.sidebarVisible) !== "false";
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
    $("#file-meta").textContent = meta
      ? `${meta.path} \u00B7 ${fmtSize(meta.size)} \u00B7 ${fmtMtime(meta.mtime)}`
      : "";
    $("#toggle-raw").disabled = false;
    $("#toggle-raw").textContent = state.renderedFormat === "raw" ? "Rendered" : "Raw";

    if (state.renderedFormat === "raw") {
      content.innerHTML = `<div class="meta">${meta.path} \u00B7 ${fmtSize(meta.size)} \u00B7 ${fmtMtime(meta.mtime)}</div><pre><code>${escapeHtml(data.text)}</code></pre>`;
      $("#toc").hidden = true;
      document.body.classList.add("no-toc");
      return;
    }

    document.body.classList.remove("no-toc");
    content.innerHTML = `<div class="meta">${meta.path} \u00B7 ${fmtSize(meta.size)} \u00B7 ${fmtMtime(meta.mtime)}</div>${data.html}`;
    hydrateContent();
    renderToc(data.toc || []);
  }

  function hydrateContent() {
    // Wikilinks / cross-file links: intercept clicks
    content.querySelectorAll('a[href*="/api/file?path="]').forEach((a) => {
      const url = new URL(a.href, location.origin);
      const p = url.searchParams.get("path");
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
      if (state.selectedFile)
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
    if (initial) openFile(initial);
  });
})();
