import discogs_client
from flask import Flask, jsonify, request, session, redirect, url_for, render_template, send_file, current_app
import requests
from . import App_Disc
from . import App_Spot
from dotenv import load_dotenv
import os
from flask import session
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
from flask_sslify import SSLify
from flask_talisman import Talisman
from bleach import clean
from flask_cors import CORS
from flask_cors import cross_origin
import uuid
import json
from flask_session import Session
import redis
from datetime import timedelta


app = Flask(__name__)
load_dotenv()

IS_PROD = os.getenv("FLASK_ENV") == "production"

# TODO: rename routes more logically and reference discogs or spotify to clarity, also in variable names


# Redis session configuration
redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_REDIS"] = redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379"))
app.config["SESSION_PERMANENT"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(
    days=3)  # Adjust session expiry as needed
app.config["SESSION_USE_SIGNER"] = True  # Encrypted session cookie
app.config["SESSION_KEY_PREFIX"] = "discofy:"  # Redis key prefix
Session(app)


ALLOWED_ORIGINS = json.loads(os.getenv("ALLOWED_ORIGINS", "[]"))
CORS(app,
     supports_credentials=True,
     origins=ALLOWED_ORIGINS,
     expose_headers=['Set-Cookie'],
     allow_headers=['Content-Type', 'Authorization'],
     methods=['GET', 'POST', 'OPTIONS', 'PUT', 'DELETE'],
     vary_header=True)

FRONTEND_URL = os.getenv("FRONTEND_URL")

csp = {
    'default-src': ["'none'"],  # Block all by default
    'connect-src': ["'self'", FRONTEND_URL],
}

if IS_PROD:
    sslify = SSLify(app)
    talisman = Talisman(app, content_security_policy=csp)

app.config['SESSION_COOKIE_SECURE'] = True  # Only send cookies over HTTPS.
# Prevent JavaScript access to session cookies.
app.config['SESSION_COOKIE_HTTPONLY'] = True
# Restrict cookies to first-party or same-site context.
app.config['SESSION_COOKIE_SAMESITE'] = 'None'

# Flask app environment variables
app.secret_key = os.environ.get('APP_SECRET_KEY')

# Spotify environment variables
client_id = os.getenv('SPOTIPY_CLIENT_ID')
client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
spotify_redirect_uri = os.getenv('SPOTIPY_CLIENT_URI')
scope = 'playlist-modify-public'

# Discogs environment variables
consumer_key = os.getenv('DISCOGS_CONSUMER_KEY')
consumer_secret = os.getenv('DISCOGS_CONSUMER_SECRET')
discogs_redirect_uri = os.getenv('DISCOGS_REDIRECT_URI')

# Temporary in-memory storage for authorization states and tokens
auth_sessions = {}

# Spotify OAuth URLs
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"


@app.route('/')
# TODO: change displayed content
def index():
    # api_url = os.getenv('DOMAIN_URL', 'http://127.0.0.1:5000')
    # return render_template('index.html', api_url=api_url)
    return 'Discofy API'


@app.route('/get_library', methods=['GET'])
def get_library():
    print(f"All cookies: {request.cookies}")
    state = request.cookies.get('discogs_state')
    print(f"state: {state}")
    if not state:
        return jsonify({"error": "state parameter"}), 400

    # Get the redis session with the state key
    session_key = f"discofy:state:{state}"
    session_data = redis_client.get(session_key)
    print(f"session data: {session_data}")

    if not session_data:
        return jsonify({"error": "Unauthorized or expired session"}), 401

    session_data = json.loads(session_data)
    # session_data = auth_sessions.get(state)
    if not session_data or 'discogs_access_token' not in session_data or 'discogs_access_token_secret' not in session_data:
        return jsonify({"error": "Unauthorized or expired session"}), 401

    try:
        discogs_access_token = session_data['discogs_access_token']
        discogs_access_token_secret = session_data['discogs_access_token_secret']

        output = App_Disc.import_library(
            discogs_access_token, discogs_access_token_secret)
        return jsonify(output)
    except Exception as e:
        print(f"Error during collection import: {e}")
        return jsonify({"error": "Internal server error during collection import"}), 500


@app.route('/get_collection', methods=['GET'])
def get_collection():
    # Get folder id from query parameters, default to 0
    # TODO: Fix - error when loading folder 0 [All]
    folder_id = request.args.get('folder', default=0, type=int)
    state = request.cookies.get('discogs_state')
    print(f"getting collection with cookies: {request.cookies}")
    if not state:
        return jsonify({"error": "state parameter"}), 400

    if not folder_id:
        return jsonify({"error": "folder parameter"}), 400

    # Get the redis session with the state key
    session_key = f"discofy:state:{state}"
    session_data = redis_client.get(session_key)

    if not session_data:
        return jsonify({"error": "Unauthorized or expired session"}), 401

    session_data = json.loads(session_data)

    if not session_data or 'discogs_access_token' not in session_data or 'discogs_access_token_secret' not in session_data:
        return jsonify({"error": "Unauthorized or expired session"}), 401

    try:
        discogs_access_token = session_data['discogs_access_token']
        discogs_access_token_secret = session_data['discogs_access_token_secret']

        output = App_Disc.import_collection(
            discogs_access_token, discogs_access_token_secret, folder_id)
        return jsonify(output)
    except Exception as e:
        print(f"Error during collection import: {e}")
        return jsonify({"error": "Internal server error during collection import"}), 500


@app.route('/transfer_to_spotify', methods=['POST'])
@cross_origin(origins=ALLOWED_ORIGINS, supports_credentials=True)
def handle_transfer_to_spotify():
    data = request.get_json()
    spotify_state = request.cookies.get('spotify_state')
    collection_items = data.get('collection')

    if not spotify_state or not collection_items:
        return "Error: state or collection items.", 400

    # Get the redis session with the state key
    session_key = f"discofy:state:{spotify_state}"
    session_data = redis_client.get(session_key)

    if not session_data:
        return jsonify({"error": "Unauthorized or expired session"}), 401

    session_data = json.loads(session_data)
    if 'spotify_tokens' not in session_data or 'access_token' not in session_data.get('spotify_tokens', {}):
        return jsonify({"error": "Unauthorized or incomplete Spotify session"}), 401

    access_token = session_data['spotify_tokens']['access_token']

    try:
        output = App_Spot.transfer_from_discogs(collection_items, access_token)
        return jsonify(output)
    except Exception as e:
        print(f"Error during collection transfer: {e}")
        return jsonify({"error": "Internal server error during collection import"}), 500


@app.route('/create_playlist', methods=['POST'])
@cross_origin(origins=ALLOWED_ORIGINS, supports_credentials=True)
def handle_create_playlist():
    print('CREATING PLAYLIST')
    data = request.get_json()
    spotify_state = request.cookies.get('spotify_state')
    playlist_items = data.get('playlist')
    playlist_name = data.get('playlist_name')

    print(playlist_name)
    print(type(playlist_name))

    if not spotify_state or not playlist_items:
        return "Error: state or playlist items.", 400
    print('STEP 2')

    # Get the redis session with the state key
    session_key = f"discofy:state:{spotify_state}"
    session_data = redis_client.get(session_key)

    if not session_data:
        return jsonify({"error": "Unauthorized or expired session"}), 401

    session_data = json.loads(session_data)

    if 'spotify_tokens' not in session_data or 'access_token' not in session_data.get('spotify_tokens', {}):
        return jsonify({"error": "Unauthorized or incomplete Spotify session"}), 401

    access_token = session_data['spotify_tokens']['access_token']

    if not access_token:
        return "Error: access token.", 400
    print('sanitizing name...')
    sanitized_name = clean(playlist_name, tags=[], attributes={}, strip=True)
    # create a playlist and get url returned
    playlist_url = App_Spot.create_playlist(
        playlist_items, sanitized_name, access_token)
    if playlist_url:
        return jsonify({"status": "success", "message": "Playlist created successfully.", "url": playlist_url})
    else:
        return jsonify({"status": "error", "message": "Failed to create playlist.",  "url": None}), 500


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
    # Generate a unique state identifier
    discogs_state = str(uuid.uuid4())  # Unique state per request
    print(f"Generated state: {discogs_state}")

    d = discogs_client.Client(
        'discofy/0.1 +discofy.onrender.com', consumer_key=consumer_key, consumer_secret=consumer_secret
    )

    # Manually append state to callback URL
    callback_with_state = f"{discogs_redirect_uri}?state={discogs_state}"

    token, secret, url = d.get_authorize_url(callback_url=callback_with_state)

    # Create session data
    session_data = {
        'request_token': token,
        'request_token_secret': secret,
        'created_at': time.time()
    }

    # Store in Redis with the state as part of the key
    session_key = f"discofy:state:{discogs_state}"
    redis_client.setex(
        session_key,
        app.config["PERMANENT_SESSION_LIFETIME"],
        json.dumps(session_data)
    )

    response_data = {"authorize_url": url}
    response = jsonify(response_data)
    response.set_cookie(
        'discogs_state',
        discogs_state,
        httponly=False,
        secure=True,
        samesite='None',
        max_age=app.config["PERMANENT_SESSION_LIFETIME"].total_seconds(),
        domain=None
    )
    print(f'Cookie set with state: {discogs_state}')
    print(f'response data: {response_data}')
    return response


# Debug endpoints to check cookies and headers
@app.route('/check_cookie', methods=['GET'])
def check_cookie():
    # Get all cookies
    all_cookies = request.cookies
    state = request.cookies.get('discogs_state')

    # Get all headers for debugging
    headers = dict(request.headers)

    # Print debug info to server console
    print(f"All cookies: {all_cookies}")
    print(f"Session state cookie: {state}")
    print(f"Request headers: {headers}")

    return jsonify({
        "cookie_exists": state is not None,
        "state": state,
        "all_cookies": {k: v for k, v in all_cookies.items()},
        "headers": headers
    })


@app.route('/set_test_cookie', methods=['GET'])
def set_test_cookie():
    """A simple endpoint to test cookie setting"""
    response = jsonify({"message": "Test cookie set"})
    response.set_cookie(
        'test_cookie',
        'test_value',
        httponly=False,  # Allow JS access for easier debugging
        secure=True,
        samesite='None',
        path='/'
    )
    return response


@app.route('/oauth_callback')
def oauth_callback():
    # Discogs callback gets state from url parameter passed in /authorize_discogs
    discogs_state = request.args.get('state')
    print(f"callback state: {discogs_state}")

    # Get the redis session with the state key
    session_key = f"discofy:state:{discogs_state}"
    session_data_str = redis_client.get(session_key)

    if not session_data_str:
        print('no session data')
        return 'Invalid or expired session state.', 400

    session_data = json.loads(session_data_str)

    # Retrieve the temporary request token and secret from callback url
    request_token = request.args.get('oauth_token')
    oauth_verifier = request.args.get('oauth_verifier')

    request_token_secret = session_data.get('request_token_secret')
    print(f"request token secret: {request_token_secret}")

    d = discogs_client.Client(
        'discofy/0.1 +discofy.onrender.com',
        consumer_key=consumer_key,
        consumer_secret=consumer_secret
    )

    # Set the temporary request token and secret to retrieve the access token
    print(f"setting tokens: {request_token, request_token_secret} ...")
    d.set_token(request_token, request_token_secret)

    try:
        discogs_access_token, discogs_access_token_secret = d.get_access_token(
            oauth_verifier)

        # For now, storing it in `auth_sessions` just for the example
        session_data['discogs_access_token'] = discogs_access_token
        session_data['discogs_access_token_secret'] = discogs_access_token_secret

        print(f"auth_sessions: {auth_sessions}")

        # Clear the request token and secret (no longer needed)
        session_data.pop('request_token', None)
        session_data.pop('request_token_secret', None)

        # Update in Redis
        redis_client.setex(
            session_key,
            app.config["PERMANENT_SESSION_LIFETIME"],
            json.dumps(session_data)
        )

        print(f"session_data update: {session_data}")

        return redirect(url_for('authorized_success'))
    except Exception as e:
        return f'Error during authorization: {e}'


@app.route('/check_authorization', methods=['GET'])
def check_authorization():
    discogs_state = request.cookies.get('discogs_state')
    print(f'state: {discogs_state}')
    if not discogs_state:
        return jsonify({'authorized': False, 'error': 'state parameter'}), 400

    # Get the redis session with the state key
    session_key = f"discofy:state:{discogs_state}"
    session_data_str = redis_client.get(session_key)

    if not session_data_str:
        print('no session data')
        return jsonify({'authorized': False})

    session_data = json.loads(session_data_str)
    print(f'session_data: {session_data}')

    # session_data = auth_sessions.get(discogs_state)
    if session_data and 'discogs_access_token' in session_data and 'discogs_access_token_secret' in session_data:
        return jsonify({'authorized': True})
    else:
        return jsonify({'authorized': False})


@app.route('/authorized_success')
def authorized_success():
    # Render a simple page that includes JavaScript for communication
    return '''
    <html>
        <head><title>Authorization Successful</title></head>
        <body>
            <script>
                window.opener.postMessage(
                    'authorizationComplete', 'https://discofy.vercel.app/'); // change url to match preferred frontend
            </script>
            Authorization successful! You can now close this window if it doesn't close automatically.
        </body>
    </html>
    '''


@app.route('/spotify_auth_url')
def get_spotify_auth_url():
    print('Getting Spotify auth URL...')
    # Generate a unique state identifier
    spotify_state = str(uuid.uuid4())  # Unique state per request
    print(f"Generated state: {spotify_state}")

    # Create session data
    session_data = {
        'created_at': time.time()
    }

    # Store in Redis with the state as part of the key
    session_key = f"discofy:state:{spotify_state}"
    redis_client.setex(
        session_key,
        app.config["PERMANENT_SESSION_LIFETIME"],
        json.dumps(session_data)
    )

    # TODO: check token caching
    oauth_object = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=spotify_redirect_uri,
        scope=scope,
        state=spotify_state,
        cache_path=".token_cache"
    )
    url = oauth_object.get_authorize_url()
    response_data = {"authorize_url": url}
    response = jsonify(response_data)
    response.set_cookie(
        'spotify_state',
        spotify_state,
        httponly=False,
        secure=True,
        samesite='None',
        max_age=app.config["PERMANENT_SESSION_LIFETIME"].total_seconds(),
        domain=None
    )
    print(f'Cookie set with state: {spotify_state}')

    print(f'response data: {response_data}')
    # TODO: Handle errors and return response code
    return response


