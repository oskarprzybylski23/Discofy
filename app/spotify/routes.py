import json
import uuid
import time
from datetime import timedelta

from flask import jsonify, request, redirect, url_for, current_app

import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from celery.result import AsyncResult
from bleach import clean

from ..services import spotify
from ..extensions import redis_client
from . import spotify_bp
from app.services.celery_tasks import celery, transfer_collection_task

# Spotify OAuth URLs
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"


@spotify_bp.route('/transfer_collection', methods=['POST'])
def transfer_collection():
    data = request.get_json()
    spotify_state = request.cookies.get('spotify_state')
    collection_items = data.get('collection')

    if not spotify_state or not collection_items:
        current_app.logger.error("Missing state or collection items")
        return jsonify({"error": "Missing state or collection items."}), 400

    # Get the redis session with the state key
    session_key = f"discofy:state:{spotify_state}"
    session_data = redis_client.get(session_key)

    if not session_data:
        current_app.logger.error(
            "Requested session key: %s not found in Redis. Session not authorized.", session_key)
        return jsonify({"error": "Unauthorized or expired session"}), 401

    session_data = json.loads(session_data)

    if 'spotify_tokens' not in session_data or 'access_token' not in session_data.get('spotify_tokens', {}):
        current_app.logger.error(
            "Session tokens not found in session data for session key: %s", session_key)
        return jsonify({"error": "Unauthorized or incomplete Spotify session"}), 401

    access_token = session_data['spotify_tokens']['access_token']

    # Generate a unique progress key for this task
    progress_key = f"discofy:progress:{uuid.uuid4()}"

    # Start the Celery task
    task = transfer_collection_task.apply_async(
        args=[collection_items, access_token, progress_key])
    current_app.logger.debug(
        "Delegated task to Celery with task id: %s and progress key: %s", task.id, progress_key)
    return jsonify({"task_id": task.id, "progress_key": progress_key})


@spotify_bp.route('/transfer_collection_status', methods=['GET'])
def transfer_collection_status():
    progress_key = request.args.get('progress_key')
    task_id = request.args.get('task_id')
    if not progress_key or not task_id:
        current_app.logger.error("Missing progress key or task id")
        return jsonify({"error": "Missing progress_key or task_id"}), 400

    # Get progress from Redis
    progress = redis_client.get(progress_key)
    if progress:
        progress = json.loads(progress)
        current_app.logger.debug(
            "Task %s progress: %s", task_id, progress)
    else:
        current_app.logger.error(
            "Progress object not found - returning default values")
        progress = {"current": 0, "total": 0}

    # Get task state
    task = AsyncResult(task_id, app=celery)
    state = task.state
    result = task.result if task.state == 'SUCCESS' else None
    current_app.logger.debug("Task %s state: %s", task_id, task.state)
    return jsonify({"state": state, "progress": progress, "result": result})


@spotify_bp.route('/create_playlist', methods=['POST'])
def handle_create_playlist():
    data = request.get_json()
    spotify_state = request.cookies.get('spotify_state')
    playlist_items = data.get('playlist')
    playlist_name = data.get('playlist_name')

    if not spotify_state or not playlist_items:
        current_app.logger.error("Missing state or playlist items")
        return jsonify({"error": "Missing state or playlist items."}), 400

    # Get the redis session with the state key
    session_key = f"discofy:state:{spotify_state}"
    session_data = redis_client.get(session_key)

    if not session_data:
        current_app.logger.error(
            "Requested session key: %s not found in Redis. Session not authorized.", session_key)
        return jsonify({"error": "Unauthorized or expired session"}), 401

    session_data = json.loads(session_data)

    if 'spotify_tokens' not in session_data or 'access_token' not in session_data.get('spotify_tokens', {}):
        current_app.logger.error(
            "Session tokens not found in session data for session key: %s", session_key)
        return jsonify({"error": "Unauthorized or incomplete Spotify session"}), 401

    access_token = session_data['spotify_tokens']['access_token']

    sanitized_name = clean(playlist_name, tags=[], attributes={}, strip=True)
    # create a playlist and get url returned
    playlist_url = spotify.create_playlist(
        playlist_items, sanitized_name, access_token)
    if playlist_url:
        return jsonify({
            "status": "success",
            "message": "Playlist created successfully.",
            "url": playlist_url
        })
    else:
        current_app.logger.error(
            "Playlist URL not available. Failed to create playlist.")
        return jsonify({
            "status": "error",
            "message": "Failed to create playlist.",
            "url": None
        }), 500


