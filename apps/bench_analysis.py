import marimo

__generated_with = "0.23.0"
app = marimo.App(width="full")


@app.cell
def _():
    import io
    import re
    import urllib.request
    from pathlib import Path

    import altair as alt
    import marimo as mo
    import pandas as pd

    def _read_csv(path):
        if isinstance(path, Path):
            return pd.read_csv(path)
        with urllib.request.urlopen(str(path)) as resp:
            return pd.read_csv(io.BytesIO(resp.read()))

    # Load all load_factor CSV files
    bench_dir = mo.notebook_location() / "public" / "bench_results"
    load_factors = ["0.33", "0.5", "0.66"]

    dfs = []
    for lf in load_factors:
        f = bench_dir / f"load_factor_{lf}.csv"
        _df = _read_csv(f)
        _df["load_factor"] = lf
        dfs.append(_df)

    lf_bench_df = pd.concat(dfs, ignore_index=True)
    lf_bench_df.columns = lf_bench_df.columns.str.strip()
    lf_bench_df["N"] = lf_bench_df["Benchmark"].str.extract(r"N=\s*(\d+)").astype(int)
    lf_bench_df["Mean (ns)"] = lf_bench_df["Mean (ns)"] / 100000

    # Load all regular_bench CSV files
    reserves = ["no_reserve", "yes_reserve"]

    reg_dfs = []
    for lf in load_factors:
        for res in reserves:
            f = bench_dir / f"regular_bench_{lf}_{res}.csv"
            _df = _read_csv(f)
            _df["load_factor"] = lf
            _df["reserve"] = res
            reg_dfs.append(_df)

    reg_bench_df = pd.concat(reg_dfs, ignore_index=True)
    reg_bench_df.columns = reg_bench_df.columns.str.strip()
    reg_bench_df["N"] = reg_bench_df["Benchmark"].str.extract(r"N=\s*(\d+)").astype(int)
    reg_bench_df["Mean (ns)"] = reg_bench_df["Mean (ns)"] / 1000000
    return alt, lf_bench_df, mo, reg_bench_df


@app.cell
def _(lf_bench_df, mo, reg_bench_df):
    _lf_options = sorted(lf_bench_df["load_factor"].unique())
    lf_dropdown = mo.ui.dropdown(
        options={f"Load Factor {lf}": lf for lf in _lf_options},
        value=f"Load Factor {_lf_options[0]}",
        label="Load Factor",
    )
    _container_order = [
        "Map<uintptr_t,int>", "Map<string,string>", "Map<int,int>",
        "Set<int>", "Set<string>",
    ]
    _available = [c for c in _container_order if c in reg_bench_df["Container"].values]
    datatype_dropdown = mo.ui.dropdown(
        options=_available,
        value=_available[0],
        label="Data Type",
    )
    reserve_radio = mo.ui.radio(
        options={"No reserve(2*N)": "no_reserve", "With reserve(2*N)": "yes_reserve"},
        value="No reserve(2*N)",
        label="Upfront reserve",
    )
    lf_y_scale_radio = mo.ui.radio(
        options={"Fixed": "fixed", "Independent": "independent"},
        value="Fixed",
        label="Y-axis scaling",
    )
    sim_scale_radio = mo.ui.radio(
        options={"Absolute": "absolute", "Relative to lf=0.66": "relative"},
        value="Absolute",
        label="Scale",
    )
    return datatype_dropdown, lf_dropdown, lf_y_scale_radio, reserve_radio, sim_scale_radio


