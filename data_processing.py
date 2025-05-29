import os
import json
import time
import logging
import pandas as pd
from sklearn.ensemble import IsolationForest
import plotly.express as px
import plotly.graph_objects as go
import plotly.colors as colors
from colorlog import ColoredFormatter

# ——— Directories ———
BASE_DIR          = os.path.dirname(__file__)
DATA_FOLDER       = os.path.join(BASE_DIR, "jsondata", "fakedata", "output")
C9REPORTS_FOLDER  = os.path.join(BASE_DIR, "c9reports")
# ——————————————————

# set up colored logging
formatter_data = ColoredFormatter(
    "%(log_color)s%(levelname)s:%(name)s:%(message)s",
    reset=True,
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'yellow',
        'WARNING': 'orange',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    }
)
handler_data = logging.StreamHandler()
handler_data.setFormatter(formatter_data)
logging.basicConfig(level=logging.INFO, handlers=[handler_data])
logger = logging.getLogger(__name__)


def read_data(file_path):
    """
    Read either a JSON array or line-delimited JSON.
    Returns: (list_of_dicts, total_cyber9_reports)
    """
    all_data = []
    try:
        with open(file_path, 'r') as f:
            text = f.read().strip()
            if text.startswith('['):
                # standard JSON array
                items = json.loads(text)
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            all_data.append(item)
            else:
                # line-delimited JSON
                for line in text.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        if isinstance(obj, dict):
                            all_data.append(obj)
                    except json.JSONDecodeError:
                        logger.debug(f"Skipping invalid JSON line: {line[:80]}…")
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        all_data = []

    total_cyber9_reports = count_files_in_directory(C9REPORTS_FOLDER)
    return all_data, total_cyber9_reports


def count_files_in_directory(directory):
    """Count regular files in the given directory."""
    try:
        return sum(
            1
            for name in os.listdir(directory)
            if os.path.isfile(os.path.join(directory, name))
        )
    except Exception as e:
        logger.error(f"Error counting files in {directory}: {e}")
        return 0


def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """Mark rows where IsolationForest flags an anomaly."""
    required = ['TOTPACKETS', 'TOTDATA_MB', 'UNIQUE_CONNECTIONS']
    for col in required:
        if col not in df.columns:
            logger.error(f"Missing column for anomaly detection: {col}")
            return pd.DataFrame()

    df_req = df[required].apply(pd.to_numeric, errors='coerce')
    if df_req.isnull().any().any():
        logger.error("Nulls in required columns for anomaly detection")
        return pd.DataFrame()

    iso = IsolationForest(contamination=0.01)
    df['ANOMALY_IF'] = iso.fit_predict(df_req)
    return df[df['ANOMALY_IF'] == -1]


