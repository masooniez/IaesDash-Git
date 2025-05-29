# layouts.py

from dash import dcc, html
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from datetime import datetime, timedelta
import logging
from colorlog import ColoredFormatter

# ——— Logging setup ———
formatter = ColoredFormatter(
    "%(log_color)s%(levelname)s:%(name)s:%(message)s",
    datefmt=None,
    reset=True,
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'blue',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    }
)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.basicConfig(level=logging.INFO, handlers=[handler])
logger = logging.getLogger(__name__)

# Define tab styles
tab_style = {
    'padding': '10px',
    'color': '#e6edf3',
    'backgroundColor': '#161b22',
    'border': 'none',
    'borderRadius': '5px',
    'marginRight': '2px'
}

tab_selected_style = {
    'padding': '10px',
    'color': '#ffffff',
    'backgroundColor': '#ff5757',
    'border': 'none',
    'borderRadius': '5px',
    'marginRight': '2px'
}

# Create reusable tab groups
def create_tab_group(prefix):
    return dbc.Tabs([
        dbc.Tab(label="KPIs", tab_id=f"{prefix}-kpi-tab", 
                tab_style=tab_style, active_tab_style=tab_selected_style),
        dbc.Tab(label="Traffic Flow", tab_id=f"{prefix}-traffic-tab",
                tab_style=tab_style, active_tab_style=tab_selected_style),
        dbc.Tab(label="Anomalies", tab_id=f"{prefix}-anomalies-tab",
                tab_style=tab_style, active_tab_style=tab_selected_style)
    ], id=f"{prefix}-tabs", active_tab=f"{prefix}-kpi-tab")

# Create reusable KPI cards instead of graphs
def create_kpi_cards(prefix):
    return html.Div([
        dbc.Row([
            dbc.Col(dcc.Graph(id=f"{prefix}-indicator-packets", className='card'), width=4),
            dbc.Col(dcc.Graph(id=f"{prefix}-indicator-data-points", className='card'), width=4),
            dbc.Col(dcc.Graph(id=f"{prefix}-indicator-cyber-reports", className='card'), width=4),
        ], className='mb-4')
    ])

# Create reusable traffic flow graphs
def create_traffic_graphs(prefix):
    return html.Div([
        html.Div([
            dcc.Graph(id=f"{prefix}-treemap", className='card'),
            dcc.Graph(id=f"{prefix}-pie-chart", className='card'),
            dcc.Graph(id=f"{prefix}-hourly-heatmap", className='card'),
            dcc.Graph(id=f"{prefix}-sankey-diagram", className='card'),
            dcc.Graph(id=f"{prefix}-stacked-area", className='card'),
            dcc.Graph(id=f"{prefix}-anomalies-scatter", className='card'),
            dcc.Graph(id=f"{prefix}-daily-heatmap", className='card'),
            dcc.Graph(id=f"{prefix}-sankey-heatmap-diagram", className='card'),
            dcc.Graph(id=f"{prefix}-line-chart", className='card'),
            dcc.Graph(id=f"{prefix}-bar-chart", className='card'),
        ], className='dashboard-grid', role="main")
    ])

# Create reusable anomaly graphs
def create_anomaly_graphs(prefix):
    return html.Div([
        html.Div([
            html.Div([
                dcc.Loading(
                    dcc.Graph(
                        id=f"{prefix}-anomalies-scatter",
                        figure=go.Figure(layout=dict(
                            margin=dict(l=50, r=50, t=50, b=50),
                            autosize=True,
                            height=400,
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='white')
                        )),
                        config={'displayModeBar': False, 'responsive': False}
                    ),
                    type="circle",
                    parent_className="loading-container"
                )
            ], className="card"),
            html.Div([
                dcc.Loading(
                    dcc.Graph(
                        id=f"{prefix}-stacked-area",
                        figure=go.Figure(layout=dict(
                            margin=dict(l=50, r=50, t=50, b=50),
                            autosize=True,
                            height=400,
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='white')
                        )),
                        config={'displayModeBar': False, 'responsive': False}
                    ),
                    type="circle",
                    parent_className="loading-container"
                )
            ], className="card")
        ], className="dashboard-grid", role="main")
    ])

