"""GIFT Habitat Explorer. In VSCode run run_streamlit.py to launch this app."""
from __future__ import annotations

import io
import json
from pathlib import Path
import sqlite3
import zipfile

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from bankfull_regressions import (BANKFULL_OPTIONS, CHAMP, CUSTOM, default_plot_settings,
                                 plot_export, plot_reach, regression_notes)
from habitat_engine import (CFS_PER_M3S, MONTHS, STATUS_LABELS, aggregate_period,
                            calculate_hydraulics, compute_monthly, curve_from_csvs, gift_diagnostics,
                            hydraulic_parameters, input_source_rows, reach_with_hydraulics,
                            month_range, native_habitat, network_export, selected_comid,
                            selected_plotly_comid)
from presentation import (COMPARISON_FIELDS, comparison_figure, flow_figure, map_records, map_view,
                          metric_scale, network_map, number, period_label, potential_maximum_note)
from prepare_data import load_settings
from runtime_data import hydraulic_model_signature, load_runtime_dataset, runtime_signature

settings = load_settings()
APP_TITLE, ROOT = settings.APP_TITLE, settings.ROOT
DATA_DIRECTORY = Path(settings.DATA_DIRECTORY).expanduser()
DATA_DIRECTORY = (ROOT / DATA_DIRECTORY).resolve() if not DATA_DIRECTORY.is_absolute() else DATA_DIRECTORY.resolve()


def data_signature():
    """Check sources and overview assets without touching native hydraulic files."""
    return runtime_signature(settings)


@st.cache_data(show_spinner=False, max_entries=2)
def cached_data(signature):
    return load_runtime_dataset(settings)


@st.cache_data(show_spinner=False, max_entries=12)
def cached_monthly(curve_json, signature):
    network, _ = cached_data(signature)
    return compute_monthly(network["features"], json.loads(curve_json))


@st.cache_data(show_spinner=False, max_entries=256)
def cached_hydraulics(comid, parameters, model_signature):
    """One physical solution per segment/input set, independent of life stage."""
    return calculate_hydraulics(parameters)


@st.cache_data(show_spinner=False, max_entries=96)
def cached_native(comid, curve_json, parameters, model_signature, summer_width, _reach):
    hyd = cached_hydraulics(comid, parameters, model_signature)
    return native_habitat(DATA_DIRECTORY, _reach, json.loads(curve_json), hydraulics=hyd)


@st.cache_data(show_spinner=False, max_entries=256)
def cached_reach_monthly(comid, curve_json, parameters, model_signature,
                         flows, summer_width, _reach):
    hyd = cached_hydraulics(comid, parameters, model_signature)
    return compute_monthly([reach_with_hydraulics(_reach, hyd)], json.loads(curve_json))


@st.cache_data(show_spinner=False, max_entries=24)
def cached_comparison(curve_json, signature, months, require_all, metric,
                      comparison, _features, _summary, overview_revision=0):
    """Cache the network points independently of the selected-reach marker."""
    figure, count = comparison_figure(_features, _summary, metric, comparison, None)
    return figure.to_dict(), count


@st.cache_data(show_spinner=False, max_entries=12)
def cached_network_csv(curve_json, signature, months, require_all, _features, _summary, _metadata,
                       overview_revision=0):
    return csv_bytes(network_export(_features, _summary, json.loads(curve_json)["id"], list(months), _metadata))


def map_content(features, summary, layer, metric, view_key):
    """Keep one map's immutable reach records in this user's session."""
    content = st.session_state.get("_map_content")
    if content is None or content["key"] != view_key:
        title, high, palette = metric_scale(features, summary, layer, metric)
        content = dict(key=view_key, title=title, high=high, palette=palette,
                       records=map_records(features, summary, layer, metric, high, palette),
                       allowed=frozenset(r["id"] for r in features),
                       views={None: map_view(features)},
                       valid_count=int(summary.hsi.notna().sum()))
        st.session_state._map_content = content
    return content


def csv_bytes(frame):
    return frame.to_csv(index=False).encode("utf-8-sig")


def curve_zip(curve):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for kind in ("depth", "velocity", "substrate"):
            columns = ["lower", "upper", "suit"] if kind == "substrate" else [kind, "suit"]
            z.writestr(f"{kind}.csv", pd.DataFrame(curve[kind], columns=columns).to_csv(index=False))
    return buffer.getvalue()


def apply_defaults(curve):
    start, end = curve.get("defaultStart", 6) + 1, curve.get("defaultEnd", 8) + 1
    st.session_state.period_mode = "Single month" if start == end else "Month range"
    st.session_state.start_month = start
    st.session_state.end_month = end
    st.session_state.single_month = curve.get("defaultMonth", start - 1) + 1
    st.session_state.inspect_month = start
    st.session_state.saved_months = {k: st.session_state[k] for k in ("start_month", "end_month", "single_month")}


def remember_month(key):
    st.session_state.saved_months[key] = st.session_state[key]


def period_mode_changed():
    # Hidden widgets are cleaned up by Streamlit. Restore their saved choices.
    for key, value in st.session_state.saved_months.items():
        st.session_state[key] = value


