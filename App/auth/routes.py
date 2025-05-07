from flask import current_app, render_template_string
from . import auth_bp


@auth_bp.route('/success')
def success():
    frontend_origin = current_app.config.get('FRONTEND_URL')
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
