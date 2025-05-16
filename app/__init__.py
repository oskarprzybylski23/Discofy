import sys
import logging

from flask import Flask
from config import Config
from .extensions import session, init_cors, init_security, init_redis, init_logging


def create_app(config=Config):
    app = Flask(__name__)

    # Set up logging using the extensions module
    init_logging(app)
    app.logger.info("Creating Flask App")

    # Load configuration
    app.config.from_object(config)
    app.logger.info("Loaded configuration from object: %s", config)

    # Initialize extensions
    session.init_app(app)
    app.logger.info("Initialized session extension")
    init_redis(app)
    app.logger.info("Initialized Redis extension")
    init_cors(app)
    app.logger.info("Initialized CORS extension")
    init_security(app)
    app.logger.info("Initialized security extension")

    # Register blueprints
    from .main import main_bp
    from .spotify import spotify_bp
    from .discogs import discogs_bp
    from .auth import auth_bp

    app.register_blueprint(main_bp)
    app.logger.info("Registered main blueprint")
    app.register_blueprint(spotify_bp, url_prefix='/spotify')
    app.logger.info("Registered spotify blueprint")
    app.register_blueprint(discogs_bp, url_prefix='/discogs')
    app.logger.info("Registered discogs blueprint")
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.logger.info("Registered auth blueprint")

    return app