def check_spotify_token_expiry(session_data):
    """Check if the Spotify token is expired and refresh if needed"""
    if 'spotify_tokens' not in session_data:
        return session_data

    current_time = int(time.time())
    # Check if the token expires in the next 60 seconds
    if session_data['spotify_tokens'].get('expires_at', 0) - current_time < 60:
        try:
            # Refreshing the token
            refresh_token = session_data['spotify_tokens']['refresh_token']

            # If we have a refresh token, refresh the access token
            token_data = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'client_id': client_id,
                'client_secret': client_secret,
            }

            response = requests.post(SPOTIFY_TOKEN_URL, data=token_data)
            new_token_info = response.json()

            # Add expiration time
            new_token_info['expires_at'] = int(
                time.time()) + new_token_info['expires_in']

            # Make sure we keep the refresh token if it's not included in the new response
            if 'refresh_token' not in new_token_info:
                new_token_info['refresh_token'] = refresh_token

            # Update session with new tokens
            session_data['spotify_tokens'] = new_token_info
        except Exception as e:
            print(f"Error refreshing token: {e}")

    return session_data


# def check_discogs_access_token_expiry():
#     if 'tokens' not in session:
#         return  # Token not in session, handle to enable login
#     current_time = int(time.time())
#     # Check if the token expires in the next 60 seconds
#     if session['tokens']['expires_at'] - current_time < 60:
#         refresh_discogs_access_token()


