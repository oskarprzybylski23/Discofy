import os
import json
import uuid
import time
from datetime import timedelta

from flask import jsonify, request, redirect, url_for, current_app

import discogs_client

from ..services import discogs
from ..extensions import redis_client
from . import discogs_bp

# Discogs environment variables
consumer_key = os.getenv('DISCOGS_CONSUMER_KEY')
consumer_secret = os.getenv('DISCOGS_CONSUMER_SECRET')
discogs_redirect_uri = os.getenv('DISCOGS_REDIRECT_URI')


@discogs_bp.route('/get_library', methods=['GET'])
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

        output = discogs.import_library(
            discogs_access_token, discogs_access_token_secret)
        return jsonify(output)
    except Exception as e:
        print(f"Error during collection import: {e}")
        return jsonify({"error": "Internal server error during collection import"}), 500


@discogs_bp.route('/get_collection', methods=['GET'])
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

        output = discogs.import_collection(
            discogs_access_token, discogs_access_token_secret, folder_id)
        return jsonify(output)
    except Exception as e:
        print(f"Error during collection import: {e}")
        return jsonify({"error": "Internal server error during collection import"}), 500


@discogs_bp.route('/authorize_discogs', methods=['POST'])
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
        timedelta(
            days=3),  # replace with global variable app.config["PERMANENT_SESSION_LIFETIME"]
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
        max_age=timedelta(days=3).total_seconds(),
        domain=None
    )
    print(f'Cookie set with state: {discogs_state}')
    print(f'response data: {response_data}')
    return response


@discogs_bp.route('/oauth_callback')
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

        # Clear the request token and secret (no longer needed)
        session_data.pop('request_token', None)
        session_data.pop('request_token_secret', None)

        # Update in Redis
        redis_client.setex(
            session_key,
            timedelta(days=3),
            json.dumps(session_data)
        )

        print(f"session_data update: {session_data}")

        return redirect(url_for('auth.success'))
    except Exception as e:
        return f'Error during authorization: {e}'


@discogs_bp.route('/check_authorization', methods=['GET'])
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
