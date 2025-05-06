import os
import json
from datetime import timedelta

from flask import Flask, session, redirect, url_for, current_app, render_template_string
from dotenv import load_dotenv
from flask_sslify import SSLify
from flask_talisman import Talisman
from flask_cors import CORS
from flask_session import Session
import redis

from .extensions import redis_client
from .spotify import spotify_bp
from .discogs import discogs_bp


app = Flask(__name__)
load_dotenv()

# Register blueprints

app.register_blueprint(spotify_bp, url_prefix='/spotify')
app.register_blueprint(discogs_bp, url_prefix='/discogs')

IS_PROD = os.getenv("FLASK_ENV") == "production"

# TODO: rename routes more logically and reference discogs or spotify to clarity, also in variable names


# Redis session configuration
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


@app.route('/')
# TODO: change displayed content
def index():
    # api_url = os.getenv('DOMAIN_URL', 'http://127.0.0.1:5000')
    # return render_template('index.html', api_url=api_url)
    return 'Discofy API'


@app.route('/authorized_success')
@app.route('/authorized_success')
def authorized_success():
    frontend_origin = FRONTEND_URL
    return render_template_string('''
    <html>
        <head><title>Authorization Successful</title></head>
        <body>
            <script>
                window.opener.postMessage(
                    'authorizationComplete', '{{ frontend_origin }}');
            </script>
            Authorization successful! You can now close this window if it doesn't close automatically.
        </body>
    </html>
    ''', frontend_origin=frontend_origin)


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
