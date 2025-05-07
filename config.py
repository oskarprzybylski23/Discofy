import os
import json
from datetime import timedelta


class Config:
    SECRET_KEY = os.environ.get('APP_SECRET_KEY')
    IS_PROD = os.getenv("FLASK_ENV") == "production"
    FRONTEND_URL = os.getenv("FRONTEND_URL")

    # Redis session configuration
    SESSION_TYPE = "redis"
    SESSION_REDIS = os.environ.get("REDIS_URL", "redis://localhost:6379")
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=3)
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = "discofy:"

    # Security settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'None'
    ALLOWED_ORIGINS = json.loads(os.getenv("ALLOWED_ORIGINS", "[]"))

    # Spotify configuration
    SPOTIFY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
    SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
    SPOTIFY_REDIRECT_URI = os.getenv('SPOTIPY_CLIENT_URI')
    SPOTIFY_SCOPE = 'playlist-modify-public'

    # Discogs configuration
    DISCOGS_CONSUMER_KEY = os.getenv('DISCOGS_CONSUMER_KEY')
    DISCOGS_CONSUMER_SECRET = os.getenv('DISCOGS_CONSUMER_SECRET')
    DISCOGS_REDIRECT_URI = os.getenv('DISCOGS_REDIRECT_URI')
