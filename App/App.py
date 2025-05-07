import os
import json
from datetime import timedelta

from flask import Flask, current_app
from dotenv import load_dotenv
from flask_sslify import SSLify
from flask_talisman import Talisman
from flask_cors import CORS
from flask_session import Session
import redis

from .main import main_bp
from .spotify import spotify_bp
from .discogs import discogs_bp
from .auth import auth_bp


app = Flask(__name__)
load_dotenv()

# Register blueprints
app.register_blueprint(main_bp)
app.register_blueprint(spotify_bp, url_prefix='/spotify')
app.register_blueprint(discogs_bp, url_prefix='/discogs')
app.register_blueprint(auth_bp, url_prefix='/auth')

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


if __name__ == "__main__":
    app.run(debug=True)
