"""
MAMS - Matrix Agentic Money System
Dashboard Application
"""

import dash
from dash import dcc, html, callback, Output, Input, State
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
import threading
import time
import random
from pathlib import Path
import loguru

logger = loguru.logger

# Dash app setup
app = dash.Dash(
    __name__,
    title="MAMS - Matrix Agentic Money System",
    suppress_callback_exceptions=True,
)

# Sample data generators
def generate_sample_revenue_data(days=30):
    """Generate sample revenue data"""
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    revenue = [random.uniform(200, 800) for _ in range(days)]
    cumulative = pd.Series(revenue).cumsum().tolist()
    targets = [333] * days  # Daily target
    
    df = pd.DataFrame({
        'date': dates,
        'revenue': revenue,
        'target': targets,
        'cumulative': cumulative,
    })
    return df


def generate_agent_performance():
    """Generate agent performance data"""
    agents = ['Director', 'Researcher', 'Creator', 'Marketer', 'Sales', 'Analyst', 'Quality']
    return pd.DataFrame({
        'agent': agents,
        'tasks_completed': [random.randint(50, 200) for _ in agents],
        'tasks_failed': [random.randint(0, 10) for _ in agents],
        'avg_time': [random.uniform(10, 60) for _ in agents],
        'status': [random.choice(['online', 'online', 'online', 'working']) for _ in agents],
    })


def generate_channel_performance():
    """Generate channel performance data"""
    channels = ['Organic Search', 'Paid Ads', 'Social Media', 'Email', 'Direct']
    return pd.DataFrame({
        'channel': channels,
        'visitors': [random.randint(5000, 50000) for _ in channels],
        'conversions': [random.randint(50, 500) for _ in channels],
        'revenue': [random.randint(500, 10000) for _ in channels],
    })


def generate_content_performance():
    """Generate content performance data"""
    content_types = ['Blog Posts', 'Social Posts', 'Emails', 'Landing Pages', 'Ads']
    return pd.DataFrame({
        'type': content_types,
        'created': [random.randint(20, 200) for _ in content_types],
        'published': [random.randint(15, 180) for _ in content_types],
        'avg_engagement': [random.uniform(2, 15) for _ in content_types],
    })


# Layout
app.layout = html.Div([
    # Header
    html.Div([
        html.H1("🚀 MAMS Dashboard", className="header-title"),
        html.Div([
            html.Span("Status: ", className="status-label"),
            html.Span("🟢 ACTIVE", id="system-status", className="status-value"),
        ], className="status-indicator"),
    ], className="header"),
    
    # Main metrics cards
    html.Div([
        # Revenue Card
        html.Div([
            html.Div("💰 Revenue Today", className="metric-label"),
            html.Div("$0.00", id="revenue-today", className="metric-value revenue"),
            html.Div([
                html.Span("Target: ", className="target-label"),
                html.Span("$333", className="target-value"),
            ], className="metric-target"),
        ], className="metric-card"),
        
        # Weekly Revenue
        html.Div([
            html.Div("📊 Weekly Revenue", className="metric-label"),
            html.Div("$0.00", id="revenue-weekly", className="metric-value revenue"),
            html.Div([
                html.Span("Target: ", className="target-label"),
                html.Span("$2,333", className="target-value"),
            ], className="metric-target"),
        ], className="metric-card"),
        
        # Monthly Revenue
        html.Div([
            html.Div("🎯 Monthly Revenue", className="metric-label"),
            html.Div("$0.00", id="revenue-monthly", className="metric-value revenue"),
            html.Div([
                html.Span("Target: ", className="target-label"),
                html.Span("$10,000", className="target-value"),
            ], className="metric-target"),
        ], className="metric-card"),
        
        # Tasks Completed
        html.Div([
            html.Div("✅ Tasks Completed", className="metric-label"),
            html.Div("0", id="tasks-completed", className="metric-value tasks"),
            html.Div([
                html.Span("Active: ", className="target-label"),
                html.Span("0", className="target-value"),
            ], className="metric-target"),
        ], className="metric-card"),
    ], className="metrics-row"),
    
    # Charts Row
    html.Div([
        # Revenue Chart
        html.Div([
            html.H3("📈 Revenue Trend", className="chart-title"),
            dcc.Graph(id="revenue-chart"),
        ], className="chart-container large"),
        
        # Agent Performance
        html.Div([
            html.H3("🤖 Agent Performance", className="chart-title"),
            dcc.Graph(id="agent-chart"),
        ], className="chart-container"),
    ], className="charts-row"),
    
    # Second Charts Row
    html.Div([
        # Channel Performance
        html.Div([
            html.H3("📡 Traffic Channels", className="chart-title"),
            dcc.Graph(id="channel-chart"),
        ], className="chart-container"),
        
        # Content Performance
        html.Div([
            html.H3("✍️ Content Production", className="chart-title"),
            dcc.Graph(id="content-chart"),
        ], className="chart-container"),
    ], className="charts-row"),
    
    # Agent Status Table
    html.Div([
        html.H3("🔧 Agent Status", className="chart-title"),
        html.Table([
            html.Thead([
                html.Tr([
                    html.Th("Agent"),
                    html.Th("Status"),
                    html.Th("Tasks"),
                    html.Th("Success Rate"),
                    html.Th("Avg Time"),
                ])
            ]),
            html.Tbody(id="agent-table"),
        ], className="agent-table"),
    ], className="table-container"),
    
    # Alerts & Activity
    html.Div([
        # Recent Activity
        html.Div([
            html.H3("📋 Recent Activity", className="chart-title"),
            html.Div(id="activity-feed", className="activity-feed"),
        ], className="activity-container"),
        
        # Alerts
        html.Div([
            html.H3("⚠️ Alerts", className="chart-title"),
            html.Div(id="alerts-feed", className="alerts-feed"),
        ], className="alerts-container"),
    ], className="bottom-row"),
    
    # Update interval
    dcc.Interval(
        id='update-interval',
        interval=5000,  # Update every 5 seconds
        n_intervals=0
    ),
], className="dashboard")