# Add site selector component
site_selector = html.Div([
    html.H6("Facility Selection", className="text-white mb-3"),
    dcc.Dropdown(
        id='site-selector',
        options=[
            {'label': '(FM1) (Active)', 'value': 'FM1'},
            {'label': '(FM2) TBA', 'value': 'FM2', 'disabled': True},
            {'label': '(FM3) TBA', 'value': 'FM3', 'disabled': True}
        ],
        value='FM1',
        clearable=False,
        className='site-selector-dropdown mb-4'
    )
], className='site-selector-container')

# ---- OVERVIEW (7 DAYS) LAYOUT ----
overview_layout = html.Div([
    # interval + store for overview
    dcc.Interval(id='overview-interval', interval=600*1000, n_intervals=0),
    dcc.Store(id='overview-figs-store', data={}),
    
    html.H1("Overview (Last 7 Days)", style={"color": "white", "margin": "16px 0"}),

    # Indicator row
    dbc.Row([
        dbc.Col(dcc.Graph(id='overview-indicator-packets', className='card'), width=4),
        dbc.Col(dcc.Graph(id='overview-indicator-data-points', className='card'), width=4),
        dbc.Col(dcc.Graph(id='overview-indicator-cyber-reports', className='card'), width=4),
    ], className='mb-4'),

    # Main graphs grid
    html.Div([
        dcc.Graph(id='overview-treemap', className='card'),
        dcc.Graph(id='overview-pie-chart', className='card'),
        dcc.Graph(id='overview-hourly-heatmap', className='card'),
        dcc.Graph(id='overview-sankey-diagram', className='card'),
        dcc.Graph(id='overview-stacked-area', className='card'),
        dcc.Graph(id='overview-anomalies-scatter', className='card'),
        dcc.Graph(id='overview-daily-heatmap', className='card'),
        dcc.Graph(id='overview-sankey-heatmap-diagram', className='card'),
        dcc.Graph(id='overview-line-chart', className='card'),
        dcc.Graph(id='overview-bar-chart', className='card'),
    ], className='dashboard-grid')
])

# ---- 1-HOUR LAYOUT ----
one_hour_layout = html.Div([
    # interval + store for 1 hour data
    dcc.Interval(id='1h-interval', interval=600*1000, n_intervals=0),
    dcc.Store(id='1h-figs-store', data={}),
    
    html.H1("Last Hour", style={"color": "white", "margin": "16px 0"}),

    # Indicator row
    dbc.Row([
        dbc.Col(dcc.Graph(id='1h-indicator-packets', className='card'), width=4),
        dbc.Col(dcc.Graph(id='1h-indicator-data-points', className='card'), width=4),
        dbc.Col(dcc.Graph(id='1h-indicator-cyber-reports', className='card'), width=4),
    ], className='mb-4'),

    # Main graphs grid
    html.Div([
        dcc.Graph(id='1h-treemap', className='card'),
        dcc.Graph(id='1h-pie-chart', className='card'),
        dcc.Graph(id='1h-hourly-heatmap', className='card'),
        dcc.Graph(id='1h-sankey-diagram', className='card'),
        dcc.Graph(id='1h-stacked-area', className='card'),
        dcc.Graph(id='1h-anomalies-scatter', className='card'),
        dcc.Graph(id='1h-daily-heatmap', className='card'),
        dcc.Graph(id='1h-sankey-heatmap-diagram', className='card'),
        dcc.Graph(id='1h-line-chart', className='card'),
        dcc.Graph(id='1h-bar-chart', className='card'),
    ], className='dashboard-grid')
])

