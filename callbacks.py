# callbacks.py
import time
from dash.dependencies import Input, Output, State
from dash import no_update, callback, ctx
from flask_caching import logger
import plotly.graph_objects as go
from cache_config import get_visualizations, update_cache_for_file, cache
from datetime import datetime, timedelta
import os
from data_processing import read_data, create_visualizations, count_files_in_directory
import hashlib
import json
from collector import NetworkDataHandler  
import dash_bootstrap_components as dbc
from dash import dcc, html


def register_callbacks(app, handler):

    def create_empty_figure():
        return go.Figure(layout=dict(
            margin=dict(l=50, r=50, t=50, b=50),
            autosize=True,
            height=400,
            showlegend=True,
            paper_bgcolor='#333333',
            plot_bgcolor='#333333',
            font=dict(color='white', size=12),
            xaxis=dict(
                gridcolor='rgba(255, 255, 255, 0.1)',
                zerolinecolor='rgba(255, 255, 255, 0.2)',
                tickfont=dict(color='white'),
                title_font=dict(color='white')
            ),
            yaxis=dict(
                gridcolor='rgba(255, 255, 255, 0.1)',
                zerolinecolor='rgba(255, 255, 255, 0.2)',
                tickfont=dict(color='white'),
                title_font=dict(color='white')
            )
        ))

    # Overview callbacks
    @app.callback(
        Output('overview-figs-store', 'data'),
        Input('overview-interval', 'n_intervals')
    )
    def update_overview_figs(n):
        figs = get_visualizations('all_data.json') or []
        if len(figs) < 13:
            figs = [create_empty_figure()] * 13
        
        # Update layout for each figure
        for fig in figs:
            fig.update_layout(
                margin=dict(l=50, r=50, t=50, b=50),
                autosize=True,
                height=400,
                showlegend=True,
                paper_bgcolor='#333333',
                plot_bgcolor='#333333',
                font=dict(color='white', size=12),
                xaxis=dict(
                    gridcolor='rgba(255, 255, 255, 0.1)',
                    zerolinecolor='rgba(255, 255, 255, 0.2)',
                    tickfont=dict(color='white'),
                    title_font=dict(color='white')
                ),
                yaxis=dict(
                    gridcolor='rgba(255, 255, 255, 0.1)',
                    zerolinecolor='rgba(255, 255, 255, 0.2)',
                    tickfont=dict(color='white'),
                    title_font=dict(color='white')
                )
            )
            
            # Special handling for Sankey diagram
            if isinstance(fig.data[0], go.Sankey):
                fig.update_layout(
                    height=500,
                    margin=dict(l=100, r=100, t=50, b=50)
                )
            
            # Special handling for Treemap
            elif isinstance(fig.data[0], go.Treemap):
                fig.update_layout(
                    height=450,  # Increased height
                    margin=dict(l=5, r=5, t=30, b=10),  # Adjusted margins
                    uniformtext=dict(minsize=10),
                    title=dict(
                        yref='container',
                        y=0.95  # Adjust title position
                    )
                )
                # Update treemap specific settings
                fig.data[0].update(
                    textposition='middle center',
                    tiling=dict(
                        packing='squarify',  # Use squarify for better box fitting
                        pad=3  # Add some padding between boxes
                    )
                )
        
        return {'figs': [f.to_dict() for f in figs]}

    @app.callback(
        [
            Output('overview-indicator-packets', 'figure'),
            Output('overview-indicator-data-points', 'figure'),
            Output('overview-indicator-cyber-reports', 'figure'),
            Output('overview-treemap', 'figure'),
            Output('overview-pie-chart', 'figure'),
            Output('overview-hourly-heatmap', 'figure'),
            Output('overview-sankey-diagram', 'figure'),
            Output('overview-stacked-area', 'figure'),
            Output('overview-anomalies-scatter', 'figure'),
            Output('overview-daily-heatmap', 'figure'),
            Output('overview-sankey-heatmap-diagram', 'figure'),
            Output('overview-line-chart', 'figure'),
            Output('overview-bar-chart', 'figure'),
        ],
        [Input('overview-interval', 'n_intervals'),
         Input('site-selector', 'value')]
    )
    def update_overview_figs(n_intervals, selected_site):
        # Use callback context to determine which input triggered the callback
        trigger = ctx.triggered_id if ctx.triggered_id else 'overview-interval'
        
        if trigger == 'site-selector':
            # Handle site selection
            data, figs, _ = handler.process_site_data(selected_site)
            if not data or not figs:
                return [create_empty_figure()] * 13
            return [
                figs.get(f'fig{i+1}', create_empty_figure())
                for i in range(13)
            ]
        else:
            # Handle regular interval update
            figs = get_visualizations('all_data.json') or []
            if len(figs) < 13:
                return [create_empty_figure()] * 13
            
            # Update layout for each figure
            for fig in figs:
                fig.update_layout(
                    margin=dict(l=50, r=50, t=50, b=50),
                    autosize=True,
                    height=400,
                    showlegend=True,
                    paper_bgcolor='#333333',
                    plot_bgcolor='#333333',
                    font=dict(color='white', size=12),
                    xaxis=dict(
                        gridcolor='rgba(255, 255, 255, 0.1)',
                        zerolinecolor='rgba(255, 255, 255, 0.2)',
                        tickfont=dict(color='white'),
                        title_font=dict(color='white')
                    ),
                    yaxis=dict(
                        gridcolor='rgba(255, 255, 255, 0.1)',
                        zerolinecolor='rgba(255, 255, 255, 0.2)',
                        tickfont=dict(color='white'),
                        title_font=dict(color='white')
                    )
                )
                
                # Special handling for Sankey diagram
                if isinstance(fig.data[0], go.Sankey):
                    fig.update_layout(
                        height=500,
                        margin=dict(l=100, r=100, t=50, b=50)
                    )
                
                # Special handling for Treemap
                elif isinstance(fig.data[0], go.Treemap):
                    fig.update_layout(
                        height=450,
                        margin=dict(l=5, r=5, t=30, b=10),
                        uniformtext=dict(minsize=10),
                        title=dict(
                            yref='container',
                            y=0.95
                        )
                    )
                    fig.data[0].update(
                        textposition='middle center',
                        tiling=dict(
                            packing='squarify',
                            pad=3
                        )
                    )
            
            return figs[:13]

    # 1-hour callbacks
    @app.callback(
        Output('1h-figs-store', 'data'),
        Input('1h-interval', 'n_intervals')
    )
    def update_1h_figs(n):
        figs = get_visualizations('1_hour_data.json') or []
        if len(figs) < 13:
            figs = [create_empty_figure()] * 13
        return {'figs': [f.to_dict() for f in figs]}

    @app.callback(
        [
            Output('1h-indicator-packets', 'figure'),
            Output('1h-indicator-data-points', 'figure'),
            Output('1h-indicator-cyber-reports', 'figure'),
            Output('1h-treemap', 'figure'),
            Output('1h-pie-chart', 'figure'),
            Output('1h-hourly-heatmap', 'figure'),
            Output('1h-sankey-diagram', 'figure'),
            Output('1h-stacked-area', 'figure'),
            Output('1h-anomalies-scatter', 'figure'),
            Output('1h-daily-heatmap', 'figure'),
            Output('1h-sankey-heatmap-diagram', 'figure'),
            Output('1h-line-chart', 'figure'),
            Output('1h-bar-chart', 'figure'),
        ],
        Input('1h-figs-store', 'data')
    )
    def display_1h_figs(data):
        if not data or 'figs' not in data:
            return [create_empty_figure()] * 13
        figs = data['figs']
        return [go.Figure(f) for f in figs[:13]]

    # 24-hour callbacks
    @app.callback(
        Output('24h-figs-store', 'data'),
        Input('24h-interval', 'n_intervals')
    )
    def update_24h_figs(n):
        figs = get_visualizations('24_hours_data.json') or []
        if len(figs) < 13:
            figs = [create_empty_figure()] * 13
        return {'figs': [f.to_dict() for f in figs]}

    @app.callback(
        [
            Output('24h-indicator-packets', 'figure'),
            Output('24h-indicator-data-points', 'figure'),
            Output('24h-indicator-cyber-reports', 'figure'),
            Output('24h-treemap', 'figure'),
            Output('24h-pie-chart', 'figure'),
            Output('24h-hourly-heatmap', 'figure'),
            Output('24h-sankey-diagram', 'figure'),
            Output('24h-stacked-area', 'figure'),
            Output('24h-anomalies-scatter', 'figure'),
            Output('24h-daily-heatmap', 'figure'),
            Output('24h-sankey-heatmap-diagram', 'figure'),
            Output('24h-line-chart', 'figure'),
            Output('24h-bar-chart', 'figure'),
        ],
        Input('24h-figs-store', 'data')
    )
    def display_24h_figs(data):
        if not data or 'figs' not in data:
            return [create_empty_figure()] * 13
        figs = data['figs']
        return [go.Figure(f) for f in figs[:13]]

    # Custom timeframe callbacks
    @app.callback(
        Output('custom-figs-store', 'data'),
        Input('custom-interval', 'n_intervals')
    )
    def update_custom_figs(n):
        figs = get_visualizations('custom_data.json') or []
        if len(figs) < 13:
            figs = [create_empty_figure()] * 13
        return {'figs': [f.to_dict() for f in figs]}

    @app.callback(
    [
            Output('custom-indicator-packets', 'figure'),
            Output('custom-indicator-data-points', 'figure'),
            Output('custom-indicator-cyber-reports', 'figure'),
            Output('custom-treemap', 'figure'),
            Output('custom-pie-chart', 'figure'),
            Output('custom-hourly-heatmap', 'figure'),
            Output('custom-sankey-diagram', 'figure'),
            Output('custom-stacked-area', 'figure'),
            Output('custom-anomalies-scatter', 'figure'),
            Output('custom-daily-heatmap', 'figure'),
            Output('custom-sankey-heatmap-diagram', 'figure'),
            Output('custom-line-chart', 'figure'),
            Output('custom-bar-chart', 'figure'),
    ],
        Input('custom-figs-store', 'data')
)
    def display_custom_figs(data):
        if not data or 'figs' not in data:
            return [create_empty_figure()] * 13
        figs = data['figs']
        return [go.Figure(f) for f in figs[:13]]

    @app.callback(
        Output('cleanup-dummy', 'data'),
        Input('cleanup-interval', 'n_intervals')
    )
    def trigger_cleanup(n):
        clean_old_custom_files()
        return no_update

    # Add new callback for site selection
    @app.callback(
        Output('site-selector', 'options'),
        Input('interval-component', 'n_intervals')
    )
    def update_site_options(n):
        available_sites = handler.get_available_sites()
        return [
            {
                'label': site_info['name'],
                'value': site_id,
                'disabled': site_info['status'] != 'active'
            }
            for site_id, site_info in available_sites.items()
        ]

def clean_old_custom_files():
    """Remove custom JSON files older than 1 hour"""
    output_dir = "/home/iaes/DiodeSensor/FM1/output"
    now = datetime.now()
    
    for entry in os.scandir(output_dir):
        if entry.name.startswith("custom_") and entry.name.endswith(".json"):
            try:
                # Clear associated cache entries
                cache.delete(f'cached_data_{entry.name}')
                cache.delete(f'visualizations_{entry.name}')
                file_time = datetime.fromtimestamp(entry.stat().st_mtime)
                if (now - file_time) > timedelta(hours=1):
                    os.remove(entry.path)
                    print(f"Cleaned up old custom file: {entry.name}")
            except Exception as e:
                print(f"Error cleaning file {entry.name}: {e}")