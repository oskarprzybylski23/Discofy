import json
import uuid
import time
from datetime import timedelta

from flask import jsonify, request, redirect, url_for, current_app

import discogs_client

from ..services import discogs
from ..extensions import redis_client
from . import discogs_bp


@discogs_bp.route('/get_library', methods=['GET'])
def get_library():
    discogs_state = request.cookies.get('discogs_state')

    if not discogs_state:
        return jsonify({"error": "state parameter"}), 400

    # Get the redis session with the state key
    session_key = f"discofy:state:{discogs_state}"
    session_data = redis_client.get(session_key)

    if not session_data:
        current_app.logger.error(
            "Requested session key: %s not found in Redis. Session not authorized.", session_key)
        return jsonify({"error": "Unauthorized or expired session"}), 401

    session_data = json.loads(session_data)
    # session_data = auth_sessions.get(state)
    if not session_data or 'discogs_access_token' not in session_data or 'discogs_access_token_secret' not in session_data:
        current_app.logger.error(
            "Session tokens not found in session data for session key: %s", session_key)
        return jsonify({"error": "Unauthorized or incomplete Discogs session"}), 401

    try:
        discogs_access_token = session_data['discogs_access_token']
        discogs_access_token_secret = session_data['discogs_access_token_secret']

        output = discogs.import_library(
            discogs_access_token, discogs_access_token_secret)

        return jsonify(output)

    except Exception as e:
        current_app.logger.error(
            "Error during collection import: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error during collection import"}), 500


@discogs_bp.route('/get_folder_contents', methods=['GET'])
def get_folder_contents():
    # Get folder id from query parameters, default to 0 [All records]
    folder_id = request.args.get('folder', 0, type=int)
    discogs_state = request.cookies.get('discogs_state')

    if not discogs_state:
        current_app.logger.error("Missing state")
        return jsonify({"error": "state parameter"}), 400
    # Get the redis session with the state key
    session_key = f"discofy:state:{discogs_state}"
    session_data = redis_client.get(session_key)

    if not session_data:
        current_app.logger.error(
            "Requested session key: %s not found in Redis. Session not authorized.", session_key)
        return jsonify({"error": "Unauthorized or expired session"}), 401

    session_data = json.loads(session_data)

    if 'discogs_access_token' not in session_data or 'discogs_access_token_secret' not in session_data:
        current_app.logger.error(
            "Session tokens not found in session data for session key: %s", session_key)
        return jsonify({"error": "Unauthorized or expired session"}), 401

    try:
        discogs_access_token = session_data['discogs_access_token']
        discogs_access_token_secret = session_data['discogs_access_token_secret']

        output = discogs.import_collection(
            discogs_access_token, discogs_access_token_secret, folder_id)

        return jsonify(output)

    except Exception as e:
        current_app.logger.error(
            "Error during collection import: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error during collection import"}), 500


@discogs_bp.route('/get_auth_url', methods=['POST'])
def get_auth_url():
    # Generate a unique state identifier
    current_app.logger.debug("Generating Discogs state identifier")
    discogs_state = str(uuid.uuid4())  # Unique state per request

    d = discogs_client.Client(
        'discofy/0.1 +discofy.onrender.com',
        consumer_key=current_app.config.get('DISCOGS_CONSUMER_KEY'),
        consumer_secret=current_app.config.get('DISCOGS_CONSUMER_SECRET')
    )

    # Manually append state to callback URL
    discogs_redirect_uri = current_app.config.get('DISCOGS_REDIRECT_URI')
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
    current_app.logger.debug(
        "Creating session entry in Redis: %s", session_key)
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
        httponly=True,
        secure=True,
        samesite='None',
        max_age=timedelta(days=3).total_seconds(),
        domain=None
    )

    current_app.logger.info("Received authorisation url: %s", url)

    return response


@discogs_bp.route('/callback')
def callback():
    # Discogs callback gets state from url parameter passed in /authorize_discogs
    discogs_state = request.args.get('state')

    # Get the redis session with the state key
    session_key = f"discofy:state:{discogs_state}"
    session_data_str = redis_client.get(session_key)

    if not session_data_str:
        current_app.logger.error('No session data found for Discogs callback.')
        return jsonify({"error": "Invalid or expired session state."}), 400

    session_data = json.loads(session_data_str)

    # Retrieve the temporary request token and secret from callback url
    request_token = request.args.get('oauth_token')
    oauth_verifier = request.args.get('oauth_verifier')

    request_token_secret = session_data.get('request_token_secret')

    d = discogs_client.Client(
        'discofy/0.1 +discofy.onrender.com',
        consumer_key=current_app.config.get('DISCOGS_CONSUMER_KEY'),
        consumer_secret=current_app.config.get('DISCOGS_CONSUMER_SECRET')
    )

    # Set the temporary request token and secret to retrieve the access token
    d.set_token(request_token, request_token_secret)

    try:
        discogs_access_token, discogs_access_token_secret = d.get_access_token(
            oauth_verifier)

        current_app.logger.info(
            "Discogs token successfully obtained. Saving in session")
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

        return redirect(url_for('auth.success'))
    except Exception as e:
        current_app.logger.error(
            "Error handling Discogs callback: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error during authorization"}), 500


@discogs_bp.route('/check_authorization', methods=['GET'])
def check_authorization():
    discogs_state = request.cookies.get('discogs_state')

    if not discogs_state:
        current_app.logger.warning(
            "User not authorized. Discogs session cookie not found")
        return jsonify({
            'authorized': False,
            'message': 'cookie not found'
        }), 200

    # Get the redis session with the state key
    session_key = f"discofy:state:{discogs_state}"
    session_data_str = redis_client.get(session_key)

    if not session_data_str:
        current_app.logger.warning(
            "User not authorized. Session data could not be found for session key: %s", session_key)
        return jsonify({'authorized': False})

    session_data = json.loads(session_data_str)

    if 'discogs_access_token' in session_data and 'discogs_access_token_secret' in session_data:
        discogs_access_token = session_data['discogs_access_token']
        discogs_access_token_secret = session_data['discogs_access_token_secret']
        # Retrieve connected user data
        current_user = discogs.getCurrentUser(discogs_access_token, discogs_access_token_secret)
        current_app.logger.info(
            "User %s connected to Discogs successfully", current_user.username)
        return jsonify({
            'authorized': True,
            'username': current_user.username,
            'user_id': current_user.id,
            'url': current_user.url
        })
    else:
        return jsonify({'authorized': False})


@discogs_bp.route('/logout', methods=['POST'])
def logout():
    discogs_state = request.cookies.get('discogs_state')

    if not discogs_state:
        current_app.logger.warning(
            "User session cookie not found")
        return jsonify({
            "status": "error",
            "message": "No session found."
        }), 400

    session_key = f"discofy:state:{discogs_state}"

    current_app.logger.info("Removing session: %s from Redis", session_key)
    redis_client.delete(session_key)

    response = jsonify({
        "status": "success",
        "message": "Logged out successfully."
    })

    # Clear the cookie by setting it with an expired max_age
    current_app.logger.info("Clearing user cookie")
    response.set_cookie(
        'discogs_state',
        '',
        max_age=0,
        httponly=True,
        secure=True,
        samesite='None'
    )

    return response