def active_curve(curves):
    if st.session_state.get("stage") == "custom":
        return st.session_state.custom_curve
    return next(c for c in curves if c["id"] == st.session_state.stage)


def stage_changed(curves):
    apply_defaults(active_curve(curves))


def map_selected(key, allowed):
    comid = selected_comid(st.session_state.get(key, {}), allowed)
    if comid is not None and comid != st.session_state.get("selected_id"):
        st.session_state.selected_id = comid
        st.session_state.selection_revision = st.session_state.get("selection_revision", 0) + 1


def comparison_selected(key, allowed):
    comid = selected_plotly_comid(st.session_state.get(key, {}), allowed)
    if comid is not None and comid != st.session_state.get("selected_id"):
        st.session_state.selected_id = comid
        st.session_state.selection_revision = st.session_state.get("selection_revision", 0) + 1
        st.session_state.view_focus = comid
        # A new map widget clears the previous read-only PyDeck selection and
        # centers the view on the reach selected in the scatterplot.
        st.session_state.view_revision += 1
        st.rerun("workspace")


def sidebar(curves):
    with st.sidebar:
        st.markdown("### GIFT\nHabitat Explorer")
        st.caption("UPPER GRANDE RONDE · EROM NETWORK")
        if "stage" not in st.session_state:
            st.session_state.stage = curves[0]["id"]
            apply_defaults(curves[0])
        if "pending_custom" in st.session_state:
            custom = st.session_state.pop("pending_custom")
            st.session_state.custom_curve = custom
            st.session_state.stage = "custom"
            apply_defaults(custom)
        options = {c["id"]: c["label"] for c in curves}
        if "custom_curve" in st.session_state:
            options["custom"] = st.session_state.custom_curve["label"]
        st.selectbox("Species / life stage", list(options), key="stage", format_func=options.get,
                     on_change=stage_changed, args=(curves,))
        curve = active_curve(curves)
        with st.expander("Use your own suitability curves"):
            st.caption("Upload one set of depth, velocity, and substrate CSVs. Coordinates use m, m/s, and mm; suitability ranges from 0 to 1.")
            with st.form("custom_curves"):
                label = st.text_input("Curve set name", value="Custom curves")
                depth = st.file_uploader("Depth CSV: depth, suit", type="csv", key="depth_upload")
                velocity = st.file_uploader("Velocity CSV: velocity, suit", type="csv", key="velocity_upload")
                substrate = st.file_uploader("Substrate CSV: lower, upper, suit", type="csv", key="substrate_upload")
                submitted = st.form_submit_button("Apply uploaded curves", width="stretch")
            if submitted:
                if any(f is None for f in (depth, velocity, substrate)):
                    st.error("Choose all three CSVs before applying.")
                else:
                    try:
                        custom = curve_from_csvs(depth.getvalue(), velocity.getvalue(), substrate.getvalue(), label, defaults=curve)
                        custom["periodNote"] = "Custom curves start with the previous life stage's assessment period. Set the months appropriate to your curves."
                        custom["periodSource"] = ""
                        st.session_state.pending_custom = custom
                        st.rerun()
                    except (ValueError, UnicodeError, pd.errors.ParserError) as exc:
                        st.error(str(exc))
            st.download_button("Download current CSV examples", curve_zip(curve), "gift_curve_examples.zip", mime="application/zip", on_click="ignore")
        st.divider()
        st.radio("EROM flow period", ["Single month", "Month range"], horizontal=True, key="period_mode", on_change=period_mode_changed)
        if st.session_state.period_mode == "Single month":
            st.selectbox("Month", range(1, 13), format_func=lambda m: MONTHS[m-1], key="single_month", on_change=remember_month, args=("single_month",))
            months = [int(st.session_state.single_month)]
            require_all = True
        else:
            a, b = st.columns(2)
            a.selectbox("From", range(1, 13), format_func=lambda m: MONTHS[m-1], key="start_month", on_change=remember_month, args=("start_month",))
            b.selectbox("Through", range(1, 13), format_func=lambda m: MONTHS[m-1], key="end_month", on_change=remember_month, args=("end_month",))
            months = month_range(int(st.session_state.start_month), int(st.session_state.end_month))
            require_all = st.checkbox("Require every selected month", value=True, key="require_all",
                help="When checked, habitat is withheld if any selected month is unsupported. Otherwise, the median uses available months and marks partial coverage.")
            st.caption("Ranges include both endpoints and can cross December.")
        st.button("Restore life-stage default", on_click=stage_changed, args=(curves,), width="stretch")
        st.caption(curve.get("periodNote", "Editable assessment period."))
        if curve.get("periodSource"):
            st.markdown(f"[Timing reference]({curve['periodSource']})")
        cfs = st.radio("Flow units", ["cfs", "m³/s"], horizontal=True, key="flow_units") == "cfs"
        st.divider()
        st.caption("Monthly flows are 1971–2000 climatological means, not current observations.")
        st.caption("GIFT Python model · GPL-3.0")
    return curve, months, require_all, cfs


