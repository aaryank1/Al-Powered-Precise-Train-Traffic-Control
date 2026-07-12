from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from scenarios.scenario_1 import build_trains
from src.planning.actions import Action, ActionType
from src.planning.scheduler import Scheduler
from src.railway.network import Network, default_network
from src.railway.occupancy import LOOP, MAIN
from src.simulation.simulator import Simulator


TRAIN_COLORS = [
    "#2563eb",
    "#dc2626",
    "#059669",
    "#9333ea",
    "#d97706",
    "#0891b2",
]


def build_frames(max_ticks: int) -> tuple[list[dict[str, Any]], str | None]:
    """Run the default scenario and return replayable visualization frames."""

    sim = Simulator(
        build_trains(),
        Scheduler(),
        network=default_network,
        verbose=False,
    )
    frames: list[dict[str, Any]] = [
        {
            "label": "Initial",
            "time": None,
            "actions": [],
            "occupancy": sim.occupancy_state.snapshot(),
            "metrics": sim.get_metrics(),
        }
    ]
    warning = None

    while sim.active_trains():
        if sim.time >= max_ticks:
            warning = f"Simulation stopped at {max_ticks} ticks with active trains remaining."
            break
        sim.step()
        latest = sim.history[-1]
        frames.append(
            {
                "label": f"Tick {latest['time']}",
                "time": latest["time"],
                "actions": latest["actions"],
                "occupancy": latest["occupancy"],
                "metrics": latest["metrics"],
            }
        )

    return frames, warning


def train_color_map(frames: list[dict[str, Any]]) -> dict[str, str]:
    """Assign stable colors to trains seen in the simulation metrics."""

    train_names = sorted(frames[0]["metrics"]["trains"])
    return {
        train_name: TRAIN_COLORS[index % len(TRAIN_COLORS)]
        for index, train_name in enumerate(train_names)
    }


def format_station(network: Network, station_index: int | None) -> str:
    """Return a station name or a placeholder for display."""

    if station_index is None:
        return "-"
    return network.station_name(station_index)


def format_action(action: Action, network: Network) -> str:
    """Return one compact action sentence for tables and captions."""

    source = format_station(network, action.source_station)
    target = format_station(network, action.target_station)

    if action.action_type in {ActionType.MOVE, ActionType.ARRIVE}:
        verb = "arrives" if action.action_type == ActionType.ARRIVE else "moves"
        return f"{action.train_name} {verb}: {source} -> {target}"
    if action.action_type == ActionType.ENTER_LOOP:
        return f"{action.train_name} enters loop at {source}"
    if action.action_type == ActionType.EXIT_LOOP:
        return f"{action.train_name} exits loop at {source}"
    return f"{action.train_name} waits at {source}"


def action_rows(actions: list[Action], network: Network) -> list[dict[str, str]]:
    """Convert actions to table rows."""

    rows = []
    for action in actions:
        rows.append(
            {
                "Train": action.train_name,
                "Action": action.action_type.value,
                "Flow": format_action(action, network),
                "Resources": ", ".join(action.reservations) or "-",
                "Conflict": "yes" if action.conflict else "no",
                "Reason": action.reason,
            }
        )
    return rows


def train_rows(frame: dict[str, Any]) -> list[dict[str, str | int]]:
    """Convert current train metrics to table rows."""

    rows = []
    for train_name, metrics in frame["metrics"]["trains"].items():
        status = "arrived" if metrics["finished"] else "active"
        rows.append(
            {
                "Train": train_name,
                "Status": status,
                "Station": metrics["current_station"],
                "Line": metrics["line"],
                "Waiting": metrics["waiting_time"],
                "Loop entries": metrics["loop_entries"],
                "Completion": metrics["completion_time"] or "-",
            }
        )
    return rows


def occupancy_rows(frame: dict[str, Any]) -> list[dict[str, str]]:
    """Convert station occupancy snapshot to table rows."""

    rows = []
    for station in frame["occupancy"]["stations"]:
        rows.append(
            {
                "Station": station["station"],
                "Main": station.get(MAIN) or "-",
                "Loop": station.get(LOOP) or "-",
            }
        )
    return rows


def block_rows(frame: dict[str, Any], network: Network) -> list[dict[str, str]]:
    """Convert block reservations to table rows."""

    rows = []
    for block, train_name in sorted(frame["occupancy"]["blocks"].items()):
        rows.append(
            {
                "Block": network.describe_block(block),
                "Reserved by": train_name,
            }
        )
    return rows


