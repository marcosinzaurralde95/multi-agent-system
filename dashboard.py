"""
MAMS - Matrix Agentic Money System
Dashboard (real data from shared memory / SQLite)
"""

from datetime import datetime
from typing import Any, Dict, List

import dash
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, dcc, html

from memory import get_memory

app = dash.Dash(
    __name__,
    title="MAMS Dashboard",
    suppress_callback_exceptions=True,
)


def _load_dashboard_state() -> Dict[str, Any]:
    memory = get_memory()
    revenue = memory.retrieve("revenue_goals", {}) or {}
    health = memory.retrieve("system_health", {}) or {}
    agent_status = memory.retrieve("agent_status", {}) or {}
    alerts = memory.retrieve("alerts", []) or []

    history = memory.query(search_key="system_health:", limit=120)
    points: List[Dict[str, Any]] = []
    for item in history:
        if isinstance(item.value, dict):
            points.append(item.value)
    points.sort(key=lambda row: row.get("timestamp", ""))

    return {
        "revenue": revenue,
        "health": health,
        "agent_status": agent_status,
        "alerts": alerts[-10:],
        "history": points,
    }


def _currency(value: Any) -> str:
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return "$0.00"


app.layout = html.Div(
    [
        html.H1("MAMS Dashboard"),
        html.Div(id="header-metrics", style={"display": "grid", "gridTemplateColumns": "repeat(4, 1fr)", "gap": "12px"}),
        dcc.Graph(id="revenue-chart"),
        dcc.Graph(id="health-chart"),
        html.H3("Agent Status"),
        html.Div(id="agent-table"),
        html.H3("Recent Alerts"),
        html.Div(id="alerts-feed"),
        dcc.Interval(id="update-interval", interval=5000, n_intervals=0),
    ],
    style={"maxWidth": "1200px", "margin": "0 auto", "padding": "20px"},
)


@app.callback(
    [
        Output("header-metrics", "children"),
        Output("revenue-chart", "figure"),
        Output("health-chart", "figure"),
        Output("agent-table", "children"),
        Output("alerts-feed", "children"),
    ],
    Input("update-interval", "n_intervals"),
)
def update_dashboard(_n):
    state = _load_dashboard_state()
    revenue = state["revenue"]
    health = state["health"]
    agent_status = state["agent_status"]
    alerts = state["alerts"]
    history = state["history"]

    daily_current = revenue.get("daily", 0) if isinstance(revenue.get("daily"), (int, float)) else revenue.get("daily", revenue.get("daily_current", 0))
    weekly_current = revenue.get("weekly", 0)
    monthly_current = revenue.get("monthly", 0)
    tasks_completed = 0
    agents_data = health.get("agents", {})
    if isinstance(agents_data, dict):
        for agent in agents_data.values():
            metrics = agent.get("metrics", {})
            tasks_completed += int(metrics.get("tasks_completed", 0))

    metrics_cards = [
        html.Div([html.H4("Revenue Today"), html.P(_currency(daily_current))], style={"border": "1px solid #ddd", "padding": "10px", "borderRadius": "8px"}),
        html.Div([html.H4("Revenue Weekly"), html.P(_currency(weekly_current))], style={"border": "1px solid #ddd", "padding": "10px", "borderRadius": "8px"}),
        html.Div([html.H4("Revenue Monthly"), html.P(_currency(monthly_current))], style={"border": "1px solid #ddd", "padding": "10px", "borderRadius": "8px"}),
        html.Div([html.H4("Tasks Completed"), html.P(str(tasks_completed))], style={"border": "1px solid #ddd", "padding": "10px", "borderRadius": "8px"}),
    ]

    revenue_fig = go.Figure()
    revenue_fig.add_trace(
        go.Bar(
            x=["daily", "weekly", "monthly"],
            y=[float(daily_current or 0), float(weekly_current or 0), float(monthly_current or 0)],
            name="Current",
        )
    )
    revenue_fig.update_layout(title="Revenue Snapshot", height=320)

    history_rows = []
    for point in history[-30:]:
        timestamp = point.get("timestamp")
        uptime = point.get("uptime_seconds", 0)
        agent_count = len(point.get("agents", {})) if isinstance(point.get("agents"), dict) else 0
        history_rows.append({"timestamp": timestamp, "uptime_seconds": uptime, "agent_count": agent_count})

    if history_rows:
        df = pd.DataFrame(history_rows)
        health_fig = go.Figure()
        health_fig.add_trace(go.Scatter(x=df["timestamp"], y=df["uptime_seconds"], mode="lines+markers", name="Uptime (s)"))
        health_fig.add_trace(go.Scatter(x=df["timestamp"], y=df["agent_count"], mode="lines", name="Agents"))
    else:
        health_fig = go.Figure()
        health_fig.add_annotation(text="No health history yet", x=0.5, y=0.5, showarrow=False)
    health_fig.update_layout(title="System Health", height=320)

    rows = []
    for agent_id, status in (agent_status or {}).items():
        rows.append(
            html.Div(
                [
                    html.Span(agent_id, style={"display": "inline-block", "width": "180px", "fontWeight": "bold"}),
                    html.Span(status.get("status", "unknown"), style={"display": "inline-block", "width": "100px"}),
                    html.Span(str(status.get("current_task", ""))),
                ],
                style={"padding": "6px 0", "borderBottom": "1px solid #eee"},
            )
        )
    if not rows:
        rows = [html.Div("No agent status published yet.")]

    alert_nodes = []
    for alert in alerts:
        alert_nodes.append(
            html.Div(
                f"[{alert.get('severity', 'info')}] {alert.get('message', '')} - {alert.get('timestamp', '')}",
                style={"padding": "6px 0", "borderBottom": "1px solid #eee"},
            )
        )
    if not alert_nodes:
        alert_nodes = [html.Div("No recent alerts.")]

    return metrics_cards, revenue_fig, health_fig, rows, alert_nodes


def run_dashboard(debug: bool = False, port: int = 8050):
    app.run(debug=debug, port=port, host="0.0.0.0")


if __name__ == "__main__":
    run_dashboard(debug=True)