# def refresh_discogs_access_token():
#     oauth_object = SpotifyOAuth(
#         client_id=client_id,
#         client_secret=client_secret,
#         redirect_uri=spotify_redirect_uri,
#         scope=scope,
#         cache_path=".token_cache"
#     )

#     # Refreshing the token
#     token_info = oauth_object.refresh_discogs_access_token(
#         session['tokens']['refresh_token'])

#     # Update the session with the new token
#     session['tokens'] = token_info

#     return token_info


@app.route('/spotify_callback')
def spotify_callback():
    # Spotify callback receives state from url parameter passed in
    spotify_state = request.cookies.get('spotify_state')
    auth_code = request.args.get('code')
    print(f'callback cookies: {request.cookies}')
    print(f'callback code: {request.args.get("code")}')

    if not auth_code or not spotify_state:
        return "Error: authorization code or state.", 400

    # Get the redis session with the state key
    session_key = f"discofy:state:{spotify_state}"
    session_data_str = redis_client.get(session_key)

    if not session_data_str:
        return "Invalid or expired state. Please try again.", 400

    session_data = json.loads(session_data_str)

    try:
        # Exchange the auth code for an access token
        token_data = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': spotify_redirect_uri,
            'client_id': client_id,
            'client_secret': client_secret,
        }

        response = requests.post(SPOTIFY_TOKEN_URL, data=token_data)
        token_info = response.json()
        # add expiration time
        token_info['expires_at'] = int(
            time.time()) + token_info['expires_in']

        # Update session data with Spotify tokens
        session_data['spotify_tokens'] = token_info

        # Update in Redis
        redis_client.setex(
            session_key,
            app.config["PERMANENT_SESSION_LIFETIME"],
            json.dumps(session_data)
        )

        return redirect(url_for('authorized_success'))
    except Exception as e:
        return f'Error during Spotify authorization: {e}'


