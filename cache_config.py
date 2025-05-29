import os
import threading
import logging
from flask_caching import Cache
from colorlog import ColoredFormatter
from data_processing import read_and_process_file
import plotly.graph_objects as go
from collections import defaultdict
import math
import pickle
import zlib

# ——— Dynamic output directory ———
BASE_DIR   = os.path.dirname(__file__)
# Change this if your JSONs are somewhere else
OUTPUT_DIR = os.path.join(BASE_DIR, "jsondata", "fakedata", "output")
# e.g. OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# —————————————————————————————————

formatter_cache = ColoredFormatter(
    "%(log_color)s%(levelname)s:%(name)s:%(message)s",
    datefmt=None,
    reset=True,
    log_colors={
        'DEBUG': 'purple',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    }
)
handler_cache = logging.StreamHandler()
handler_cache.setFormatter(formatter_cache)
logging.basicConfig(level=logging.INFO, handlers=[handler_cache])
logger = logging.getLogger(__name__)

cache = Cache()

# track last update times so dash doesn't keep re-fetching
last_file_timestamp = {}
file_locks = defaultdict(threading.Lock)

# --- CHUNKED CACHE HELPERS --- #
def set_in_chunks(key, data, chunk_size=500*1024):
    comp = zlib.compress(data)
    nchunks = math.ceil(len(comp) / chunk_size)
    for i in range(nchunks):
        chunk = comp[i*chunk_size:(i+1)*chunk_size]
        cache.set(f"{key}:chunk:{i}", chunk)
    cache.set(f"{key}:nchunks", nchunks)

def get_from_chunks(key):
    nchunks = cache.get(f"{key}:nchunks")
    if not nchunks:
        return None
    comp = b"".join(cache.get(f"{key}:chunk:{i}") for i in range(int(nchunks)))
    try:
        return zlib.decompress(comp)
    except Exception as e:
        logger.error(f"decompress failed for {key}: {e}")
        return None
# --- END CHUNKED CACHE HELPERS --- #

def initialize_cache():
    # Initialize site-specific caches
    cache.set('active_sites', ['FM1'])  # Initially only FM1 is active
    cache.set('site_data', {
        'FM1': {},  # Your existing FM1 data structure
        'FM2': {},  # Prepared for future use
        'FM3': {}   # Prepared for future use
    })

def update_cache_for_file(filename, site_id='FM1'):
    """Update cache for a specific site when new data arrives"""
    site_data = cache.get('site_data') or {}
    if site_id not in site_data:
        site_data[site_id] = {}
    
    file_path = os.path.join(OUTPUT_DIR, filename)

    if not os.path.isfile(file_path):
        logger.warning(f"Skipping missing file {filename!r} in {OUTPUT_DIR}")
        return

    with file_locks[file_path]:
        mod_time = os.path.getmtime(file_path)
        prev_time = last_file_timestamp.get(filename, 0)
        if mod_time <= prev_time:
            logger.debug(f"No change in {filename}, skipping.")
            return

        logger.info(f"Generating figures for {filename} …")
        try:
            data, figs, total_reports = read_and_process_file(file_path)

            # convert figs to serializable dicts
            figs_dicts = [f.to_dict() for f in figs]

            # cache raw data + timestamp
            payload = pickle.dumps({
                'data': data,
                'total_reports': total_reports,
                'timestamp': mod_time
            })
            set_in_chunks(f"cached_data_{filename}", payload)

            # cache the visualizations
            figs_payload = pickle.dumps(figs_dicts)
            set_in_chunks(f"visualizations_{filename}", figs_payload)

            cache.set(f"last_update_timestamp_{filename}", mod_time)
            last_file_timestamp[filename] = mod_time
            logger.info(f"Cache updated for {filename}")
        except Exception as e:
            logger.error(f"Error reading & caching {filename}: {e}", exc_info=True)

def get_cached_data(filename):
    payload = get_from_chunks(f"cached_data_{filename}")
    if not payload:
        logger.info(f"No cached data for {filename!r}, forcing update…")
        update_cache_for_file(filename)
        payload = get_from_chunks(f"cached_data_{filename}")
    if not payload:
        return None, 0
    stored = pickle.loads(payload)
    return stored['data'], stored['total_reports']

def get_visualizations(filename, force_refresh=True):
    logger.debug(f"Loading visuals for {filename}")
    if force_refresh:
        logger.debug(f"Force refresh for {filename}")
        update_cache_for_file(filename)

    figs_payload = get_from_chunks(f"visualizations_{filename}")
    if not figs_payload:
        logger.error(f"No figure payload for {filename!r}, returning empty figures.")
        return [go.Figure()] * 13

    try:
        figs_dicts = pickle.loads(figs_payload)
        logger.debug(f"Loaded {len(figs_dicts)} figures for {filename}")
        return [go.Figure(f) for f in figs_dicts]
    except Exception as e:
        logger.critical(f"Failed to unpickle figs for {filename}: {e}")
        return [go.Figure()] * 13

def initialize_cache():
    logger.info(f"Initializing cache from {OUTPUT_DIR}")
    if not os.path.isdir(OUTPUT_DIR):
        logger.error(f"{OUTPUT_DIR!r} does not exist! No files loaded.")
        return

    for fn in sorted(os.listdir(OUTPUT_DIR)):
        if fn.endswith(".json"):
            logger.info(f"  Preloading {fn}")
            update_cache_for_file(fn)