def render_network_svg(
    network: Network,
    frame: dict[str, Any],
    train_colors: dict[str, str],
) -> str:
    """Render a control-panel style network snapshot as responsive SVG."""

    stations = frame["occupancy"]["stations"]
    actions: list[Action] = frame["actions"]
    blocks = frame["occupancy"]["blocks"]
    movement_by_block = {
        action.block: action
        for action in actions
        if action.action_type in {ActionType.MOVE, ActionType.ARRIVE}
    }
    wait_by_train = {
        action.train_name: action
        for action in actions
        if action.action_type == ActionType.WAIT
    }
    loop_by_train = {
        action.train_name: action
        for action in actions
        if action.action_type in {ActionType.ENTER_LOOP, ActionType.EXIT_LOOP}
    }

    width = 1120
    height = 460
    left = 90
    right = width - 90
    main_y = 220
    loop_y = 316
    spacing = (right - left) / (len(stations) - 1)
    xs = [left + index * spacing for index in range(len(stations))]

    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" xmlns="http://www.w3.org/2000/svg">',
        """
        <defs>
          <marker id="arrow" markerWidth="12" markerHeight="12" refX="9" refY="3"
            orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L0,6 L9,3 z" fill="currentColor" />
          </marker>
          <filter id="softShadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="8" stdDeviation="8" flood-color="#0f172a" flood-opacity="0.18"/>
          </filter>
        </defs>
        <style>
          .panel { fill: #f8fafc; }
          .track { stroke: #334155; stroke-width: 5; stroke-linecap: round; }
          .track-idle { stroke: #94a3b8; stroke-width: 5; stroke-linecap: round; }
          .block-label { fill: #475569; font: 12px system-ui, sans-serif; }
          .station { fill: #ffffff; stroke: #0f172a; stroke-width: 3; filter: url(#softShadow); }
          .station-loop { fill: #ecfeff; stroke: #0891b2; stroke-width: 3; }
          .station-name { fill: #0f172a; font: 700 15px system-ui, sans-serif; text-anchor: middle; }
          .station-sub { fill: #64748b; font: 12px system-ui, sans-serif; text-anchor: middle; }
          .train { fill: #ffffff; stroke: #0f172a; stroke-width: 2; }
          .train-label { fill: #ffffff; font: 700 13px system-ui, sans-serif; text-anchor: middle; dominant-baseline: central; }
          .legend { fill: #334155; font: 13px system-ui, sans-serif; }
          .tick-title { fill: #0f172a; font: 700 18px system-ui, sans-serif; }
        </style>
        """,
        '<rect class="panel" x="16" y="16" width="1088" height="428" rx="8"/>',
        f'<text class="tick-title" x="42" y="56">{escape(frame["label"])}</text>',
    ]

    for index in range(len(stations) - 1):
        x1 = xs[index]
        x2 = xs[index + 1]
        block = (index, index + 1)
        train_name = blocks.get(block)
        action = movement_by_block.get(block)
        color = train_colors.get(train_name, "#334155")
        edge_class = "track" if train_name else "track-idle"
        stroke = color if train_name else "#94a3b8"
        stroke_width = 11 if train_name else 5
        parts.append(
            f'<line class="{edge_class}" x1="{x1 + 28:.1f}" y1="{main_y}" '
            f'x2="{x2 - 28:.1f}" y2="{main_y}" '
            f'style="stroke:{stroke}; stroke-width:{stroke_width}"/>'
        )
        if action:
            arrow_start = x1 + 52 if action.source_station == index else x2 - 52
            arrow_end = x2 - 52 if action.source_station == index else x1 + 52
            marker_color = train_colors.get(action.train_name, "#0f172a")
            parts.append(
                f'<line x1="{arrow_start:.1f}" y1="{main_y - 16}" '
                f'x2="{arrow_end:.1f}" y2="{main_y - 16}" stroke="{marker_color}" '
                f'stroke-width="4" marker-end="url(#arrow)" style="color:{marker_color}"/>'
            )
            parts.append(
                f'<text class="block-label" x="{(x1 + x2) / 2:.1f}" y="{main_y - 32}" '
                f'text-anchor="middle">{escape(action.train_name)}</text>'
            )

    for index, station in enumerate(stations):
        x = xs[index]
        has_loop = LOOP in station
        if has_loop:
            parts.append(
                f'<path d="M{x - 40:.1f},{main_y + 24} C{x - 74:.1f},{loop_y - 20} '
                f'{x - 68:.1f},{loop_y + 22} {x:.1f},{loop_y + 22} '
                f'C{x + 68:.1f},{loop_y + 22} {x + 74:.1f},{loop_y - 20} '
                f'{x + 40:.1f},{main_y + 24}" fill="none" stroke="#0891b2" '
                'stroke-width="5" stroke-linecap="round"/>'
            )
            parts.append(
                f'<rect class="station-loop" x="{x - 42:.1f}" y="{loop_y - 12}" '
                'width="84" height="34" rx="8"/>'
            )
            parts.append(
                f'<text class="station-sub" x="{x:.1f}" y="{loop_y + 10}">loop</text>'
            )

        parts.append(
            f'<circle class="station" cx="{x:.1f}" cy="{main_y}" r="32"/>'
        )
        parts.append(
            f'<text class="station-name" x="{x:.1f}" y="{main_y + 58}">'
            f'{escape(station["station"])}</text>'
        )
        parts.append(
            f'<text class="station-sub" x="{x:.1f}" y="{main_y + 77}">'
            f'S{index}</text>'
        )

        main_train = station.get(MAIN)
        if main_train:
            parts.append(
                train_badge(
                    x,
                    main_y - 58,
                    main_train,
                    train_colors,
                    wait_by_train,
                    loop_by_train,
                )
            )
        loop_train = station.get(LOOP)
        if loop_train:
            parts.append(
                train_badge(
                    x,
                    loop_y + 54,
                    loop_train,
                    train_colors,
                    wait_by_train,
                    loop_by_train,
                )
            )

    legend_x = 42
    legend_y = 400
    for index, (train_name, color) in enumerate(train_colors.items()):
        x = legend_x + index * 150
        parts.append(f'<rect x="{x}" y="{legend_y}" width="16" height="16" rx="4" fill="{color}"/>')
        parts.append(f'<text class="legend" x="{x + 24}" y="{legend_y + 13}">{escape(train_name)}</text>')

    parts.append("</svg>")
    return "".join(parts)


