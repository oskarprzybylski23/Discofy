import discogs_client
from flask import Flask, jsonify, request, session, redirect, url_for, render_template, send_file, current_app
import App_Disc
import App_Spot
from dotenv import load_dotenv
import os
from flask import session
from pathlib import Path

app = Flask(__name__)

app.secret_key = 'your_secret_key'  # Set this to a random secret value

load_dotenv()

consumer_key = os.getenv('discogs_consumer_key')
consumer_secret = os.getenv('discogs_consumer_secret')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_collection', methods=['GET'])
def get_collection():
    try:
        output = App_Disc.import_collection()
        return jsonify(output)
    except Exception as e:
        print(f"Error during collection import: {e}")
        return jsonify({"error": "Internal server error during collection import"}), 500

@app.route('/create_playlist', methods=['POST'])
def create_playlist():
    thread = Thread(target=App_Spot.create_playlist)
    thread.start()
    return jsonify({"status": "success"})

@app.route('/see_report')
def see_report():
    # Assuming your Flask app is located in the App directory
    # and the export_report.txt is in the parent directory
    file_path = os.path.join(current_app.root_path, '..', 'export_report.txt')
    absolute_file_path = os.path.abspath(file_path)
    print(f"Attempting to access file at: {absolute_file_path}")
    
    try:
        return send_file(absolute_file_path, as_attachment=True, download_name='export_report.txt')
    except FileNotFoundError:
        return "File not found.", 404

@app.route('/authorize_discogs', methods=['POST'])
def authorize_discogs():
    print("authorizing user")

    d = discogs_client.Client(
        'my_user_agent/1.0', consumer_key=consumer_key, consumer_secret=consumer_secret
    )

    token, secret, url = d.get_authorize_url(callback_url='http://127.0.0.1:5000/oauth_callback')

    # Save the request token and secret in the user's session or your chosen storage mechanism
    session['request_token'] = token
    session['request_token_secret'] = secret

    response_data = {"authorize_url": url}
    return jsonify(response_data)

@app.route('/oauth_callback')
def oauth_callback():
    request_token = request.args.get('oauth_token')
    oauth_verifier = request.args.get('oauth_verifier')

    # Retrieve the request token secret from the user's session
    request_token_secret = session.get('request_token_secret')

    if not request_token_secret:
        return 'Session expired or invalid request', 400

    d = discogs_client.Client(
        'my_user_agent/1.0',
        consumer_key=consumer_key,
        consumer_secret=consumer_secret
    )

    # Set the temporary request token and secret to retrieve the access token
    d.set_token(request_token, request_token_secret)

    try:
        access_token, access_token_secret = d.get_access_token(oauth_verifier)
        
        # Save the access token and secret securely for future use
        session['access_token'] = access_token
        session['access_token_secret'] = access_token_secret

        # Clear the request token and secret from the session
        session.pop('request_token', None)
        session.pop('request_token_secret', None)
        
        session['authorized'] = True  # Indicate authorization success

        return redirect(url_for('authorized_success'))
    except Exception as e:
        return f'Error during authorization: {e}'

@app.route('/check_authorization', methods=['GET'])
def check_authorization():
    authorized = session.get('authorized', False)
    return jsonify({'authorized': authorized})

@app.route('/authorized_success')
def authorized_success():
    # Render a simple page that includes JavaScript for communication
    return '''
    <html>
        <head><title>Authorization Successful</title></head>
        <body>
            <script>
                window.opener.postMessage('authorizationComplete', '*');
                window.close(); // Close the current window
            </script>
            Authorization successful! You can now close this window if it doesn't close automatically.
        </body>
    </html>
    '''

@app.route('/logout')
def logout():
    # Clear the stored access token and secret from the session
    session.pop('access_token', None)
    session.pop('access_token_secret', None)
    session.pop('authorized', None)
    # Redirect to home page or a logout confirmation page
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)