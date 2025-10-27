import os
import sqlite3
import requests
import base64
from flask import Flask, request, jsonify, redirect, render_template_string
from requests_oauthlib import OAuth2Session

# --- CONFIGURATION ---
# These MUST be set as environment variables in your AWS Elastic Beanstalk configuration.
CLIENT_ID = os.environ.get('DISCORD_CLIENT_ID')
CLIENT_SECRET = os.environ.get('DISCORD_CLIENT_SECRET')
REDIRECT_URI = os.environ.get('DISCORD_REDIRECT_URI')  # e.g., 'http://your-aws-url/callback'
BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN')  # Needed for uploading assets

API_BASE_URL = 'https://discord.com/api/v10'  # Use a specific API version
AUTHORIZATION_BASE_URL = f'{API_BASE_URL}/oauth2/authorize'
TOKEN_URL = f'{API_BASE_URL}/oauth2/token'

# Initialize the Flask app for AWS
flask_app = Flask(__name__)

# --- DATABASE SETUP ---
DATABASE_FILE = 'qobuz_oauth_users.db'


def init_db():
    """Initializes the database to store user authentication tokens."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS users
                   (
                       app_user_id
                       TEXT
                       PRIMARY
                       KEY,
                       discord_user_id
                       TEXT
                       NOT
                       NULL
                       UNIQUE,
                       access_token
                       TEXT
                       NOT
                       NULL,
                       refresh_token
                       TEXT
                       NOT
                       NULL
                   )
                   ''')
    conn.commit()
    conn.close()


# Initialize the database when the app starts
with flask_app.app_context():
    init_db()


# --- WEB PAGES FOR USER LOGIN AND REGISTRATION ---

@flask_app.route('/')
def index():
    """The main landing page with the 'Login with Discord' button."""
    return render_template_string("""
        <h1>Qobuz Discord RPC Setup</h1>
        <p>Click the button below to connect your Discord account. This will allow the app to show your Qobuz activity on your profile.</p>
        <a href="/login" style="padding: 10px; background-color: #5865F2; color: white; text-decoration: none; border-radius: 5px; font-family: sans-serif;">
            Login with Discord
        </a>
        <hr>
        <h3>Your App ID:</h3>
        <p>After logging in, you will be asked to provide your unique App ID. You can find this ID in the Android app.</p>
    """)


@flask_app.route('/login')
def login():
    """Redirects the user to Discord's official authorization page."""
    # 'rpc.activities.write' is the specific permission to update a user's activity.
    scope = ['rpc.activities.write', 'identify']
    discord = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, scope=scope)
    authorization_url, state = discord.authorization_url(AUTHORIZATION_BASE_URL)
    return redirect(authorization_url)


@flask_app.route('/callback')
def callback():
    """Handles the callback from Discord after user authorizes the app."""
    code = request.args.get('code')
    discord = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI)
    try:
        token = discord.fetch_token(
            TOKEN_URL,
            client_secret=CLIENT_SECRET,
            code=code
        )

        user_session = OAuth2Session(token=token)
        user_response = user_session.get(f'{API_BASE_URL}/users/@me')
        user_data = user_response.json()
        discord_user_id = user_data['id']

        # Present a form to the user to enter their App ID from the Android app.
        return render_template_string("""
            <h1>Almost Done!</h1>
            <p>Please enter the <strong>App ID</strong> from the Android app to complete the link.</p>
            <form action="/register_app_id" method="post" style="font-family: sans-serif;">
                <input type="hidden" name="discord_id" value="{{ discord_id }}">
                <input type="hidden" name="access_token" value="{{ access_token }}">
                <input type="hidden" name="refresh_token" value="{{ refresh_token }}">
                <label for="app_id">Your App ID:</label><br>
                <input type="text" id="app_id" name="app_id" required style="padding: 8px; margin-top: 5px; width: 300px;"><br><br>
                <input type="submit" value="Link Account" style="padding: 10px; background-color: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer;">
            </form>
        """, discord_id=discord_user_id, access_token=token['access_token'], refresh_token=token['refresh_token'])

    except Exception as e:
        return f"An error occurred during authentication: {e}", 500


