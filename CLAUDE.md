# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repo is a **marimo WebAssembly + GitHub Pages site**. Each `.py` file under `notebooks/` and `apps/` is a standalone marimo notebook that gets exported to a static HTML/WASM page by `.github/scripts/build.py` and published to GitHub Pages via `.github/workflows/deploy.yml` on every push to `main`.

- `notebooks/` — exported with `marimo export html-wasm --mode edit` (interactive, code visible).
- `apps/` — exported with `--mode run --no-show-code` (dashboard-style, code hidden).
- `public/` directories next to a notebook hold the assets (CSVs, JSON, images) that the notebook loads at runtime.
- `templates/` — Jinja2 templates (`index.html.j2`, `bare.html.j2`, `tailwind.html.j2`) used to render the `_site/index.html` landing page that links to every exported notebook. `tailwind.html.j2` is the default.
- The real content today is the `bench_analysis.py` notebook (hash-container benchmark viewer).

## Critical runtime constraint: dual local / WASM execution

Every notebook must work in **two** runtimes, because the same file is both executed locally during development and shipped as WebAssembly to browsers.

`mo.notebook_location()` is the portable way to reach assets, but it returns **different types** in each mode:

- **Local** (`marimo edit` / `marimo run` / `uv run`): a `pathlib.Path`.
- **WASM** (pyodide): a `URLPath` (a `PurePosixPath` subclass) whose `str()` yields `https://…`.

Code that reads from `notebook_location()` must dispatch on the type. The pattern used in `notebooks/bench_analysis.py:18` is:

```python
from pathlib import Path

def _read_csv(path):
    if isinstance(path, Path):
        return pd.read_csv(path)          # local filesystem
    with urllib.request.urlopen(str(path)) as resp:  # WASM URL
        return pd.read_csv(io.BytesIO(resp.read()))
```

A mirror helper `_read_text` is used for the JSON infolog files in the same notebook. Do **not** call `urllib.request.urlopen` on a bare local `Path` — it fails with `ValueError: unknown url type: '/Users/…/file.csv'` because local paths lack a URL scheme. Pandas' `read_csv` is happy with both a `Path` and a URL string if you prefer a one-liner, but keeping the urllib branch preserves the exact WASM behavior the site was shipped with.

`mo.notebook_dir()` is **not** a substitute — it only works locally.

## Common commands

```bash
# Edit a notebook interactively
marimo edit notebooks/bench_analysis.py

# Run a notebook as a read-only dashboard
marimo run apps/bench_analysis.py

# Headless smoke test (imports/executes cells)
uv run notebooks/bench_analysis.py

# Full site export (matches what CI runs)
uv run build.py
```

## Adding a new notebook

1. Drop a marimo `.py` file into `notebooks/` (edit mode) or `apps/` (run mode).
2. Put any data it loads under a sibling `public/` directory and reference it via `mo.notebook_location() / "public" / …` with the dispatch pattern above.
3. `uv run build.py` — confirm it shows up in `_site/index.html` and the exported HTML loads the assets.
4. Push to `main`; the `Deploy to GitHub Pages` workflow will publish it.

The build script's `_export` walks every `*.py` under the folder recursively, so nested directories are fine.

## bench_analysis.py specifics

The notebook renders three tabs (`mo.ui.tabs(..., lazy=True)`):

- **Regular Bench** — bar charts from `regular_bench_<lf>_<no|yes>_reserve.csv` (1M ops × 100 iters). Filtered by `Container` dropdown and `reserve` radio.
- **Scaling Benchmarks** — line charts from `load_factor_<lf>.csv` (100k ops × 10 iters). Filtered by load-factor dropdown; y-axis can be fixed or independent per facet.
- **Sim Frame Timing** — bar chart + per-run table from `lf_<lf>_infolog_<run>.json`. The JSON files are actually Lua-table-formatted text; `_parse_lua_table` in cell 3 parses them without a dependency.

CSV columns: `Container`, `Workload`, `Impl`, `Benchmark` (value like `N= 1000`), `Mean (ns)`, `Iterations`, `Samples`. The notebook strips the headers, extracts `N` with the regex `N=\s*(\d+)`, and rescales `Mean (ns)` by dividing out the ops-per-iteration (100k for scaling, 1M for regular).

Implementation color scheme (re-declared in each chart cell): `spring` → `#1f77b4`, `unsynced` → `#ff7f0e`, `std` → `#2ca02c`.
