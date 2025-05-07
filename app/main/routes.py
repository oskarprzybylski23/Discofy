from . import main_bp


@main_bp.route('/')
def index():
    return 'Discofy API'
