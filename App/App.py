import discogs_client
from flask import Flask, jsonify, request, session, redirect, url_for, render_template, send_file, current_app
import requests
import App_Disc
import App_Spot
from dotenv import load_dotenv
import os
from flask import session
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
from flask_sslify import SSLify
from flask_talisman import Talisman
from bleach import clean

load_dotenv()

app = Flask(__name__)
sslify = SSLify(app)

csp = {
    'default-src': [
        '\'self\'',
        'https://discofy.onrender.com',
    ],
    'style-src': [
        '\'self\'',
        'https://fonts.googleapis.com',
        '\'unsafe-inline\'',  # Allows inline styles
    ],
    'font-src': [
        '\'self\'',
        'https://fonts.gstatic.com',
    ],
    'img-src': [
        '\'self\'',
        'https://i.discogs.com',
        'https://i.scdn.co'
    ],
    'script-src': [
        '\'self\'',
        '\'unsafe-inline\'',  # Caution: Allows all inline scripts, use with care
    ],
}

talisman = Talisman(app, content_security_policy=csp)

app.config['SESSION_COOKIE_SECURE'] = True  # Only send cookies over HTTPS.
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access to session cookies.
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Restrict cookies to first-party or same-site context.

# Flask app environment variables
app.secret_key = os.environ.get('APP_SECRET_KEY')

# Spotify environment variables
client_id = os.getenv('SPOTIPY_CLIENT_ID')
client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
redirect_uri = os.getenv('SPOTIPY_CLIENT_URI')
scope = 'playlist-modify-public'

# Discogs environment variables
consumer_key = os.getenv('DISCOGS_CONSUMER_KEY')
consumer_secret = os.getenv('DISCOGS_CONSUMER_SECRET')
discogs_redirect_uri = os.getenv('DISCOGS_REDIRECT_URI')
print(discogs_redirect_uri)

# Spotify OAuth URLs
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"

@app.route('/')
def index():
    api_url = os.getenv('DOMAIN_URL', 'http://127.0.0.1:5000')
    return render_template('index.html', api_url=api_url)

@app.route('/get_library', methods=['GET'])
def get_library():
    try:
        output = App_Disc.import_library()
        return jsonify(output)
    except Exception as e:
        print(f"Error during collection import: {e}")
        return jsonify({"error": "Internal server error during collection import"}), 500

@app.route('/get_collection', methods=['GET'])
def get_collection():
    folder_id = request.args.get('folder', default=0, type=int)  # Get folder id from query parameters, default to 0
    try:
        output = App_Disc.import_collection(folder_id)
        return jsonify(output)
    except Exception as e:
        print(f"Error during collection import: {e}")
        return jsonify({"error": "Internal server error during collection import"}), 500

@app.route('/transfer_to_spotify', methods=['GET'])
def handle_transfer_to_spotify():
    check_access_token_expiry()
    try:
        output = App_Spot.transfer_from_discogs()
        return jsonify(output)
    except Exception as e:
        print(f"Error during collection transfer: {e}")
        return jsonify({"error": "Internal server error during collection import"}), 500

@app.route('/create_playlist', methods=['POST'])
def handle_create_playlist():
    check_access_token_expiry()
    data = request.get_json()
    playlist_name = data.get('name')
    sanitized_name = clean(playlist_name, tags=[], attributes={}, strip=True)
    playlist_url = App_Spot.create_playlist(sanitized_name)
    if playlist_url:
        return jsonify({"status": "success", "message": "Playlist created successfully.", "url": playlist_url})
    else:
        return jsonify({"status": "error", "message": "Failed to create playlist."}), 500

@app.route('/see_report')
def see_report():
    file_path = os.path.join(current_app.root_path, '..', 'export_report.txt')
    absolute_file_path = os.path.abspath(file_path)
    
    try:
        return send_file(absolute_file_path, as_attachment=True, download_name='export_report.txt')
    except FileNotFoundError:
        return "File not found.", 404

@app.route('/authorize_discogs', methods=['POST'])
def authorize_discogs():

    d = discogs_client.Client(
        'discofy/0.1', consumer_key=consumer_key, consumer_secret=consumer_secret
    )

    token, secret, url = d.get_authorize_url(callback_url=discogs_redirect_uri)

    # Save the request token and secret in the user's session or your chosen storage mechanism
    session['request_token'] = token
    session['request_token_secret'] = secret

    response_data = {"authorize_url": url}
    return jsonify(response_data)