@flask_app.route('/register_app_id', methods=['POST'])
def register_app_id():
    """Saves the user's tokens and links the app_user_id to their Discord ID."""
    app_user_id = request.form.get('app_id')
    discord_user_id = request.form.get('discord_id')
    access_token = request.form.get('access_token')
    refresh_token = request.form.get('refresh_token')

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    # Use INSERT OR REPLACE to handle both new registrations and re-authorizations.
    cursor.execute(
        "INSERT OR REPLACE INTO users (app_user_id, discord_user_id, access_token, refresh_token) VALUES (?, ?, ?, ?)",
        (app_user_id, discord_user_id, access_token, refresh_token)
    )
    conn.commit()
    conn.close()

    return "<h1>Success!</h1><p>Your account is linked. You can now close this page. Your Qobuz activity will appear on your Discord profile.</p>"


# --- API ENDPOINT FOR THE ANDROID APP ---

@flask_app.route('/api/update-song', methods=['POST'])
def update_song():
    """Receives song updates from the Android app and sets the user's Rich Presence."""
    data = request.get_json()
    if not data or 'userId' not in data or 'songTitle' not in data:
        return jsonify({"error": "Missing required fields"}), 400

    app_user_id = data['userId']
    song_title = data['songTitle']
    artist_name = data.get('artistName', 'Unknown Artist')
    album_art_base64 = data.get('albumArtBase64')

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT access_token FROM users WHERE app_user_id = ?", (app_user_id,))
    result = cursor.fetchone()
    conn.close()

    if not result:
        return jsonify({"error": "User not registered. Please link your account via the web page."}), 404

    access_token = result[0]

    # Step 1: Upload album art to get an asset key, if art is provided.
    asset_key = "your_default_qobuz_logo_key"  # A fallback image key you should upload once manually.
    if album_art_base64:
        try:
            asset_key = upload_asset(album_art_base64)
        except Exception as e:
            print(f"Failed to upload asset: {e}. Using default asset.")
            # If upload fails, we'll just use the default key.

    # Step 2: Set the Rich Presence using the asset key.
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    payload = {
        "pid": os.getpid(),
        "activity": {
            "details": song_title,
            "state": f"by {artist_name}",
            "assets": {
                "large_image": asset_key,
                "large_text": "Qobuz"
            },
            "type": 2  # Type 2 is "Listening to"
        }
    }

    rpc_url = f'{API_BASE_URL}/users/@me/activities'
    response = requests.put(rpc_url, headers=headers, json=payload)

    if response.status_code == 200:
        return jsonify({"message": "Activity updated successfully."}), 200
    else:
        return jsonify({"error": "Failed to update activity.", "details": response.text}), response.status_code


def upload_asset(base64_image_data: str) -> str:
    """Uploads a base64 encoded image to Discord's asset service and returns the asset key."""
    if not BOT_TOKEN or not CLIENT_ID:
        raise Exception("BOT_TOKEN and CLIENT_ID environment variables must be set for asset uploads.")

    headers = {
        'Authorization': f'Bot {BOT_TOKEN}',
        'Content-Type': 'application/json'
    }
    # The image data must be prefixed with a data URI scheme for the Discord API.
    image_data_uri = f"data:image/png;base64,{base64_image_data}"

    payload = {
        "name": f"qobuz_art_{os.urandom(8).hex()}",  # Generate a unique name for the asset.
        "type": 1,  # 1 for large image
        "image": image_data_uri,
    }

    asset_upload_url = f'{API_BASE_URL}/applications/{CLIENT_ID}/assets'
    response = requests.post(asset_upload_url, headers=headers, json=payload)

    response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)

    asset_data = response.json()
    # The asset key is the 'id' field in the returned JSON.
    return asset_data['id']
