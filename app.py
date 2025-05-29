import os
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output, MATCH
import logging
import threading
from collector import NetworkDataAggregator, NetworkDataHandler  
from dotenv import load_dotenv
from flask import Flask, redirect, url_for, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from passlib.hash import pbkdf2_sha256
from cache_config import cache, initialize_cache
from watchdog_handler import start_watchdog
from callbacks import register_callbacks
from colorlog import ColoredFormatter
import signal
import sys
from flask_socketio import SocketIO

# Signal handler to release the port on exit
def signal_handler(sig, frame):
    print("Gracefully stopping the application...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Initialize Flask server
server = Flask(__name__)
server.config['LOGIN_DISABLED'] = True  # Disable login requirement
server.config['BYPASS_AUTH'] = True  # Add explicit bypass
load_dotenv()

# Configure colorlog
formatter = ColoredFormatter(
    "%(log_color)s%(levelname)s:%(name)s:%(message)s",
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

# Suppress Werkzeug logs
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Database config
server.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
server.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
server.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(server)

# Disable login manager
# login_manager = LoginManager()
# login_manager.init_app(server)
# login_manager.login_view = "/login"

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    registration_code = db.Column(db.String(50), nullable=True)
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())

    def set_password(self, password):
        self.password_hash = pbkdf2_sha256.hash(password)

    def check_password(self, password):
        return pbkdf2_sha256.verify(password, self.password_hash)

@server.route('/')
def index():
    return redirect('/dashboard')

@server.route('/dashboard')
def dashboard_redirect():
    return app.index()

@server.route('/register', methods=['GET', 'POST'])
def register():
    error_message = None
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        registration_code = request.form['code']
        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            error_message = 'Username or email already exists'
        elif not email.endswith('.edu'):
            error_message = 'Registration is only allowed for special email addresses'
        elif registration_code != os.getenv('AUTH_CODE'):
            error_message = 'Invalid registration code'
        elif password != confirm_password:
            error_message = 'Passwords do not match'
        if error_message is None:
            new_user = User(username=username, email=email,
                            registration_code=registration_code, is_active=True)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
    return f'''
    <!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Register</title><link rel="stylesheet" href="/assets/styles.css"></head>
    <body class="auth-body"><div class="auth-container"><div class="auth-card">
    <h2 class="auth-h2">Register</h2><form method="POST">
    <input class="auth-input" name="username" placeholder="Username" required>
    <input class="auth-input" type="email" name="email" placeholder="Email" required>
    <input class="auth-input" type="password" name="password" placeholder="Password" required>
    <input class="auth-input" type="password" name="confirm_password" placeholder="Confirm Password" required>
    <input class="auth-input" name="code" placeholder="Registration Code" required>
    {f'<p style="color:red;">{error_message}</p>' if error_message else ''}
    <button class="auth-button" type="submit">Register</button>
    </form></div></div></body></html>
    '''

# Comment out or remove the login route to prevent any redirects
# @server.route('/login', methods=['GET', 'POST'])
# def login():
#     return redirect('/dashboard')

@server.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            # Here you would typically:
            # 1. Generate a reset token
            # 2. Send email with reset link
            # 3. Store the token in the database
            return jsonify({
                'success': True,
                'message': 'Reset instructions sent'
            })
        return jsonify({
            'success': False,
            'message': 'Email not found'
        })

    return send_from_directory('templates', 'reset_password.html')

@server.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# initialize cache
cache.init_app(server, config={
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 3600
})
with server.app_context():
    initialize_cache()

# Initialize SocketIO in threading mode (falls back to Werkzeug)
socketio = SocketIO(server,
                    cors_allowed_origins='*',
                    async_mode='threading')

# Watchdog & DataHandler setup
BASE_DIR   = os.path.dirname(__file__)
WATCH_DIR  = os.path.join(BASE_DIR, "jsondata", "fakedata", "output")
OUTPUT_DIR = WATCH_DIR
aggregator = NetworkDataAggregator(WATCH_DIR, OUTPUT_DIR)
data_handler = NetworkDataHandler(aggregator)

from layouts import (
    overview_layout,
    one_hour_layout,
    twenty_four_hour_layout,
    custom_layout,
    sidebar
)

app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://use.fontawesome.com/releases/v5.15.4/css/all.css"
    ],
    server=server,
    suppress_callback_exceptions=True
)
register_callbacks(app, data_handler)

app.layout = html.Div([
    # Logo container at the top
    html.Div([
        # Left side with IAES logo and text
        html.Div([
    html.Img(src="/assets/iaes.png", className="fixed-logo"),
            html.Span("IAES - Industrial Asymmetric Environmental Surveillance", className="logo-text")
        ], className="logo-left"),
        
        # Right side with UA logo
        html.Div([
            html.Img(src="/assets/uofa.png", className="ua-logo")
        ], className="logo-right")
    ], className="logo-container"),
    
    # Main content area with sidebar and page content
    html.Div([
        # Sidebar
        dbc.Col(sidebar, width=2, className="sidebar-col"),
        
        # Page content
        dbc.Col([
    dcc.Location(id="url", refresh=False),
    html.Div(id="page-content"),
    dcc.Interval(id="interval-component", interval=30_000, n_intervals=0),
    dcc.Store(id="figs-store", data={}),
    dcc.Store(id="last-visual-update", data={}),
        ], width=10, className="content-col")
    ], className="main-container"),
])

@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')]
)
def display_page(pathname):
    if pathname == '/1_hour_data':
        return one_hour_layout
    elif pathname == '/24_hours_data':
        return twenty_four_hour_layout
    elif pathname == '/custom_data':
        return custom_layout
    else:
        return overview_layout

if __name__ == "__main__":
    logger.info("Starting the application...")
    # Start watchdog
    watchdog_thread = threading.Thread(
        target=start_watchdog,
        args=("/home/iaes/DiodeSensor/FM1/output/", app.server),
        daemon=True
    )
    watchdog_thread.start()
    # Start data handler
    task_thread = threading.Thread(
        target=data_handler.process_tasks,
        daemon=True
    )
    task_thread.start()
    # Run HTTPS via Werkzeug
    logger.info("Initializing the server")
    socketio.run(
        server,
        host=os.getenv('LOCAL_IP', '0.0.0.0'),
        port=8443,
        debug=True,
        use_reloader=True,
        allow_unsafe_werkzeug=True,
        ssl_context='adhoc'
    )