@app.route('/oauth_callback')
def oauth_callback():
    request_token = request.args.get('oauth_token')
    oauth_verifier = request.args.get('oauth_verifier')

    # Retrieve the request token secret from the user's session
    request_token_secret = session.get('request_token_secret')

    if not request_token_secret:
        return 'Session expired or invalid request', 400

    d = discogs_client.Client(
        'discofy/0.1',
        consumer_key=consumer_key,
        consumer_secret=consumer_secret
    )

    # Set the temporary request token and secret to retrieve the access token
    d.set_token(request_token, request_token_secret)

    try:
        access_token, access_token_secret = d.get_access_token(oauth_verifier)
        
        # Save the access token and secret securely for future use
        session['access_token'] = access_token
        session['access_token_secret'] = access_token_secret

        # Clear the request token and secret from the session
        session.pop('request_token', None)
        session.pop('request_token_secret', None)
        
        session['authorized'] = True  # Indicate authorization success

        return redirect(url_for('authorized_success'))
    except Exception as e:
        return f'Error during authorization: {e}'

@app.route('/check_authorization', methods=['GET'])
def check_authorization():
    authorized = session.get('authorized', False)
    return jsonify({'authorized': authorized})

@app.route('/authorized_success')
def authorized_success():
    # Render a simple page that includes JavaScript for communication
    return '''
    <html>
        <head><title>Authorization Successful</title></head>
        <body>
            <script>
                window.opener.postMessage('authorizationComplete', '*');
                window.close(); // Close the current window
            </script>
            Authorization successful! You can now close this window if it doesn't close automatically.
        </body>
    </html>
    '''

@app.route('/spotify_auth_url')
def get_spotify_auth_url():
    oauth_object = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope,
        cache_path=".token_cache"
    )
    auth_url = oauth_object.get_authorize_url()
    return jsonify({'auth_url': auth_url})


def exchange_code_for_token(auth_code):
    oauth_object = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope,
        cache_path=".token_cache"
    )
    token_info = oauth_object.get_access_token(code=auth_code)
    return token_info

def check_access_token_expiry():
    if 'tokens' not in session:
        return  # Token not in session, handle to enable login
    current_time = int(time.time())
    if session['tokens']['expires_at'] - current_time < 60:  # Check if the token expires in the next 60 seconds
        refresh_access_token()

def refresh_access_token():
    oauth_object = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope,
        cache_path=".token_cache"
    )

    # Refreshing the token
    token_info = oauth_object.refresh_access_token(session['tokens']['refresh_token'])

    # Update the session with the new token
    session['tokens'] = token_info

    return token_info

@app.route('/login')
def login():
    auth_url = f"{SPOTIFY_AUTH_URL}?client_id={client_id}&response_type=code&redirect_uri={redirect_uri}&scope=playlist-modify-private"
    return redirect(auth_url)

@app.route('/spotify_callback')
def spotify_callback():
    code = request.args.get('code')
    
    if not code:
        return "Error: No authorization code received. Please try again."
        
    # Now exchange the auth code for an access token
    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri,
        'client_id': client_id,
        'client_secret': client_secret,
    }

    response = requests.post(SPOTIFY_TOKEN_URL, data=token_data)
    token_info = response.json()
    token_info['expires_at'] = int(time.time()) + token_info['expires_in']
    session['tokens'] = token_info  # Store token info in the session
    return render_template('close_window.html')

@app.route('/check_spotify_authorization', methods=['GET'])
def check_spotify_authorization():
    # Check if token information is present and if the access token is still valid
    if 'tokens' in session and session['tokens'].get('expires_at', 0) > time.time():

        # Extract the username (Spotify user ID) from the user profile
        spotify = spotipy.Spotify(auth=session['tokens']['access_token'])
        user_profile = spotify.current_user()
        username = user_profile['id']
        user_url = user_profile['external_urls']['spotify']

        return jsonify({'authorized': True, 'username': username, 'url': user_url})
    else:
        # If the token is expired or not present, consider the user not authorized
        return jsonify({'authorized': False})

@app.route('/logout')
def logout():
    # Clear the stored access token and secret from the session
    session.pop('access_token', None)
    session.pop('access_token_secret', None)
    session.pop('authorized', None)
    session.pop('tokens', None)
    # Redirect to home page or a logout confirmation page
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)