# Callbacks
@app.callback(
    [Output("revenue-chart", "figure"),
     Output("agent-chart", "figure"),
     Output("channel-chart", "figure"),
     Output("content-chart", "figure"),
     Output("revenue-today", "children"),
     Output("revenue-weekly", "children"),
     Output("revenue-monthly", "children"),
     Output("tasks-completed", "children"),
     Output("agent-table", "children"),
     Output("activity-feed", "children"),
     Output("alerts-feed", "children")],
    Input("update-interval", "n_intervals")
)
def update_dashboard(n):
    """Update all dashboard components"""
    
    # Generate sample data
    revenue_df = generate_sample_revenue_data()
    agent_df = generate_agent_performance()
    channel_df = generate_channel_performance()
    content_df = generate_content_performance()
    
    # Revenue Chart
    revenue_fig = make_subplots(specs=[[{"secondary_y": True}]])
    revenue_fig.add_trace(
        go.Bar(x=revenue_df['date'], y=revenue_df['revenue'], 
               name="Daily Revenue", marker_color='#4CAF50'),
        secondary_y=False,
    )
    revenue_fig.add_trace(
        go.Scatter(x=revenue_df['date'], y=revenue_df['cumulative'], 
                   name="Cumulative", line=dict(color='#FF9800', width=2)),
        secondary_y=True,
    )
    revenue_fig.add_hline(y=333, line_dash="dash", line_color="red", 
                          annotation_text="Daily Target", secondary_y=False)
    revenue_fig.update_layout(
        showlegend=True,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        height=300,
    )
    revenue_fig.update_yaxes(gridcolor='rgba(255,255,255,0.1)', secondary_y=False)
    revenue_fig.update_yaxes(gridcolor='rgba(255,255,255,0.1)', secondary_y=True)
    
    # Agent Performance Chart
    agent_fig = px.bar(
        agent_df, x='agent', y='tasks_completed', 
        color='status', barmode='group',
        color_discrete_map={'online': '#4CAF50', 'working': '#2196F3', 'idle': '#FFC107'}
    )
    agent_fig.update_layout(
        showlegend=True,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        height=300,
    )
    agent_fig.update_yaxes(gridcolor='rgba(255,255,255,0.1)')
    
    # Channel Performance
    channel_fig = go.Figure(data=[
        go.Bar(name='Visitors', x=channel_df['channel'], y=channel_df['visitors'], marker_color='#2196F3'),
        go.Bar(name='Revenue', x=channel_df['channel'], y=channel_df['revenue'], marker_color='#4CAF50'),
    ])
    channel_fig.update_layout(
        barmode='group',
        showlegend=True,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        height=300,
    )
    channel_fig.update_yaxes(gridcolor='rgba(255,255,255,0.1)')
    
    # Content Performance
    content_fig = px.pie(
        content_df, values='created', names='type',
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set3,
    )
    content_fig.update_layout(
        showlegend=True,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        height=300,
    )
    
    # Revenue values
    revenue_today = f"${random.uniform(250, 450):.2f}"
    revenue_weekly = f"${random.uniform(1500, 2800):.2f}"
    revenue_monthly = f"${random.uniform(5000, 12000):.2f}"
    tasks = random.randint(100, 300)
    
    # Agent table rows
    agent_rows = []
    for _, row in agent_df.iterrows():
        status_color = {'online': '#4CAF50', 'working': '#2196F3', 'idle': '#FFC107'}.get(row['status'], 'gray')
        agent_rows.append(html.Tr([
            html.Td(row['agent']),
            html.Td(html.Span('●', style={'color': status_color}), ),
            html.Td(f"{row['tasks_completed']}"),
            html.Td(f"{(row['tasks_completed']/(row['tasks_completed']+row['tasks_failed'])*100):.0f}%"),
            html.Td(f"{row['avg_time']:.1f}s"),
        ]))
    
    # Activity feed
    activities = [
        ("Researcher", "Completed keyword research", "2m ago"),
        ("Creator", "Published 3 new articles", "5m ago"),
        ("Marketer", "Launched email campaign", "12m ago"),
        ("Sales", "Generated $250 in affiliate revenue", "15m ago"),
        ("Analyst", "Generated weekly report", "30m ago"),
    ]
    activity_items = [
        html.Div([
            html.Span(f"{agent}: ", className="activity-agent"),
            html.Span(desc, className="activity-desc"),
            html.Span(time, className="activity-time"),
        ], className="activity-item")
        for agent, desc, time in activities
    ]
    
    # Alerts
    alerts = [
        ("🔴", "Revenue below target for this hour", "15m ago"),
        ("🟡", "New trending topic detected: AI Tools", "1h ago"),
        ("🟢", "All systems operational", "2h ago"),
    ]
    alert_items = [
        html.Div([
            html.Span(icon, className="alert-icon"),
            html.Div([
                html.Span(msg, className="alert-msg"),
                html.Span(time, className="alert-time"),
            ], className="alert-content"),
        ], className="alert-item")
        for icon, msg, time in alerts
    ]
    
    return (
        revenue_fig, agent_fig, channel_fig, content_fig,
        revenue_today, revenue_weekly, revenue_monthly, tasks,
        agent_rows, activity_items, alert_items,
    )


