import json
import discogs_client
import csv
from dotenv import load_dotenv
import os
from flask import session
import time
import re

load_dotenv()

consumer_key = os.getenv('DISCOGS_CONSUMER_KEY')
consumer_secret = os.getenv('DISCOGS_CONSUMER_SECRET')


def retrieve_tokens(state):
    # TODO: This function could get tokens from database once implemented
    return discogs_access_token, discogs_access_token_secret


def initialize_discogs_client(discogs_access_token, discogs_access_token_secret):
    if not discogs_access_token or not discogs_access_token_secret:
        return None

    d = discogs_client.Client(
        'discofy/0.1 +discofy.onrender.com',
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        token=discogs_access_token,
        secret=discogs_access_token_secret,
    )

    me = d.identity()
    print(me.username)

    return me


def import_library(discogs_access_token, discogs_access_token_secret):
    me = initialize_discogs_client(
        discogs_access_token, discogs_access_token_secret)

    username = me.username
    user_url = me.url
    folders = me.collection_folders

    library = []

    for index, folder in enumerate(folders, start=1):
        folder_item = {'index': index, 'folder': folder.name,
                       'count': f"{folder.count} records"}
        library.append(folder_item)

    response = {
        'user_info': {
            'username': username,
            'url': user_url
        },
        'library': library
    }

    return response


def import_collection(discogs_access_token, discogs_access_token_secret, folder_id=0):
    me = initialize_discogs_client(
        discogs_access_token, discogs_access_token_secret)

    collection = []
    selected_folder = me.collection_folders[folder_id]

    for index, item in enumerate(selected_folder.releases, start=1):
        artist = item.data.get('basic_information').get(
            'artists')[0].get('name')
        title = item.data.get('basic_information').get('title')
        year = item.data.get('basic_information').get('year')
        id = item.data.get('id')
        thumb = item.data.get('basic_information').get('thumb')
        url = item.data.get('basic_information').get('uri')

        artist_sanitised = re.sub(r'\s*\(\d+\)$', '', artist.strip())

        release = {'index': index, 'artist': artist_sanitised, 'title': title,
                   'year': year, 'discogs_id': id, 'cover': thumb, 'url': url}

        collection.append(release)

    return collection


def export_to_json(collection, filename="import_data.json"):
    app_folder = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(app_folder, filename)

    with open(filepath, 'w') as json_file:
        json.dump(collection, json_file, indent=2)


def export_to_csv(list, filename="discogs_collection.csv"):
    #   Append data to csv
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