@spotify_bp.route('/get_auth_url')
def get_auth_url():
    # Generate a unique state identifier
    current_app.logger.debug("Generating Spotify state identifier")
    spotify_state = str(uuid.uuid4())  # Unique state per request

    # Create session data
    session_data = {
        'created_at': time.time()
    }

    # Store in Redis with the state as part of the key
    session_key = f"discofy:state:{spotify_state}"
    current_app.logger.debug(
        "Creating session entry in Redis: %s", session_key)
    redis_client.setex(
        session_key,
        timedelta(days=3),
        json.dumps(session_data)
    )

    # TODO: check token caching
    oauth_object = SpotifyOAuth(
        client_id=current_app.config.get('SPOTIFY_CLIENT_ID'),
        client_secret=current_app.config.get('SPOTIFY_CLIENT_SECRET'),
        redirect_uri=current_app.config.get('SPOTIFY_REDIRECT_URI'),
        scope=current_app.config.get('SPOTIFY_SCOPE'),
        state=spotify_state,
        cache_path=".token_cache"
    )

    # Get auth url
    current_app.logger.debug("Requesting authorisation url")
    url = oauth_object.get_authorize_url()
    response_data = {"authorize_url": url}
    response = jsonify(response_data)
    response.set_cookie(
        'spotify_state',
        spotify_state,
        httponly=True,
        secure=True,
        samesite='None',
        max_age=timedelta(days=3).total_seconds(),
        domain=None
    )

    current_app.logger.info("Received authorisation url: %s", url)
    # TODO: Handle errors and return response code
    return response


@spotify_bp.route('/callback')
def callback():
    # Spotify callback receives state from url parameter passed in
    spotify_state = request.cookies.get('spotify_state')
    auth_code = request.args.get('code')

    if not auth_code or not spotify_state:
        return "Error: authorization code or state.", 400

    # Get the redis session with the state key
    session_key = f"discofy:state:{spotify_state}"
    session_data_str = redis_client.get(session_key)

    if not session_data_str:
        current_app.logger.error(
            'No session data found for Spotify callback.')
        return jsonify({"error": "Invalid or expired session state."}), 400

    session_data = json.loads(session_data_str)

    try:
        # Exchange the auth code for an access token
        token_data = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': current_app.config.get('SPOTIFY_REDIRECT_URI'),
            'client_id': current_app.config.get('SPOTIFY_CLIENT_ID'),
            'client_secret': current_app.config.get('SPOTIFY_CLIENT_SECRET'),
        }

        response = requests.post(SPOTIFY_TOKEN_URL, data=token_data)
        token_info = response.json()

        if 'error' in token_info:
            current_app.logger.error(
                "Spotify token exchange error: %s", token_info)
            return f"Spotify token error: {token_info['error_description']}", 400

        # add expiration time
        token_info['expires_at'] = int(
            time.time()) + token_info['expires_in']

        current_app.logger.info(
            "Spotify token successfully obtained. Saving in session. Expires at: %s", token_info['expires_at'])
        # Update session data with Spotify tokens
        session_data['spotify_tokens'] = token_info

        # Update in Redis
        redis_client.setex(
            session_key,
            timedelta(days=3),
            json.dumps(session_data)
        )

        return redirect(url_for('auth.success'))

    except Exception as e:
        current_app.logger.error(
            "Error handling Spotify callback: %s", e, exc_info=True)
        return jsonify({"error": "Error handling Spotify callback"}), 500


@spotify_bp.route('/check_authorization', methods=['GET'])
def check_authorization():
    """ Check if token information is present and if the access token is still valid """
    spotify_state = request.cookies.get('spotify_state')

    if not spotify_state:
        current_app.logger.warning(
            "User not authorized. Spotify session cookie not found")
        return jsonify({
            'authorized': False,
            'message': 'cookie not found'
        }), 200

    # Get the redis session with the state key
    session_key = f"discofy:state:{spotify_state}"
    session_data_str = redis_client.get(session_key)

    if not session_data_str:
        current_app.logger.warning(
            "User not authorized. Session data could not be found for session key: %s", session_key)
        return jsonify({
            'authorized': False,
            'message': 'session data not found'
        }), 200

    session_data = json.loads(session_data_str)

    # Check if token needs refresh and refresh if needed
    session_data = spotify.check_token_expiry(session_data)

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
            spotify_client = spotipy.Spotify(auth=spotify_access_token)
            user_profile = spotify_client.current_user()
            username = user_profile['id']
            user_url = user_profile['external_urls']['spotify']

            current_app.logger.info(
                "User %s connected to Spotify successfully", username)

            return jsonify({
                'authorized': True,
                'username': username,
                'url': user_url
            })

        except Exception as e:
            current_app.logger.error(
                "Error getting Spotify user profile: %s", e, exc_info=True)
            return jsonify({'authorized': False, 'error': str(e)}), 400
    else:
        # If the token is expired or not present, consider the user not authorized
        return jsonify({
            'authorized': False,
            'message': 'spotify token expired or not present'
        }), 200


@spotify_bp.route('/logout', methods=['POST'])
def logout():
    spotify_state = request.cookies.get('spotify_state')

    if not spotify_state:
        current_app.logger.warning(
            "User session cookie not found")
        return jsonify({
            "status": "error",
            "message": "No session found."
        }), 400

    session_key = f"discofy:state:{spotify_state}"

    current_app.logger.info("Removing session: %s from Redis", session_key)
    redis_client.delete(session_key)

    response = jsonify({
        "status": "success",
        "message": "Logged out successfully."
    })

    # Clear the cookie by setting it with an expired max_age
    current_app.logger.info("Clearing user cookie")
    response.set_cookie(
        'spotify_state',
        '',
        max_age=0,
        httponly=True,
        secure=True,
        samesite='None'
    )

    return response