def create_visualizations(all_data, total_cyber9_reports):
    """
    Returns a tuple of 13 Plotly figures, exactly as your original code.
    If all_data is empty, returns 13 blank figs.
    """
    if not all_data:
        logger.error("No data to visualize, returning empty figures.")
        return (go.Figure(),) * 13

    df = pd.DataFrame(all_data)

    # --- Ensure every column you use exists (fill defaults) ---
    defaults = {
        'DSTIP': 'Unknown', 'SRCIP': 'Unknown', 'PROTOCOL': 'Unknown',
        'TOTPACKETS': 0, 'TOTDATA': "0 MB",
        'SRCPORT': 0, 'DSTPORT': 0
    }
    for col, default in defaults.items():
        if col not in df.columns:
            df[col] = default

    # hourly + daily columns
    hours = [f"{h}{ampm}" for ampm in ("AM","PM") for h in list(range(1,12))+[12]]
    days  = ["MON","TUE","WED","THU","FRI","SAT","SUN"]
    for col in hours + days:
        if col in df.columns:
            # convert existing Series safely
            df[col] = (
                pd.to_numeric(df[col], errors='coerce')
                  .fillna(0)
                  .astype(float)
            )
        else:
            # if entirely missing, just set float 0.0
            df[col] = 0.0


    # parse TOTDATA -> TOTDATA_MB
    df["TOTDATA_MB"] = (
        df["TOTDATA"]
        .astype(str)
        .str.replace(" MB","",regex=False)
        .pipe(pd.to_numeric, errors='coerce')
        .fillna(0)
    )

    # Indicator: total packets
    fig1 = go.Figure(go.Indicator(
        mode="number",
        value=df["TOTPACKETS"].sum(),
        title={"text":"Total Packets"}
    )).update_layout(template="plotly_dark", height=250)

    # Indicator: total connections
    fig2 = go.Figure(go.Indicator(
        mode="number",
        value=len(df),
        title={"text":"Total Connections"}
    )).update_layout(template="plotly_dark", height=250)

    # Indicator: Cyber9 line reports
    fig3 = go.Figure(go.Indicator(
        mode="number",
        value=total_cyber9_reports,
        title={"text":"Total Cyber9 Line Reports"}
    )).update_layout(template="plotly_dark", height=250)

    # Treemap: SRC→DST→PROTOCOL by packets
    fig4 = px.treemap(
        df,
        path=['SRCIP','DSTIP','PROTOCOL'],
        values='TOTPACKETS',
        template="plotly_dark",
        height=600,
        title="Source→Dest→Protocol Distribution",
        custom_data=['SRCIP', 'DSTIP', 'PROTOCOL', 'TOTPACKETS']
    )
    fig4.update_traces(
        hovertemplate="""
        Source IP: %{customdata[0]}<br>
        Destination IP: %{customdata[1]}<br>
        Protocol: %{customdata[2]}<br>
        Total Packets: %{customdata[3]:,.0f}<br>
        <extra></extra>
        """
    )

    # Pie: top 10 SRCIP by data
    totdata = df.groupby("SRCIP",as_index=False)["TOTDATA_MB"].sum()
    top10  = totdata.nlargest(10,"TOTDATA_MB")
    df["SRCIP_GROUPED"] = df["SRCIP"].where(df["SRCIP"].isin(top10["SRCIP"]), "Others")
    pie    = df.groupby("SRCIP_GROUPED",as_index=False)["TOTDATA_MB"].sum()
    fig5   = px.pie(
        pie,
        names="SRCIP_GROUPED",
        values="TOTDATA_MB",
        title="Data by Top 10 Source IP",
        template="plotly_dark",
        hover_data=["TOTDATA_MB"]
    )
    fig5.update_traces(
        hovertemplate="""
        IP: %{label}<br>
        Data: %{value:.2f} MB<br>
        <extra></extra>
        """
    )

    # Heatmap + overlay line: hourly activity
    hourly = df[hours].sum().values.reshape(1,-1)
    fig6   = go.Figure(data=go.Heatmap(
        z=hourly, 
        x=hours, 
        y=["Packets"], 
        colorscale="Jet",
        hovertemplate="Hour: %{x}<br>Packets: %{z:,.0f}<extra></extra>"
    ))
    fig6.update_layout(
        title="Hourly Packet Activity",
        template="plotly_dark"
    ).add_trace(
        go.Scatter(x=hours, y=df[hours].sum(axis=0),
                   mode="lines+markers", yaxis="y2")
    ).update_layout(yaxis2=dict(overlaying="y",side="right"))

    # Heatmap: daily activity
    daily  = df[days].sum().values.reshape(1,-1)
    fig7   = go.Figure(data=go.Heatmap(
        z=daily, x=days, y=["Packets"], colorscale="Jet"
    )).update_layout(
        title="Daily Activity Heatmap", template="plotly_dark"
    )

    # Sankey: top 10 flows by TOTDATA_MB
    sank = df.groupby(["SRCIP","DSTIP"],as_index=False)["TOTDATA_MB"].sum()
    topk = sank.nlargest(10,"TOTDATA_MB")
    nodes = list(dict.fromkeys(topk["SRCIP"].tolist() + topk["DSTIP"].tolist()))
    idx   = {n:i for i,n in enumerate(nodes)}
    fig8  = go.Figure(data=go.Sankey(
        node=dict(label=nodes, pad=15,thickness=20),
        link=dict(
            source=[idx[s] for s in topk["SRCIP"]],
            target=[idx[d] for d in topk["DSTIP"]],
            value= topk["TOTDATA_MB"]
        )
    )).update_layout(title="Top 10 IP Flows", template="plotly_dark")

    # Sankey with heatmap coloring
    norm = (topk["TOTDATA_MB"] - topk["TOTDATA_MB"].min())/\
           (topk["TOTDATA_MB"].max()-topk["TOTDATA_MB"].min())
    colorscale = colors.sample_colorscale("Jet", norm)
    fig9 = go.Figure(data=go.Sankey(
        node=dict(label=nodes, pad=15, thickness=20),
        link=dict(
            source=[idx[s] for s in topk["SRCIP"]],
            target=[idx[d] for d in topk["DSTIP"]],
            value=topk["TOTDATA_MB"],
            color=colorscale
        )
    )).update_layout(title="Sankey w/ Heatmap", template="plotly_dark")

    # Protocol usage pie
    fig10 = px.pie(
        df, names="PROTOCOL", title="Protocol Usage",
        hole=0.3, template="plotly_dark"
    ).update_traces(textinfo="percent+label")

    # Parallel categories top-10 by packets
    fig11 = px.parallel_categories(
        df.nlargest(10,"TOTPACKETS"),
        dimensions=["SRCIP","DSTIP","PROTOCOL"],
        color="TOTPACKETS",
        template="plotly_dark",
        title="Top 10 Connections"
    )

    # Stacked-area: protocol vs hour
    melt = df.melt(
        id_vars=["PROTOCOL"], value_vars=hours,
        var_name="Hour", value_name="Packets"
    )
    fig12 = px.area(
        melt, x="Hour", y="Packets", color="PROTOCOL",
        title="Hourly Traffic by Protocol", template="plotly_dark"
    )

    # Anomalies scatter
    df["CONNECTION"] = (
        df["SRCIP"]+"-"+df["DSTIP"]+"-"+
        df["SRCPORT"].astype(str)+"-"+df["DSTPORT"].astype(str)
    )
    df["UNIQUE_CONNECTIONS"] = df["CONNECTION"].nunique()
    anom = detect_anomalies(df)
    fig13 = px.scatter(
        anom, x="SRCIP", y="DSTIP",
        size="TOTDATA_MB", color="PROTOCOL",
        title="Detected Anomalies", template="plotly_dark"
    )

    return (
        fig1, fig2, fig3, fig4, fig5,
        fig6, fig7, fig8, fig9, fig10,
        fig11, fig12, fig13
    )


