from flask import Blueprint

discogs_bp = Blueprint('discogs', __name__)

from . import routes 