import json
import discogs_client
import csv
from dotenv import load_dotenv
import os
from flask import session

load_dotenv()

consumer_key = os.getenv('discogs_consumer_key')
consumer_secret = os.getenv('discogs_consumer_secret')

def import_collection():

    print("importing collection") 
    # Retrieve the stored access token and secret
    access_token = session.get('access_token')
    access_token_secret = session.get('access_token_secret')

    if not access_token or not access_token_secret:
        print("Access token or secret is missing.")
        return None

    # Initialize the Discogs client with the access token
    d = discogs_client.Client(
        'my_user_agent/1.0',
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        token=access_token,
        secret=access_token_secret,
    )

    me = d.identity()

    if not me:
        print("Failed to authenticate with the provided access token.")
        return

    print('user authorized:' + me)

    # Create a list of records in the collection with position information
    collection = []

    for index, item in enumerate(me.collection_folders[0].releases, start=1):
        release = {'index': index, 'artist': item.release.fetch('artists')[0]['name'], 'title': item.release.title,
                   'year': item.release.fetch('year'), 'discogs_id': item.release.fetch('id')}
        collection.append(release)

    export_to_json(collection)
    export_to_csv(collection)

    return collection

def export_to_json(collection, filename="collection_export.json"):
    app_folder = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(app_folder, filename)

    with open(filepath, 'w') as json_file:
        json.dump(collection, json_file, indent=2)


def export_to_csv(list, filename="discogs_collection.csv"):
    #   Append data to csv
    print("creating csv")
    filename = filename
    f = open(filename, 'w+')
    f.close

    try:
        for index, item in enumerate(list):
            with open(filename, 'a', newline='') as f:
                w = csv.writer(f)
                w.writerow(list[index].values())

        f.close

    except:
        pass
