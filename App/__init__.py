from flask import Flask
from config import Config
from .extensions import session, init_cors, init_security, init_redis


def create_app(config=Config):
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(config)

    # Initialize extensions
    session.init_app(app)
    init_redis(app)
    init_cors(app)
    init_security(app)

    # Register blueprints
    from .main import main_bp
    from .spotify import spotify_bp
    from .discogs import discogs_bp
    from .auth import auth_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(spotify_bp, url_prefix='/spotify')
    app.register_blueprint(discogs_bp, url_prefix='/discogs')
    app.register_blueprint(auth_bp, url_prefix='/auth')

    return app
