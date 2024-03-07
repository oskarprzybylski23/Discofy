import json
import discogs_client
import csv
from dotenv import load_dotenv
import os
from flask import session

load_dotenv()

consumer_key = os.getenv('discogs_consumer_key')
consumer_secret = os.getenv('discogs_consumer_secret')

def retrieve_tokens():
    access_token = session.get('access_token')
    access_token_secret = session.get('access_token_secret')

    if not access_token or not access_token_secret:
        print("Access token or secret is missing.")
        return None, None

    return access_token, access_token_secret

def initialize_discogs_client():
    access_token, access_token_secret = retrieve_tokens()
    if not access_token or not access_token_secret:
        return None
    
    d = discogs_client.Client(
        'my_user_agent/1.0',
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        token=access_token,
        secret=access_token_secret,
    )

    return d

def import_library():
    print("Fetching library")
    d = initialize_discogs_client()
    if d is None:
        print("Failed to initialize Discogs client.")
        return

    me = d.identity()
    folders = me.collection_folders
    
    library = []

    for index, folder in enumerate(folders, start=1):
        folder_item = {'index': index, 'folder': folder.name, 'count': str(folder.count) + " records"}
        library.append(folder_item)
        print(folder.releases)

    return library

def import_collection(folder_id=0):

    print("importing collection") 
    d = initialize_discogs_client()
    if d is None:
        print("Failed to initialize Discogs client.")
        return

    me = d.identity()

    print('user authorized:' + str(me))

    # Create a list of records in the collection with position information
    collection = []

    selected_folder = me.collection_folders[folder_id]

    for index, item in enumerate(selected_folder.releases, start=1):
        release = {'index': index, 'artist': item.release.fetch('artists')[0]['name'], 'title': item.release.title,
                   'year': item.release.fetch('year'), 'discogs_id': item.release.fetch('id'), 'cover': item.release.fetch('thumb')}
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