def monthly_display(frame, cfs):
    factor, unit = (CFS_PER_M3S, "cfs") if cfs else (1, "m³/s")
    out = frame[["month", "q", "depth", "velocity", "width", "d", "v", "s", "hsi", "wua", "status"]].copy()
    out["month"] = out.month.map(lambda m: MONTHS[int(m)-1])
    out["q"] *= factor
    out["status"] = out.status.map(lambda s: STATUS_LABELS.get(s,s))
    return out.rename(columns={"month":"Month", "q":f"Flow ({unit})", "depth":"Mean depth (m)",
        "velocity":"Mean velocity (m/s)", "width":"Wetted width (m)", "d":"Depth suitability",
        "v":"Velocity suitability", "s":"Substrate suitability", "hsi":"HSI", "wua":"WUA (m²/m)", "status":"Availability"})


def inspector(reach, monthly, summary, months, cfs):
    st.caption("SELECTED SEGMENT")
    st.subheader(reach["name"])
    st.caption(f"COMID {reach['id']}")
    if st.session_state.get("inspect_month") not in months:
        st.session_state.inspect_month = months[0]
    detail = st.selectbox("Inspect month", months, format_func=lambda m: MONTHS[m-1], key="inspect_month")
    row = monthly[monthly.month.eq(detail)].iloc[0]
    factor, unit = (CFS_PER_M3S, "cfs") if cfs else (1, "m³/s")
    st.metric(f"{MONTHS[detail-1]} EROM flow ({unit})", number(row.q * factor if pd.notna(row.q) else None))
    table = pd.DataFrame({"Component": ["Mean depth", "Mean velocity", "Substrate D84"],
                          "Raw value": [f"{number(row.depth)} m", f"{number(row.velocity)} m/s", f"{number(reach['d84'],1)} mm"],
                          "Suitability": [number(row.d), number(row.v), number(row.s)]})
    st.dataframe(table, hide_index=True, width="stretch", height=145)
    a, b = st.columns(2)
    a.metric("Monthly HSI", number(row.hsi))
    b.metric("Monthly WUA (m²/m)", number(row.wua))
    if row.status not in ("ok", "zero_flow"):
        st.warning(STATUS_LABELS.get(row.status, row.status))
    else:
        st.caption(STATUS_LABELS[row.status])
    if reach["modelStatus"] != "ok":
        st.caption(reach["modelStatus"])
    if len(months) > 1:
        st.markdown(f"**{period_label(months)}** · {int(summary.validCount)}/{len(months)} supported months")
        st.caption(f"HSI {number(summary.hsi)} · WUA {number(summary.wua)} m²/m")
        if summary.status != "ok":
            st.caption(STATUS_LABELS.get(summary.status, summary.status))
    st.caption(f"Temperature score: {number(reach['temp'])} · Priority score: {number(reach['priority'])}")
    with st.expander("CHaMP Regression input values"):
        st.dataframe(pd.DataFrame([
            {"Input": label, "Value": reach.get(field), "Units": unit}
            for label, field, unit in (("Bankfull width", "bfWidth", "m"),
                ("Mean bankfull depth", "bfDepth", "m"), ("Maximum bankfull depth", "maxDepth", "m"),
                ("Channel slope", "slope", "m/m"), ("Substrate D84", "d84", "mm"))
        ]), hide_index=True, width="stretch")
    return detail