@app.route('/check_spotify_authorization', methods=['GET'])
@cross_origin(origins=ALLOWED_ORIGINS, supports_credentials=True)
def check_spotify_authorization():
    """ Check if token information is present and if the access token is still valid """
    spotify_state = request.cookies.get('spotify_state')
    print(f'auth_status check cookies: {request.cookies}')
    if not spotify_state:
        return jsonify({'authorized': False, 'error': 'state parameter'}), 400

    # Get the redis session with the state key
    session_key = f"discofy:state:{spotify_state}"
    session_data_str = redis_client.get(session_key)

    if not session_data_str:
        return jsonify({'authorized': False})

    session_data = json.loads(session_data_str)

    # Check if token needs refresh and refresh if needed
    session_data = check_spotify_token_expiry(session_data)

    # Update session in Redis with possibly refreshed token
    redis_client.setex(
        session_key,
        app.config["PERMANENT_SESSION_LIFETIME"],
        json.dumps(session_data)
    )

    if session_data and 'spotify_tokens' in session_data and session_data['spotify_tokens'].get('expires_at', 0) > time.time():
        spotify_access_token = session_data['spotify_tokens'].get(
            'access_token')

        # Extract the username (Spotify user ID) from the user profile
        try:
            spotify = spotipy.Spotify(auth=spotify_access_token)
            user_profile = spotify.current_user()
            username = user_profile['id']
            user_url = user_profile['external_urls']['spotify']

            return jsonify({'authorized': True, 'username': username, 'url': user_url})
        except Exception as e:
            print(f"Error getting Spotify user profile: {e}")
            return jsonify({'authorized': False, 'error': str(e)})
    else:
        # If the token is expired or not present, consider the user not authorized
        return jsonify({'authorized': False})


@app.route('/logout')
# WIP - not implemented
def logout():
    # Clear the stored access token and secret from the session
    session.pop('discogs_access_token', None)
    session.pop('discogs_access_token_secret', None)
    session.pop('authorized', None)
    session.pop('tokens', None)
    # Redirect to home page or a logout confirmation page
    return redirect(url_for('index'))


def cleanup_expired_sessions():
    """
    Function to clean up expired sessions
    This can be run periodically using a scheduler or cron job
    """
    pattern = "discofy:state:*"
    keys = redis_client.keys(pattern)
    count = 0

    for key in keys:
        ttl = redis_client.ttl(key)
        if ttl <= 0:  # Already expired or no expiry
            redis_client.delete(key)
            count += 1

    print(f"Cleaned up {count} expired sessions")
    return count


if __name__ == "__main__":
    app.run(debug=True)
