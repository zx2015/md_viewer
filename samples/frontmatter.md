# Frontmatter

This file demonstrates YAML frontmatter. In v1 it is rendered as plain
markdown (not specially parsed), so the `---` delimiters appear as horizontal
rules and the YAML key/value pairs as paragraphs.

---

title: Sample with frontmatter
author: Test
date: 2026-06-28
tags:

  - sample
  - test

---

## Below frontmatter

The block above is parsed by markdown-it-py's `front_matter_plugin` (which
exposes it as a `front_matter` token), but for v1 we render it as
markdown-style content. A future version could hide it behind a metadata panel.