def train_badge(
    x: float,
    y: float,
    train_name: str,
    train_colors: dict[str, str],
    waits: dict[str, Action],
    loops: dict[str, Action],
) -> str:
    """Render one train badge with action-aware styling."""

    color = train_colors.get(train_name, "#334155")
    stroke = "#991b1b" if train_name in waits and waits[train_name].conflict else "#0f172a"
    width = 82
    note = ""
    if train_name in waits:
        note = "WAIT"
    elif train_name in loops:
        note = "LOOP"

    parts = [
        f'<rect x="{x - width / 2:.1f}" y="{y - 18:.1f}" width="{width}" height="36" '
        f'rx="8" fill="{color}" stroke="{stroke}" stroke-width="3"/>',
        f'<text class="train-label" x="{x:.1f}" y="{y:.1f}">{escape(train_name)}</text>',
    ]
    if note:
        parts.append(
            f'<text class="station-sub" x="{x:.1f}" y="{y + 34:.1f}">{note}</text>'
        )
    return "".join(parts)


def main() -> None:
    """Launch the Streamlit train simulation visualizer."""

    st.set_page_config(page_title="Train Traffic Control", layout="wide")
    st.title("Train Traffic Control Simulation")

    with st.sidebar:
        st.header("Scenario")
        max_ticks = st.slider("Max ticks", min_value=5, max_value=100, value=30)

    frames, warning = build_frames(max_ticks)
    colors = train_color_map(frames)
    last_index = len(frames) - 1

    if "selected_frame" not in st.session_state:
        st.session_state.selected_frame = 0
    st.session_state.selected_frame = min(st.session_state.selected_frame, last_index)

    col_prev, col_next, col_initial, col_latest = st.columns([1, 1, 1, 1])
    if col_prev.button("Previous", use_container_width=True):
        st.session_state.selected_frame = max(0, st.session_state.selected_frame - 1)
    if col_next.button("Next", use_container_width=True):
        st.session_state.selected_frame = min(last_index, st.session_state.selected_frame + 1)
    if col_initial.button("Initial", use_container_width=True):
        st.session_state.selected_frame = 0
    if col_latest.button("Latest", use_container_width=True):
        st.session_state.selected_frame = last_index

    selected = st.select_slider(
        "Replay tick",
        options=list(range(last_index + 1)),
        value=st.session_state.selected_frame,
        format_func=lambda index: frames[index]["label"],
    )
    st.session_state.selected_frame = selected
    frame = frames[selected]

    if warning:
        st.warning(warning)

    metrics = frame["metrics"]
    metric_cols = st.columns(5)
    metric_cols[0].metric("Ticks", metrics["total_ticks"])
    metric_cols[1].metric("Arrived", metrics["arrived_trains"])
    metric_cols[2].metric("Active", metrics["active_trains"])
    metric_cols[3].metric("Conflicts", metrics["conflict_count"])
    metric_cols[4].metric("Loop usage", metrics["loop_usage"])

    svg = render_network_svg(default_network, frame, colors)
    components.html(
        f'<div style="width:100%; overflow-x:auto;">{svg}</div>',
        height=500,
        scrolling=False,
    )

    actions = frame["actions"]
    if actions:
        st.subheader("Tick actions")
        for action in actions:
            st.write(f"**{format_action(action, default_network)}** - {action.reason}")
    else:
        st.info("Initial station occupancy before any scheduler decision.")

    tab_actions, tab_trains, tab_occupancy, tab_blocks = st.tabs(
        ["Actions", "Trains", "Stations", "Blocks"]
    )
    with tab_actions:
        st.dataframe(action_rows(actions, default_network), use_container_width=True, hide_index=True)
    with tab_trains:
        st.dataframe(train_rows(frame), use_container_width=True, hide_index=True)
    with tab_occupancy:
        st.dataframe(occupancy_rows(frame), use_container_width=True, hide_index=True)
    with tab_blocks:
        rows = block_rows(frame, default_network)
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("No block reservations in this frame.")


if __name__ == "__main__":
    main()