@st.fragment(key="workspace")
def workspace(network, curve, monthly, summary, months, cfs, signature):
    features = network["features"]
    if st.session_state.get("_overview_signature") != signature:
        st.session_state._overview_signature = signature
        st.session_state._evaluated_reaches = {}
        st.session_state._plot_choices = {}
        for key in list(st.session_state):
            if key.startswith("plot-"):
                st.session_state.pop(key, None)
    allowed_ids = {r["id"] for r in features}
    if st.session_state.get("selected_id") not in allowed_ids:
        st.session_state.selected_id = None
    selected_id = st.session_state.selected_id
    curve_json = json.dumps(curve, sort_keys=True)
    model_signature = hydraulic_model_signature()
    reach = next((r for r in features if r["id"] == selected_id), None)
    selected_monthly = selected_summary = None
    if reach is not None:
        parameters = hydraulic_parameters(reach)
        with st.spinner("Calculating the selected segment…"):
            hyd = cached_hydraulics(selected_id, parameters, model_signature)
            evaluated = reach_with_hydraulics(reach, hyd)
            selected_monthly = cached_reach_monthly(
                selected_id, curve_json, parameters, model_signature,
                tuple(row[0] for row in reach["months"]), reach.get("summerWidth"), reach)
        selected_summary = aggregate_period(selected_monthly, months, bool(summary.requireAll.iloc[0])).loc[selected_id]
        if any(row[4] == "pending_selection" for row in reach["months"]):
            if selected_id not in st.session_state._evaluated_reaches:
                st.session_state._evaluated_reaches[selected_id] = evaluated
        reach = evaluated
    overrides = st.session_state._evaluated_reaches
    # Shared comparison/export caches must distinguish which reaches were
    # evaluated, including two users who have evaluated the same number of IDs.
    overview_revision = tuple(sorted(overrides))
    if overrides:
        features = [overrides.get(r["id"], r) for r in features]
        updated = [cached_reach_monthly(
            r["id"], curve_json, hydraulic_parameters(r), model_signature,
            tuple(row[0] for row in r["months"]), r.get("summerWidth"), r)
            for r in overrides.values()]
        monthly = monthly.set_index(["id", "month"]).copy()
        for frame in updated:
            replacement = frame.set_index(["id", "month"])
            monthly.loc[replacement.index, replacement.columns] = replacement
        monthly = monthly.reset_index()
        summary = aggregate_period(monthly, months, bool(summary.requireAll.iloc[0]))
    pending = [r["id"] for r in features if any(row[4] == "pending_selection" for row in r["months"])]
    network = dict(network, features=features,
                   metadata=dict(network["metadata"], pendingHydraulics=pending))
    a, b, c = st.columns([3, 1.25, 1])
    layer = a.radio("Network layer", ["GIFT habitat", "Temperature", "Priority"], horizontal=True, key="network_layer")
    metric_labels = {"hsi":"HSI", "wua":"WUA"}
    if st.session_state.get("map_metric", "hsi") not in metric_labels:
        st.session_state.map_metric = "hsi"
    metric = b.selectbox("Habitat metric", list(metric_labels), format_func=metric_labels.get, key="map_metric")
    basemap = c.selectbox("Basemap", ["Light", "Dark", "Satellite"], key="basemap")
    if st.session_state.get("view_focus") not in allowed_ids:
        st.session_state.view_focus = None
    content = map_content(features, summary, layer, metric,
                          (signature, curve_json, tuple(months), bool(summary.requireAll.iloc[0]),
                           layer, metric, overview_revision))
    st.caption(f"{curve['label']} · {period_label(months)} · {content['valid_count']}/{len(features)} segments with habitat results")
    if pending:
        st.info(f"{len(pending)} segments await habitat calculation. Select a segment to calculate it; gray values are unavailable until evaluated.")
    if layer == "Temperature":
        st.info("Temperature scores describe juvenile-salmon suitability under the supplied interpretation of See et al. (2021). They do not change with the selected life stage or month.")
    elif layer == "Priority":
        st.caption("Map colors use the configured priority field, unchanged by life stage or flow period.")
    left, right = st.columns([2.6, 1], gap="large")
    with left:
        fit_a, fit_b, _ = st.columns([1, 1, 2])
        if fit_a.button("Fit network", width="stretch"):
            st.session_state.view_focus = None
            st.session_state.view_revision += 1
        if fit_b.button("Zoom to segment", width="stretch", disabled=selected_id is None):
            st.session_state.view_focus = selected_id
            st.session_state.view_revision += 1
        focus = st.session_state.get("view_focus")
        if focus not in content["views"]:
            content["views"][focus] = map_view(features, focus)
        deck = network_map(content["records"], content["views"][focus], selected_id, basemap)
        key = f"network-map-{st.session_state.view_revision}"
        st.pydeck_chart(
            deck, key=key, height=530, on_select=lambda: map_selected(key, content["allowed"]),
            selection_mode="single-object")
        colors = ",".join("rgb("+",".join(map(str,color))+")" for color in content["palette"])
        st.markdown(f'<div class="legend"><span>{content["title"]} &nbsp; 0</span><div style="background:linear-gradient(90deg,{colors})"></div><span>{number(content["high"])}</span></div>', unsafe_allow_html=True)
        st.caption(potential_maximum_note(layer, metric))
        st.caption("Higher values → greater suitability or priority. Gray = unavailable map value. Gold = selected segment. Select a reach on the map or in a comparison plot.")
    with right:
        if reach is None:
            st.info("Select a stream segment or comparison point to calculate its hydraulic and habitat curves.")
        else:
            inspector(reach, selected_monthly, selected_summary, months, cfs)
    if reach is not None:
        diagnostics_panel(reach, selected_monthly, selected_summary, months, cfs, curve, network["metadata"])
        flow_panel(reach, selected_monthly, months, cfs, curve_json, signature)
    comparison_panel(features, summary, selected_id, curve_json, months, signature, overview_revision)
    network_downloads(network, summary, curve, months, bool(summary.requireAll.iloc[0]), signature,
                      overview_revision)


