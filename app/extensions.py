import redis
from flask_session import Session
from flask_sslify import SSLify
from flask_talisman import Talisman
from flask_cors import CORS
import logging

logger = logging.getLogger(__name__)

# Initialize Flask-Session
session = Session()

# Initialize Redis client
redis_client = None


def init_redis(app):
    global redis_client
    redis_client = redis.from_url(app.config['SESSION_REDIS'])
    logger.info("Initialized Redis client with URL: %s",
                app.config['SESSION_REDIS'])

# Initialize security extensions


def init_security(app):
    if app.config['IS_PROD']:
        # Initialize SSLify
        SSLify(app)

        # Initialize Talisman with CSP
        csp = {
            'default-src': ["'none'"],
            'connect-src': ["'self'", app.config['FRONTEND_URL']],
        }
        Talisman(app, content_security_policy=csp)
    else:
        return

# Initialize CORS


def init_cors(app):
    allowed_origins = app.config['ALLOWED_ORIGINS']
    CORS(app,
         supports_credentials=True,
         origins=allowed_origins,
         expose_headers=['Set-Cookie'],
         allow_headers=['Content-Type', 'Authorization'],
         methods=['GET', 'POST', 'OPTIONS', 'PUT', 'DELETE'],
         vary_header=True)
    logger.info("Initialized CORS with allowed origins: %s", allowed_origins)


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

    logger.info("Cleaned up %d expired sessions", count)
    return count
