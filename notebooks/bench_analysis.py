import marimo

__generated_with = "0.23.0"
app = marimo.App(width="full")


@app.cell
def _():
    import re

    import altair as alt
    import marimo as mo
    import pandas as pd

    # Load all load_factor CSV files
    bench_dir = mo.notebook_location() / "public" / "bench_results"
    load_factors = ["0.33", "0.5", "0.66"]

    dfs = []
    for lf in load_factors:
        f = bench_dir / f"load_factor_{lf}.csv"
        _df = pd.read_csv(str(f), compression=None)
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
            _df = pd.read_csv(str(f), compression=None)
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
    return datatype_dropdown, lf_dropdown, reserve_radio


@app.cell
def _(alt, lf_bench_df, lf_dropdown, mo):
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

    _y_min = _df["Mean (ns)"].min()
    _y_max = _df["Mean (ns)"].max()
    _y_scale = alt.Scale(domain=[_y_min * 0.95, _y_max * 1.05])

    _rows = []
    for _container in _containers:
        _row_charts = []
        _container_data = _df[_df["Container"] == _container]

        for _workload in _workloads:
            _subset = _container_data[_container_data["Workload"] == _workload]
            _chart = (
                alt.Chart(_subset)
                .mark_line(point=True, strokeWidth=1.5, opacity=0.8)
                .encode(
                    x=alt.X("N:Q", title="Size of container"),
                    y=alt.Y("Mean (ns):Q", scale=_y_scale, title="Mean (ns/op)", axis=alt.Axis(labelExpr="datum.value + ' ns'")),
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
    lf_tab = mo.vstack([lf_dropdown, _chart_grid])
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
def _(lf_tab, mo, reg_tab):
    mo.ui.tabs({
        "Regular Bench": reg_tab,
        "Scaling Benchmarks": lf_tab,
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
