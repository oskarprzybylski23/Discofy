import os
import json
import uuid
import time
from datetime import timedelta

from flask import jsonify, request, redirect, url_for, current_app
from flask_cors import cross_origin

import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from bleach import clean

from ..services import spotify
from ..extensions import redis_client
from . import spotify_bp

ALLOWED_ORIGINS = json.loads(os.getenv("ALLOWED_ORIGINS", "[]"))

# Spotify OAuth URLs
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"


# Spotify environment variables
client_id = os.getenv('SPOTIPY_CLIENT_ID')
client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
spotify_redirect_uri = os.getenv('SPOTIPY_CLIENT_URI')
scope = 'playlist-modify-public'


@spotify_bp.route('/transfer_to_spotify', methods=['POST'])
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
        output = spotify.transfer_from_discogs(collection_items, access_token)
        return jsonify(output)
    except Exception as e:
        print(f"Error during collection transfer: {e}")
        return jsonify({"error": "Internal server error during collection import"}), 500


@spotify_bp.route('/create_playlist', methods=['POST'])
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
    playlist_url = spotify.create_playlist(
        playlist_items, sanitized_name, access_token)
    if playlist_url:
        return jsonify({"status": "success", "message": "Playlist created successfully.", "url": playlist_url})
    else:
        return jsonify({"status": "error", "message": "Failed to create playlist.",  "url": None}), 500


@spotify_bp.route('/spotify_auth_url')
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
        timedelta(days=3),
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
        max_age=timedelta(days=3).total_seconds(),
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


@spotify_bp.route('/spotify_callback')
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

        if 'error' in token_info:
            print("Spotify token exchange error:", token_info)
            return f"Spotify token error: {token_info['error_description']}", 400

        # add expiration time
        token_info['expires_at'] = int(
            time.time()) + token_info['expires_in']

        # Update session data with Spotify tokens
        session_data['spotify_tokens'] = token_info

        # Update in Redis
        redis_client.setex(
            session_key,
            timedelta(days=3),
            json.dumps(session_data)
        )

        return redirect(url_for('authorized_success'))
    except Exception as e:
        return f'Error during Spotify authorization: {e}'


@spotify_bp.route('/check_spotify_authorization', methods=['GET'])
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
        timedelta(days=3),
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
