# Qobuz RPC - Text-Only Server Edition
# Requires: Flask, pypresence, requests

from flask import Flask, request, jsonify
from pypresence import Presence
import threading
import time
import requests
import urllib.parse

# --- Configuration ---
DISCORD_CLIENT_ID = "928957672907227147"

# --- Global state containers ---
rpc_container = [None]
last_activity_time = time.time()
art_cache = {}

# --- Constants ---
IDLE_TIMEOUT_SECONDS = 300  # 5 minutes


# ======================================================================
# --- NEW: Final, Most Robust Album Art Function ---
# ======================================================================
def fetch_album_art_robust(song_title, artist_name):
    """
    Tries to find album art using multiple methods for the best results.
    1. Tries a specific search on TheAudioDB.
    2. If that fails, falls back to a general search on the iTunes API.
    """
    cache_key = f"{song_title}-{artist_name}"
    if cache_key in art_cache:
        # Return cached result, whether it was successful (a URL) or a failure (None)
        return art_cache[cache_key]

    # --- Method 1: Specific Search on TheAudioDB (High Accuracy) ---
    try:
        artist_encoded = urllib.parse.quote_plus(artist_name)
        song_encoded = urllib.parse.quote_plus(song_title)
        url = f"https://www.theaudiodb.com/api/v1/json/2/searchtrack.php?s={artist_encoded}&t={song_encoded}"
        print(f"  [DEBUG] Art Fetch (Step 1): Searching TheAudioDB for '{song_title}'...")

        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        if data and data.get('track'):
            art_url = data['track'][0].get('strTrackThumb')
            if art_url:
                print(f"  [DEBUG] Art Fetch (Step 1): SUCCESS -> Found on TheAudioDB.")
                art_cache[cache_key] = art_url
                return art_url
    except Exception as e:
        print(f"  [DEBUG-WARN] Art Fetch (Step 1): TheAudioDB search failed: {e}")

    # --- Method 2: Fallback to General iTunes Search (High Chance of Match) ---
    try:
        search_term = urllib.parse.quote_plus(f"{song_title} {artist_name}")
        url = f"https://itunes.apple.com/search?term={search_term}&entity=song&limit=1"
        print(f"  [DEBUG] Art Fetch (Step 2): Falling back to iTunes search...")

        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        if data.get('resultCount', 0) > 0 and data['results']:
            art_url = data['results'][0].get('artworkUrl100')
            if art_url:
                large_art_url = art_url.replace('100x100bb', '512x512bb')
                print(f"  [DEBUG] Art Fetch (Step 2): SUCCESS -> Found on iTunes.")
                art_cache[cache_key] = large_art_url
                return large_art_url
    except Exception as e:
        print(f"  [DEBUG-ERROR] Art Fetch (Step 2): iTunes fallback also failed: {e}")

    # If both methods fail
    print("  [DEBUG] Art Fetch: No art found on any platform.")
    art_cache[cache_key] = None  # Cache the failure
    return None


# ======================================================================

def update_discord_presence(title):
    """Connects to Discord and updates the Rich Presence, using the robust art search."""
    global last_activity_time
    last_activity_time = time.time()
    rpc = rpc_container[0]

    try:
        if not rpc:
            print("[RPC] State: Not connected. Attempting to connect...")
            rpc = Presence(DISCORD_CLIENT_ID)
            rpc.connect()
            rpc_container[0] = rpc
            print("[RPC] State: Connection SUCCESS.")

        if not title:
            print("[RPC] Action: Clearing presence.")
            rpc.clear()
            return

        print(f"[RPC] Action: Updating presence for title -> '{title}'")
        song_title, artist_name = (title.rsplit(' - ', 1) + ["Unknown Artist"])[:2]

        # --- KEY CHANGE: Use the new robust function ---
        art_url = fetch_album_art_robust(song_title.strip(), artist_name.strip())
        large_image_asset = art_url if art_url else "qobuz"  # Fallback to default
        # -----------------------------------------------

        payload = {
            "details": song_title.strip(),
            "state": f"by {artist_name.strip()}",
            "large_image": large_image_asset,
            "large_text": f"{song_title.strip()} - {artist_name.strip()}",
            "small_image": "qobuz_icon",
            "small_text": "Qobuz Player"
        }
        print(f"  [DEBUG] RPC Payload: {payload}")

        rpc.update(**payload)
        print("[RPC] State: Presence update sent successfully.")

    except Exception as e:
        print(f"[RPC-ERROR] A critical error occurred during update: {e}")
        if rpc_container[0]:
            try:
                rpc_container[0].close()
            except:
                pass
        rpc_container[0] = None


# ... (The rest of the file: idle_checker, the Flask routes, and the __main__ block are all unchanged and correct) ...
def idle_checker():
    """Background thread to clear presence if the app is idle."""
    while True:
        if rpc_container[0] and (time.time() - last_activity_time > IDLE_TIMEOUT_SECONDS):
            print("[RPC-IDLE] Timeout reached. Clearing presence.")
            try:
                rpc_container[0].clear()
                rpc_container[0].close()
            except:
                pass
            finally:
                rpc_container[0] = None
        time.sleep(60)


# --- Web Server Setup ---
app = Flask(__name__)


@app.route('/update', methods=['POST'])
def update_presence_route():
    data = request.get_json()
    if not data or 'title' not in data:
        return jsonify({"status": "error", "message": "Missing 'title' in request"}), 400

    song_title = data['title']
    update_discord_presence(song_title)
    return jsonify({"status": "ok"}), 200


# --- Main execution block ---
if __name__ == '__main__':
    print("==========================================================")
    print("  Qobuz RPC Text-Only Server (Robust Fallback Edition)  ")
    print("==========================================================")

    try:
        from waitress import serve

        idle_thread = threading.Thread(target=idle_checker, daemon=True)
        idle_thread.start()
        print("[SERVER] Starting Waitress server on http://0.0.0.0:5000")
        serve(app, host='0.0.0.0', port=5000, threads=8)
    except ImportError:
        print("\n[WARNING] 'waitress' not found. Using Flask's development server.")
        app.run(host='0.0.0.0', port=5000)