@app.cell
def _(alt, lf_bench_df, lf_dropdown, lf_y_scale_radio, mo):
    _df = lf_bench_df[lf_bench_df["load_factor"] == lf_dropdown.value].copy()

    _impl_colors = {
        "spring": "#1f77b4",
        "unsynced": "#ff7f0e",
        "std": "#2ca02c",
    }
    _color_scale = alt.Scale(
        domain=list(_impl_colors.keys()),
        range=list(_impl_colors.values()),
    )

    _container_order = ["Map<ptr,int>", "Map<string,string>", "Map<int,int>"]
    _containers = [c for c in _container_order if c in _df["Container"].values]
    _workloads = sorted(_df["Workload"].unique())

    _fixed = lf_y_scale_radio.value == "fixed"
    _y_min = _df["Mean (ns)"].min()
    _y_max = _df["Mean (ns)"].max()
    _global_y_scale = alt.Scale(domain=[_y_min * 0.95, _y_max * 1.05])

    _rows = []
    for _container in _containers:
        _row_charts = []
        _container_data = _df[_df["Container"] == _container]

        for _workload in _workloads:
            _subset = _container_data[_container_data["Workload"] == _workload]
            _y_enc = alt.Y("Mean (ns):Q", title="Mean (ns/op)", axis=alt.Axis(labelExpr="datum.value + ' ns'"))
            if _fixed:
                _y_enc = _y_enc.scale(_global_y_scale)
            _chart = (
                alt.Chart(_subset)
                .mark_line(point=True, strokeWidth=1.5, opacity=0.8)
                .encode(
                    x=alt.X("N:Q", title="Size of container"),
                    y=_y_enc,
                    color=alt.Color("Impl:N", scale=_color_scale, title="Implementation"),
                    tooltip=["Impl:N", "N:Q", "Mean (ns):Q"],
                )
                .properties(
                    title=f"{_container} - {_workload}",
                    width=350,
                    height=250,
                )
            )
            _row_charts.append(_chart)
        _rows.append(alt.hconcat(*_row_charts))

    _chart_grid = mo.ui.altair_chart(
        alt.vconcat(*_rows).properties(
            title=alt.TitleParams(
                f"Scaling Benchmarks (load factor = {lf_dropdown.value})",
                fontSize=18,
                subtitle="Examining behaviour of a varying N for each given load factor. 100,000 ops per iteration, 10 iterations per run",
            )
        )
    )
    lf_tab = mo.vstack([mo.hstack([lf_dropdown, lf_y_scale_radio], justify="start"), _chart_grid])
    return (lf_tab,)