def diagnostics_panel(reach, monthly, summary, months, cfs, curve, metadata):
    rows = monthly.set_index("month").loc[months].reset_index()
    if not rows[["hsi", "wua"]].isna().any().any() and pd.notna(summary.hsi) and pd.notna(summary.wua):
        return
    payload = gift_diagnostics(reach, monthly, summary, months, curve, metadata)
    with st.expander("GIFT inputs and unavailable-result diagnostics", expanded=True):
        st.markdown(f"**{reach['name']} (COMID: {reach['id']})**")
        source_label = "Selected plot" if reach.get("plotInputs") else "CHaMP Regression"
        st.caption(f"{source_label} · Hydraulic model: {reach['modelStatus']} · Period: {STATUS_LABELS.get(summary.status, summary.status)}")
        factor, flow_unit = (CFS_PER_M3S, "cfs") if cfs else (1.0, "m³/s")
        definitions = [
            ("Bankfull width", "bfWidth", "m", True),
            ("Mean bankfull depth", "bfDepth", "m", True),
            ("Maximum bankfull depth", "maxDepth", "m", True),
            ("Channel slope", "slope", "m/m", True),
            ("Substrate D84", "d84", "mm", True),
            ("Raw shape factor", "shapeRaw", "dimensionless", False),
            ("Shape factor used", "shapeUsed", "dimensionless", False),
            ("Minimum modeled flow", "qMin", flow_unit, False),
            ("Maximum modeled flow", "qMax", flow_unit, False),
            ("Native hydraulic levels", "nativeCount", "count", False),
        ]
        parameters = []
        for label, field, unit, required in definitions:
            value = payload["input_parameters"][field]
            missing = value is None or not np.isfinite(value)
            if field == "maxDepth" and reach.get("plotInputs") and not reach["plotInputs"]["maximum_depth_supplied"]:
                required = False
                status = "Not supplied for this plot"
            else:
                status = ("Missing required input" if required else "Unavailable") if missing else (
                "Invalid: must be positive" if required and value <= 0 else "Available")
            shown = value * factor if not missing and field in ("qMin", "qMax") else value
            parameters.append(dict(Parameter=label, Value="Unavailable" if missing else f"{shown:.6g}",
                                   Units=unit, Status=status))
        st.dataframe(pd.DataFrame(parameters), hide_index=True, width="stretch")
        shape_method = ("1 - mean bankfull depth / maximum bankfull depth" if reach.get("maxDepth") is not None
                        else "(bankfull width / mean bankfull depth) / 100")
        st.caption(f"Active curves: {curve['label']}. Shape factor = {shape_method}; no cap is applied.")
        curve_ranges = [
            {"Curve": "Depth", "Input range": f"{min(r[0] for r in curve['depth']):.6g} to {max(r[0] for r in curve['depth']):.6g}", "Units": "m"},
            {"Curve": "Velocity", "Input range": f"{min(r[0] for r in curve['velocity']):.6g} to {max(r[0] for r in curve['velocity']):.6g}", "Units": "m/s"},
            {"Curve": "Substrate classes", "Input range": "; ".join(f"[{lo:.6g}, {hi:.6g})" for lo, hi, _ in curve["substrate"]), "Units": "mm"},
        ]
        st.dataframe(pd.DataFrame(curve_ranges), hide_index=True, width="stretch")
        st.markdown("**Inputs and availability at each selected monthly flow**")
        st.dataframe(monthly_display(rows, cfs), hide_index=True, width="stretch")
        st.caption("Unavailable values are retained. Positive flows outside the modeled range are not extrapolated. The JSON download includes full input values and the active suitability curves in SI units.")
        st.download_button("Download GIFT inputs and diagnostics (JSON)",
                           json.dumps(payload, allow_nan=False, ensure_ascii=False, indent=2),
                           f"gift_{reach['id']}_diagnostics.json", mime="application/json", on_click="ignore")


def remember_plot_input(comid, field, key):
    st.session_state._plot_choices.setdefault(comid, {})[field] = st.session_state[key]


def reset_plot_inputs(reach):
    comid = reach["id"]
    st.session_state._plot_choices[comid] = default_plot_settings(reach)
    for field in default_plot_settings(reach):
        st.session_state.pop(f"plot-{comid}-{field}", None)


def plot_controls(reach):
    """Persist independent plot choices by COMID, including hidden custom inputs."""
    comid = reach["id"]
    st.session_state.setdefault("_plot_choices", {})
    choices = st.session_state._plot_choices.setdefault(comid, default_plot_settings(reach))
    with st.expander("Adjust selected-segment hydraulics", expanded=True):
        st.caption("These inputs apply to this segment's response curves and monthly plot results. "
                   "The network map and comparisons use CHaMP Regression.")
        columns = st.columns(2)
        for col, kind, label, field in ((columns[0], "width", "Bankfull width", "bfWidth"),
                                        (columns[1], "depth", "Mean bankfull depth", "bfDepth")):
            with col:
                name, key = kind+"_source", f"plot-{comid}-{kind}_source"
                st.session_state.setdefault(key, choices[name])
                st.selectbox(label+" source", BANKFULL_OPTIONS, key=key,
                             on_change=remember_plot_input, args=(comid, name, key))
                choices[name] = st.session_state[key]
                if choices[name] == CUSTOM:
                    name, key = "custom_"+kind, f"plot-{comid}-custom_{kind}"
                    value = choices.get(name)
                    value = float(value) if value is not None and np.isfinite(value) else 0.
                    st.session_state.setdefault(key, value)
                    st.number_input(label+" for plotting (m)", min_value=0., step=.01,
                                    format="%.4f", key=key,
                                    on_change=remember_plot_input, args=(comid, name, key))
                    choices[name] = st.session_state[key]
        slope_key = f"plot-{comid}-slope"
        slope = choices.get("slope")
        st.session_state.setdefault(slope_key, float(slope) if slope is not None and np.isfinite(slope) else 0.)
        slope_col, reset_col = st.columns([2, 1])
        slope_col.number_input("Slope for plotting (m/m)", min_value=0., step=.0001,
                               format="%.7f", key=slope_key,
                               on_change=remember_plot_input, args=(comid, "slope", slope_key))
        choices["slope"] = st.session_state[slope_key]
        reset_col.button("Reset plot inputs", key=f"reset-plot-{comid}", width="stretch",
                         on_click=reset_plot_inputs, args=(reach,))
        region = getattr(settings, "BIEGER_REGION", "IMP")
        for note in regression_notes(reach, choices, region):
            st.caption(note)
        if choices["width_source"] != CHAMP or choices["depth_source"] != CHAMP:
            st.caption("Maximum bankfull depth is not supplied. GIFT estimates shape factor from "
                       "(bankfull width / mean bankfull depth) / 100.")
    return plot_reach(reach, choices, region)


