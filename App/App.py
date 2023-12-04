
from flask import Flask, render_template, jsonify, request
import App_Disc
import App_Spot

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_collection', methods=['GET'])
def get_collection():
    output = App_Disc.import_collection()
    return jsonify(output)

@app.route('/create_playlist', methods=['POST'])
def create_playlist():
    thread = Thread(target=App_Spot.create_playlist)
    thread.start()
    return jsonify({"status": "success"})

@app.route('/see_report', methods=['GET'])
def see_report():
    App_Spot.see_report()
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(debug=True)