@app.cell
def _(alt, datatype_dropdown, mo, reg_bench_df, reserve_radio):
    _df = reg_bench_df[
        (reg_bench_df["Container"] == datatype_dropdown.value)
        & (reg_bench_df["reserve"] == reserve_radio.value)
    ].copy()

    _impl_colors = {
        "spring": "#1f77b4",
        "unsynced": "#ff7f0e",
        "std": "#2ca02c",
    }
    _color_scale = alt.Scale(
        domain=list(_impl_colors.keys()),
        range=list(_impl_colors.values()),
    )

    _load_factors = sorted(_df["load_factor"].unique())
    _workloads = sorted(_df["Workload"].unique())

    _non_iter = _df[_df["Workload"] != "iterate"]
    _iter = _df[_df["Workload"] == "iterate"]
    _y_scale = alt.Scale(domain=[0, _non_iter["Mean (ns)"].max() * 1.05])
    _y_scale_iter = alt.Scale(domain=[0, _iter["Mean (ns)"].max() * 1.05])

    _rows = []
    for _lf in _load_factors:
        _row_charts = []
        _lf_data = _df[_df["load_factor"] == _lf]

        for _workload in _workloads:
            _subset = _lf_data[_lf_data["Workload"] == _workload]
            _wl_scale = _y_scale_iter if _workload == "iterate" else _y_scale
            _chart = (
                alt.Chart(_subset)
                .mark_bar(opacity=0.8)
                .encode(
                    x=alt.X("N:O", title="Size of container", axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("Mean (ns):Q", scale=_wl_scale, title="Mean (ns/op)", axis=alt.Axis(labelExpr="datum.value + ' ns'")),
                    color=alt.Color("Impl:N", scale=_color_scale, title="Implementation"),
                    xOffset="Impl:N",
                    tooltip=["Impl:N", "N:O", "Mean (ns):Q"],
                )
                .properties(
                    title=f"LoadFactor {_lf} - {_workload}",
                    width=350,
                    height=250,
                )
            )
            _row_charts.append(_chart)
        _rows.append(alt.hconcat(*_row_charts))

    _reserve_label = "with reserve(2*N)" if reserve_radio.value == "yes_reserve" else "no reserve"
    _chart_grid = mo.ui.altair_chart(
        alt.vconcat(*_rows).properties(
            title=alt.TitleParams(
                f"Regular Benchmarks — {datatype_dropdown.value} ({_reserve_label})",
                fontSize=18,
                subtitle="Examining spring vs. std:: implementations of hash containers. 1,000,000 ops per iteration, 100 iterations per run",
            )
        )
    )
    reg_tab = mo.vstack([mo.hstack([datatype_dropdown, reserve_radio], justify="start"), _chart_grid])
    return (reg_tab,)


@app.cell
def _(mo):
    import re as _re
    import urllib.request as _urllib_request
    from pathlib import Path as _Path

    def _read_text(path):
        if isinstance(path, _Path):
            return path.read_text()
        with _urllib_request.urlopen(str(path)) as _resp:
            return _resp.read().decode("utf-8")

    def _parse_lua_table(text):
        """Parse Lua-table-style benchmark output into a Python dict."""
        # Normalize: strip outer braces, handle nested tables recursively
        text = text.strip()
        if text.startswith("{") and text.endswith("}"):
            text = text[1:-1]

        result = {}
        i = 0
        while i < len(text):
            # Skip whitespace and commas
            while i < len(text) and text[i] in " \t\n\r,":
                i += 1
            if i >= len(text):
                break

            # [N]=value
            if text[i] == "[":
                end_bracket = text.index("]", i)
                key = text[i + 1 : end_bracket].strip()
                # Try int key
                try:
                    key = int(key)
                except ValueError:
                    pass
                i = end_bracket + 1
                assert text[i] == "="
                i += 1
            # key=value
            elif text[i].isalpha() or text[i] == "_":
                eq = text.index("=", i)
                key = text[i:eq].strip()
                i = eq + 1
            else:
                break

            # Parse value
            while i < len(text) and text[i] in " \t\n\r":
                i += 1

            if text[i] == "{":
                # Nested table - find matching brace
                depth = 1
                start = i
                i += 1
                while depth > 0:
                    if text[i] == "{":
                        depth += 1
                    elif text[i] == "}":
                        depth -= 1
                    i += 1
                value = _parse_lua_table(text[start:i])
            elif text[i] == '"':
                # String value
                end_quote = text.index('"', i + 1)
                value = text[i + 1 : end_quote]
                i = end_quote + 1
            else:
                # Number or identifier
                end = i
                while end < len(text) and text[end] not in ",\n}":
                    end += 1
                raw = text[i:end].strip()
                try:
                    value = int(raw)
                except ValueError:
                    try:
                        value = float(raw)
                    except ValueError:
                        value = raw
                i = end

            result[key] = value

        return result

    _bench_dir = mo.notebook_location() / "public" / "bench_results"

    _rows = []

    for _lf in ["0.25", "0.66"]:
        for _bmark, _prefix, _max_run in [
            ("fightertest", f"fightertest_lf_{_lf}_infolog_", 4),
            ("pathfinding", f"pathfinding_lf_{_lf}_infolog_", 5),
            ("collision", f"collision_lf_{_lf}_infolog_", 5),
        ]:
            for _run in range(1, _max_run + 1):
                _fname = f"{_prefix}{_run}.txt"
                try:
                    _text = _read_text(_bench_dir / _fname)
                except (FileNotFoundError, OSError):
                    continue
                _data = _parse_lua_table(_text)
                _sim = _data.get("Sim", {})
                _percentiles = _sim.get("percentiles", {})
                _rows.append({
                    "benchmark": _bmark,
                    "load_factor": _lf,
                    "run": _run,
                    "sim_mean_ms": _sim.get("mean", 0),
                    "sim_p99_ms": _percentiles.get(99, 0),
                })

    for _bmark, _prefix in [("fightertest_std", "fightertest_std"), ("pathfinding_std", "pathfinding_std")]:
        for _run in range(1, 6):
            _fname = f"{_prefix}_infolog_{_run}.txt"
            try:
                _text = _read_text(_bench_dir / _fname)
            except (FileNotFoundError, OSError):
                continue
            _data = _parse_lua_table(_text)
            _sim = _data.get("Sim", {})
            _percentiles = _sim.get("percentiles", {})
            _rows.append({
                "benchmark": _bmark,
                "load_factor": "std",
                "run": _run,
                "sim_mean_ms": _sim.get("mean", 0),
                "sim_p99_ms": _percentiles.get(99, 0),
            })

    import pandas as _pd

    sim_df = _pd.DataFrame(_rows)
    sim_avg_df = sim_df.groupby(["benchmark", "load_factor"], as_index=False).agg(
        sim_mean_ms=("sim_mean_ms", "mean"),
        sim_p99_ms=("sim_p99_ms", "mean"),
    )
    return sim_avg_df, sim_df


@app.cell
def _(alt, mo, sim_avg_df, sim_df, sim_scale_radio):
    import pandas as _pd2

    _melted = sim_avg_df.melt(
        id_vars=["benchmark", "load_factor"],
        value_vars=["sim_mean_ms", "sim_p99_ms"],
        var_name="metric",
        value_name="ms",
    )
    _melted["metric"] = _melted["metric"].map({
        "sim_mean_ms": "Mean",
        "sim_p99_ms": "99th Pct",
    })

    _relative = sim_scale_radio.value == "relative"

    def _make_chart(bmarks, title, subtitle, ref_bmark):
        if isinstance(bmarks, str):
            bmarks = [bmarks]
        _data = _melted[_melted["benchmark"].isin(bmarks)].copy()
        if _relative:
            _ref = _melted[
                (_melted["benchmark"] == ref_bmark) & (_melted["load_factor"] == "0.66")
            ].set_index("metric")["ms"]
            _data["ms"] = _data.apply(lambda r: r["ms"] / _ref[r["metric"]], axis=1)
            _y = alt.Y("ms:Q", title="vs lf=0.66", axis=alt.Axis(labelExpr="datum.value + 'x'"))
        else:
            _y = alt.Y("ms:Q", title="Frame Time", axis=alt.Axis(labelExpr="datum.value + ' ms'"))

        _bars = (
            alt.Chart(_data)
            .mark_bar(opacity=0.8)
            .encode(
                x=alt.X("metric:N", title=None, axis=alt.Axis(labelAngle=0)),
                y=_y,
                color=alt.Color("load_factor:N", title="Load Factor"),
                xOffset="load_factor:N",
                tooltip=["load_factor:N", "metric:N", alt.Tooltip("ms:Q", format=".3f")],
            )
        )
        _layers = [_bars]
        if _relative:
            _layers.append(
                alt.Chart(_pd2.DataFrame({"y": [1.0]}))
                .mark_rule(color="black", strokeDash=[4, 2])
                .encode(y="y:Q")
            )
        return (
            alt.layer(*_layers)
            .properties(width=300, height=300, title=alt.TitleParams(title, fontSize=15, subtitle=subtitle))
        )

    _chart = mo.hstack([
        mo.ui.altair_chart(_make_chart(
            ["fightertest", "fightertest_std"],
            "fightertest",
            "luarules fightertest corak armpw 650 10 2040",
            ref_bmark="fightertest",
        )),
        mo.ui.altair_chart(_make_chart(
            ["pathfinding", "pathfinding_std"],
            "fightertest pathfinding",
            "luarules fightertest armcv armck 11000 1 12000",
            ref_bmark="pathfinding",
        )),
        mo.ui.altair_chart(_make_chart(
            "collision",
            "fightertest collision",
            "luarules fightertest corak armpw 650 10 2040",
            ref_bmark="collision",
        )),
    ], justify="start")

    # Also show per-run detail table
    _detail = sim_df.copy()
    _detail.columns = ["Benchmark", "Load Factor", "Run", "Sim Mean (ms)", "Sim P99 (ms)"]

    sim_tab = mo.vstack([
        mo.md("## Sim Frame Timing"),
        sim_scale_radio,
        _chart,
        mo.md("### Per-run detail"),
        mo.ui.table(_detail),
    ])
    return (sim_tab,)


@app.cell
def _(lf_tab, mo, reg_tab, sim_tab):
    mo.ui.tabs({
        "Regular Bench": reg_tab,
        "Scaling Benchmarks": lf_tab,
        "Sim Frame Timing": sim_tab,
    }, lazy=True)
    return


@app.cell
def _():
    return


@app.cell
def _():
    return


@app.cell
def _():
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