@st.fragment
def flow_panel(reach, selected_monthly, months, cfs, curve_json, signature):
    """Tab switches update the flow panel without redrawing the map."""
    selected_id = reach["id"]
    detail = st.session_state.inspect_month
    st.subheader("Habitat response to flow")
    st.caption(f"{reach['name']} (COMID: {selected_id}) · {json.loads(curve_json)['label']}")
    try:
        adjusted = plot_controls(reach)
    except (ValueError, KeyError) as exc:
        st.error(f"Plot inputs: {exc}")
        st.info("A flow-response curve is unavailable because this segment has missing hydraulic inputs "
                "or invalid plot values. Choose another regression or enter positive custom values.")
        return
    parameters = hydraulic_parameters(adjusted)
    try:
        hyd = cached_hydraulics(selected_id, parameters, hydraulic_model_signature())
    except ValueError as exc:
        st.error(f"Plot inputs: {exc}")
        return
    reach = reach_with_hydraulics(adjusted, hyd)
    selected_monthly = cached_reach_monthly(selected_id, curve_json, parameters,
        hydraulic_model_signature(), tuple(row[0] for row in reach["months"]), reach.get("summerWidth"), reach)
    a, b, c, d = st.columns(4)
    a.metric("Plot bankfull width (m)", number(reach["bfWidth"]))
    b.metric("Plot mean bankfull depth (m)", number(reach["bfDepth"]))
    c.metric("Plot slope (m/m)", f"{reach['slope']:.6g}")
    factor, unit = (CFS_PER_M3S, "cfs") if cfs else (1., "m³/s")
    d.metric(f"Plot bankfull flow ({unit})", number(reach.get("qMax")*factor if reach.get("qMax") is not None else None))
    native = cached_native(selected_id, curve_json, hydraulic_parameters(reach),
                           hydraulic_model_signature(), reach.get("summerWidth"), reach)
    if native.empty:
        st.info("A flow-response curve is unavailable because this segment has missing hydraulic inputs.")
    wua_tab, hsi_tab = st.tabs(["WUA", "HSI"], key="flow_tabs", on_change="rerun")
    for tab, field in ((wua_tab, "wua"), (hsi_tab, "hsi")):
        if tab.open:
            with tab:
                st.plotly_chart(flow_figure(native, selected_monthly, months, detail, field, cfs), width="stretch", key=f"flow-{field}")
    st.caption(f"Substrate suitability = {number(selected_monthly.iloc[0].s)} at predicted D84 = {number(reach['d84'],1)} mm. Dashed component curves use the right axis. Gold points are separately evaluated monthly results; pale shading spans the selected flows (a dotted line marks a single flow). No extrapolation beyond the modeled flow range.")
    details = st.expander("Monthly results for this segment", key="monthly_results", on_change="rerun")
    if details.open:
        with details:
            selected_rows = selected_monthly.set_index("month").loc[months].reset_index()
            selected_rows["D84_mm"] = reach["d84"]
            st.dataframe(monthly_display(selected_rows, cfs), hide_index=True, width="stretch")
            st.caption("Raw values refer to each listed month's exact flow; component suitability incorporates GIFT's within-reach distributions.")
            export = selected_rows.drop(columns=["summer_width", "normalized"]).rename(columns={"id":"COMID", "q":"EROM_Q_m3s", "depth":"mean_depth_m", "velocity":"mean_velocity_m_s", "width":"wetted_width_m", "wua":"WUA_m2_per_m"})
            st.download_button("Download monthly results (SI units)", csv_bytes(plot_export(export, reach)), f"gift_{selected_id}_monthly.csv", mime="text/csv", on_click="ignore")
            if not native.empty:
                st.download_button("Download full flow-response curve (SI units)", csv_bytes(plot_export(native.drop(columns=["normalized"]).rename(columns={"q":"Q_m3s","depth":"mean_depth_m","velocity":"mean_velocity_m_s","width":"wetted_width_m","wua":"WUA_m2_per_m"}), reach)), f"gift_{selected_id}_flow_curve.csv", mime="text/csv", on_click="ignore")