# ---- 24-HOURS LAYOUT ----
twenty_four_hour_layout = html.Div([
    # interval + store for 24 hours data
    dcc.Interval(id='24h-interval', interval=600*1000, n_intervals=0),
    dcc.Store(id='24h-figs-store', data={}),
    
    html.H1("Last 24 Hours", style={"color": "white", "margin": "16px 0"}),

    # Indicator row
    dbc.Row([
        dbc.Col(dcc.Graph(id='24h-indicator-packets', className='card'), width=4),
        dbc.Col(dcc.Graph(id='24h-indicator-data-points', className='card'), width=4),
        dbc.Col(dcc.Graph(id='24h-indicator-cyber-reports', className='card'), width=4),
    ], className='mb-4'),

    # Main graphs grid
    html.Div([
        dcc.Graph(id='24h-treemap', className='card'),
        dcc.Graph(id='24h-pie-chart', className='card'),
        dcc.Graph(id='24h-hourly-heatmap', className='card'),
        dcc.Graph(id='24h-sankey-diagram', className='card'),
        dcc.Graph(id='24h-stacked-area', className='card'),
        dcc.Graph(id='24h-anomalies-scatter', className='card'),
        dcc.Graph(id='24h-daily-heatmap', className='card'),
        dcc.Graph(id='24h-sankey-heatmap-diagram', className='card'),
        dcc.Graph(id='24h-line-chart', className='card'),
        dcc.Graph(id='24h-bar-chart', className='card'),
    ], className='dashboard-grid')
])

# ---- CUSTOM LAYOUT ----
custom_layout = html.Div([
    dcc.Interval(id='custom-interval', interval=600*1000, n_intervals=0),
    dcc.Store(id='custom-figs-store', data={}),
    
    html.H1("Custom Search", style={"color": "white", "margin": "16px 0"}),
    
    # Custom date range selector
    html.Div([
        dcc.DatePickerRange(
            id='custom-date-picker',
            className='date-picker'
        ),
    ], className='mb-4'),
    
    # Indicator row
    dbc.Row([
        dbc.Col(dcc.Graph(id='custom-indicator-packets', className='card'), width=4),
        dbc.Col(dcc.Graph(id='custom-indicator-data-points', className='card'), width=4),
        dbc.Col(dcc.Graph(id='custom-indicator-cyber-reports', className='card'), width=4),
    ], className='mb-4'),

    # Main graphs grid
    html.Div([
        dcc.Graph(id='custom-treemap', className='card'),
        dcc.Graph(id='custom-pie-chart', className='card'),
        dcc.Graph(id='custom-hourly-heatmap', className='card'),
        dcc.Graph(id='custom-sankey-diagram', className='card'),
        dcc.Graph(id='custom-stacked-area', className='card'),
        dcc.Graph(id='custom-anomalies-scatter', className='card'),
        dcc.Graph(id='custom-daily-heatmap', className='card'),
        dcc.Graph(id='custom-sankey-heatmap-diagram', className='card'),
        dcc.Graph(id='custom-line-chart', className='card'),
        dcc.Graph(id='custom-bar-chart', className='card'),
    ], className='dashboard-grid')
])

# Side navigation
sidebar = dbc.Nav(
    [
        site_selector,  # Add the site selector at the top
        dbc.NavLink(
            [html.I(className="fas fa-chart-line me-2"), "Overview"],
            href="/",
            active="exact",
            className="nav-link"
        ),
        dbc.NavLink(
            [html.I(className="fas fa-clock me-2"), "Last Hour"],
            href="/1_hour_data",
            active="exact",
            className="nav-link"
        ),
        dbc.NavLink(
            [html.I(className="fas fa-calendar-day me-2"), "Last 24 Hours"],
            href="/24_hours_data",
            active="exact",
            className="nav-link"
        ),
        dbc.NavLink(
            [html.I(className="fas fa-search me-2"), "Custom Search"],
            href="/custom_data",
            active="exact",
            className="nav-link"
        ),
    ],
    vertical=True,
    pills=True,
    className="sidebar-nav"
)