def read_and_process_file(file_path):
    """API for cache_config.py"""
    data, reports = read_data(file_path)
    figs = create_visualizations(data, reports)
    return data, figs, reports


class MultiSiteDataProcessor:
    def __init__(self):
        self.sites = {
            'FM1': {
                'name': 'Facility Module 1',
                'location': 'Primary Site',
                'status': 'active',
                'data_path': 'jsondata/fakedata/output'  # Current FM1 path
            },
            'FM2': {
                'name': 'Facility Module 2',
                'location': 'Secondary Site',
                'status': 'pending',
                'data_path': 'jsondata/FM2/output'
            },
            'FM3': {
                'name': 'Facility Module 3',
                'location': 'Tertiary Site',
                'status': 'pending',
                'data_path': 'jsondata/FM3/output'
            }
        }
    
    def get_active_sites(self):
        return {k: v for k, v in self.sites.items() if v['status'] == 'active'}
    
    def get_site_config(self, site_id):
        return self.sites.get(site_id)


class NetworkDataHandler:
    def __init__(self, aggregator):
        self.aggregator = aggregator
        self.site_processor = MultiSiteDataProcessor()
        
    def process_site_data(self, site_id='FM1'):
        site_config = self.site_processor.get_site_config(site_id)
        if not site_config or site_config['status'] != 'active':
            return None
            
        # Existing processing logic remains the same for now
        # as we're currently only processing FM1 data
        return self.process_data()

    # Add this new method
    def get_available_sites(self):
        return self.site_processor.get_active_sites()