@st.fragment
def comparison_panel(features, summary, selected_id, curve_json, months, signature, overview_revision=0):
    st.divider()
    st.subheader("HSI comparisons")
    st.caption("Click a dot to select and locate its reach on the map. Values summarize the selected months; the HSI axis follows the observed maximum.")
    comparisons = list(COMPARISON_FIELDS)
    tabs = st.tabs(comparisons, key="comparison_tabs", on_change="rerun")
    for tab, comparison in zip(tabs, comparisons):
        if tab.open:
            with tab:
                base = cached_comparison(curve_json, signature, tuple(months), bool(summary.requireAll.iloc[0]),
                                         "hsi", comparison, features, summary, overview_revision)
                figure, count = comparison_figure(features, summary, "hsi", comparison, selected_id, base=base)
                key = f"selection-{st.session_state.selection_revision}-comparison-{comparison}"
                allowed = frozenset(r["id"] for r in features)
                st.plotly_chart(figure, width="stretch", key=key, selection_mode="points",
                                on_select=lambda key=key, allowed=allowed: comparison_selected(key, allowed))
                st.caption(f"{count} segments with both values. Each point represents one segment; this comparison does not establish causation.")


def network_downloads(network, summary, curve, months, require_all, signature, overview_revision=0):
    """Reuse the export until the overview or assessment settings change."""
    features = network["features"]
    export = cached_network_csv(json.dumps(curve, sort_keys=True), signature, tuple(months),
                                require_all, features, summary, network["metadata"], overview_revision)
    st.download_button("Download network period summary (CSV)", export, "gift_network_period_summary.csv", mime="text/csv", on_click="ignore")
    with st.expander("Coverage and input notes"):
        status_counts = summary.status.value_counts().rename_axis("Status").reset_index(name="Segments")
        status_counts["Status"] = status_counts.Status.map(lambda s: STATUS_LABELS.get(s,s))
        st.dataframe(status_counts, hide_index=True, width="stretch")
        st.caption(f"{int(summary.complete.sum())}/{len(features)} segments have every selected month. A positive flow outside the modeled range stays unavailable. A valid zero-flow month contributes zero HSI and WUA.")
        st.caption(f"Maximum bankfull depth joined for {network['metadata']['maxDepthMatches']} stream IDs; priority joined for {network['metadata']['priorityMatches']}. {len(network['metadata']['skippedHydraulics'])} segments have missing or invalid hydraulic inputs. Shape factors are used without capping; {len(network['metadata']['shapeFactorAbove07'])} exceed 0.7.")


