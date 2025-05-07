import os
import re

import discogs_client
from dotenv import load_dotenv

load_dotenv()

consumer_key = os.getenv('DISCOGS_CONSUMER_KEY')
consumer_secret = os.getenv('DISCOGS_CONSUMER_SECRET')


# def retrieve_tokens(state):
#     # TODO: This function could get tokens from database once implemented
#     return discogs_access_token, discogs_access_token_secret


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