# CSS styles
app.index_string = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>MAMS - Matrix Agentic Money System</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #0f0f23 0%, #1a1a3e 100%);
            color: #ffffff;
            min-height: 100vh;
            padding: 20px;
        }
        
        .dashboard {
            max-width: 1600px;
            margin: 0 auto;
        }
        
        /* Header */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 30px;
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            margin-bottom: 24px;
            backdrop-filter: blur(10px);
        }
        
        .header-title {
            font-size: 28px;
            font-weight: 700;
            background: linear-gradient(90deg, #00D4FF, #7B2FFF);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .status-indicator {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            background: rgba(76, 175, 80, 0.2);
            border-radius: 20px;
        }
        
        .status-label {
            color: #888;
        }
        
        .status-value {
            color: #4CAF50;
            font-weight: 600;
        }
        
        /* Metrics */
        .metrics-row {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 24px;
        }
        
        .metric-card {
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 24px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
        }
        
        .metric-label {
            font-size: 14px;
            color: #888;
            margin-bottom: 8px;
        }
        
        .metric-value {
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 8px;
        }
        
        .metric-value.revenue {
            color: #4CAF50;
        }
        
        .metric-value.tasks {
            color: #2196F3;
        }
        
        .target-label {
            color: #666;
            font-size: 12px;
        }
        
        .target-value {
            color: #888;
            font-size: 12px;
        }
        
        /* Charts */
        .charts-row {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
            margin-bottom: 24px;
        }
        
        .chart-container {
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
        }
        
        .chart-title {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 16px;
            color: #fff;
        }
        
        /* Table */
        .table-container {
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 24px;
            backdrop-filter: blur(10px);
        }
        
        .agent-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .agent-table th {
            text-align: left;
            padding: 12px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            color: #888;
            font-weight: 500;
        }
        
        .agent-table td {
            padding: 12px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        
        /* Activity & Alerts */
        .bottom-row {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
        }
        
        .activity-container, .alerts-container {
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 20px;
            backdrop-filter: blur(10px);
        }
        
        .activity-feed, .alerts-feed {
            max-height: 300px;
            overflow-y: auto;
        }
        
        .activity-item {
            padding: 12px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        
        .activity-agent {
            font-weight: 600;
            color: #2196F3;
        }
        
        .activity-desc {
            color: #ccc;
            margin-left: 8px;
        }
        
        .activity-time {
            color: #666;
            font-size: 12px;
            float: right;
        }
        
        .alert-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        
        .alert-icon {
            font-size: 20px;
        }
        
        .alert-content {
            flex: 1;
        }
        
        .alert-msg {
            display: block;
            color: #ccc;
        }
        
        .alert-time {
            font-size: 12px;
            color: #666;
        }
        
        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 6px;
        }
        
        ::-webkit-scrollbar-track {
            background: rgba(255,255,255,0.05);
        }
        
        ::-webkit-scrollbar-thumb {
            background: rgba(255,255,255,0.2);
            border-radius: 3px;
        }
        
        /* Responsive */
        @media (max-width: 1200px) {
            .metrics-row {
                grid-template-columns: repeat(2, 1fr);
            }
            .charts-row, .bottom-row {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    {%app_entry%}
    <footer>
        {%config%}
        {%scripts%}
        {%renderer%}
    </footer>
</body>
</html>
'''


def run_dashboard(debug=False, port=None):
    """Run the dashboard server"""
    if port is None:
        import os
        port = int(os.getenv("PORT", 8050))
    app.run(debug=debug, port=port, host='0.0.0.0')


if __name__ == '__main__':
    run_dashboard(debug=True)