def methods(network):
    metadata = network["metadata"]
    with st.expander("Input sources and field mappings"):
        st.caption("These are the files and columns used for the loaded model inputs. Source units are converted to SI for calculation. Edit settings.py, then use Reload input data in the sidebar or restart the app.")
        st.dataframe(pd.DataFrame(input_source_rows(metadata)), hide_index=True, width="stretch")
    with st.expander("Data, methods, and suitability curves"):
        st.markdown("""
**Network and joins.** The active files, layers, join keys, fields, and source units
are listed in **Input sources and field mappings**. Geometry, bankfull width,
mean depth, slope, D84, and monthly flows come from the configured streams layer.
Maximum depth and priority use their configured ID joins. Temperature uses the
explicitly configured streams or priority source. Missing values remain unavailable.

**Hydraulics and habitat.** The network uses **CHaMP Regression** inputs. Its shape factor is
`1 - mean bankfull depth / maximum bankfull depth`, without capping.
Selected-segment plots have independent width/depth sources: CHaMP Regression,
Bieger National, Bieger Regional, Castro and Jackson 2001, or custom values.
Slope can be changed for the selected plot. Plot choices are saved separately
for each segment in the current session and do not replace network scores.
Alternative or custom width/depth omits maximum bankfull depth; GIFT then uses
`(bankfull width / mean bankfull depth) / 100` for its shape factor.
The Bieger Regional division is configured by `BIEGER_REGION` in settings.py
(Intermontane Plateau for this network). Castro and Jackson uses the Western
Cordillera drainage-area relationships verified against USGS StreamStats,
converting feet and mi² to SI.
The equations are shown with the plot controls, and selected-segment downloads
record the active width/depth sources, geometry, and slope.
Selecting a segment runs the original Python GIFT model for that segment and
caches its hydraulic solution. The map overview uses the bundled monthly
hydraulics where the source inputs still match. Mean depth,
velocity, and wetted width are interpolated to each exact monthly flow before
GIFT evaluates its 121-bin distributions and nearest-coordinate suitability lookup.
Substrate suitability uses the class containing predicted D84, with inclusive lower
and exclusive upper bounds. D84 represents one grain size, not a full distribution.

**HSI and WUA.** HSI is the product of depth, velocity, and substrate suitability.
WUA is HSI × wetted width, expressed in m² per meter of reach. Period summaries
take the median of separately calculated monthly HSI and WUA. They do not evaluate
habitat at median discharge or multiply separately aggregated suitability scores.
Raw values in the inspector always refer to its single selected month.

**Flows and availability.** EROM values are gage-adjusted 1971–2000 monthly climatology,
not current observations. Represented alterations and gage corrections are included;
diversions are incompletely accounted for. The default requires every selected month.
Turning this off permits available-month medians, with coverage retained in the export.
Unsupported positive flows are never extrapolated or replaced by zero. A modeled
zero-flow month has zero HSI and WUA; depth/velocity suitability is undefined.

**Comparison scores.** The configured temperature score is displayed unchanged.
For the supplied `currTempScoreKSee` field, higher values indicate better juvenile-salmon temperature suitability
from [See et al. (2021)](https://doi.org/10.1002/ecs2.3404). Its score transformation
was not independently reconstructed, and it is not a spawning temperature model.
Priority is also displayed unchanged. Neither score is a GIFT component.

**Display and source.** Display geometry uses the configured simplification; hydraulic calculations
use the original reach attributes. The Python source and original GIFT model are
included in the project under GPL-3.0. Custom uploads are held in the user's session;
derived computations use a bounded server cache. Full app reruns check the source
files, field mappings, units, curves, and calculation code before using prepared data.
Changed inputs refresh the stream attributes. Segments needing new hydraulics
are evaluated when selected, and their results are added to the map and export.
Startup does not rebuild hydraulic curves for the network.
""")
        curve = st.session_state.get("current_curve")
        if curve:
            a,b,c = st.columns(3)
            for col,kind in ((a,"depth"),(b,"velocity"),(c,"substrate")):
                with col:
                    st.markdown(f"**{kind.capitalize()} curve**")
                    if kind == "substrate":
                        st.dataframe(pd.DataFrame(curve[kind], columns=["Lower (mm)","Upper (mm)","Suitability"]), hide_index=True, height=220)
                    else:
                        values = np.asarray(curve[kind])
                        fig = go.Figure(go.Scatter(x=values[:,0],y=values[:,1],mode="lines+markers",line=dict(color="#186354")))
                        fig.update_layout(height=220,template="plotly_white",margin=dict(l=10,r=10,t=10,b=10),xaxis_title="m" if kind == "depth" else "m/s",yaxis_range=[0,1])
                        st.plotly_chart(fig,width="stretch",key=f"curve-{kind}")
            st.caption("Points are looked up by nearest coordinate. The connecting lines illustrate the supplied curve; they do not change that lookup rule.")


def main():
    st.set_page_config(page_title=APP_TITLE, page_icon="🌊", layout="wide")
    st.markdown("""<style>
    .stApp {background:#f7f8f4;color:#183e36}
    [data-testid="stSidebar"] {background:#edf2e9}
    h1,h2,h3 {color:#183e36;letter-spacing:-.025em}
    .block-container {padding-top:2rem;max-width:1650px}
    [data-testid="stMetricValue"] {font-size:1.65rem;color:#186354}
    .legend {display:flex;align-items:center;gap:12px;font-size:13px;color:#486058;margin-top:8px}
    .legend div {height:9px;flex:1;border-radius:4px;max-width:280px}
    /* Tooltips appear only when a pickable stream or comparison dot is hit.
       Keep the map's normal grab cursor and the graph's pan cursor elsewhere. */
    [data-testid="stDeckGlJsonChart"]:has(.deck-tooltip[style*="display: block"]) canvas,
    [data-testid="stDeckGlJsonChart"]:has(.deck-tooltip[style*="display: block"])
    [style*="cursor: grab;"] {
        cursor:pointer !important;
    }
    [class*="st-key-selection-"][class*="-comparison-"]
    [data-testid="stPlotlyChart"]:has(.hoverlayer .hovertext) .nsewdrag {
        cursor:pointer !important;
    }
    </style>""", unsafe_allow_html=True)
    st.title(APP_TITLE)
    st.caption("Explore hydraulic habitat, temperature suitability, and restoration priority across one stream network.")
    if st.sidebar.button("Reload input data", help="Reread settings.py and check for changes to source files and field mappings."):
        st.rerun()
    try:
        with st.spinner("Loading stream network…"):
            signature = data_signature()
            network, curves = cached_data(signature)
    except (OSError, ValueError, sqlite3.Error, KeyError) as exc:
        st.error(f"Input data could not be loaded: {exc}")
        st.info("Check the paths, layers, fields, and units in settings.py, then reload the app.")
        st.stop()
    st.session_state.setdefault("view_revision", 0)
    st.session_state.setdefault("selection_revision", 0)
    curve, months, require_all, cfs = sidebar(curves)
    st.session_state.current_curve = curve
    with st.spinner("Evaluating monthly habitat with GIFT…"):
        monthly = cached_monthly(json.dumps(curve, sort_keys=True), signature)
        summary = aggregate_period(monthly, months, require_all)
    workspace(network, curve, monthly, summary, months, cfs, signature)
    methods(network)


if __name__ == "__main__":
    main()
