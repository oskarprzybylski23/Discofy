import os
import re

import discogs_client
from dotenv import load_dotenv
from flask import current_app

load_dotenv()

consumer_key = os.getenv('DISCOGS_CONSUMER_KEY')
consumer_secret = os.getenv('DISCOGS_CONSUMER_SECRET')


def initialize_discogs_client(discogs_access_token, discogs_access_token_secret):
    """
    Initializes and authenticates a Discogs API client.

    Uses OAuth tokens to authenticate with the Discogs API and returns the
    authenticated user's identity object.

    Args:
        discogs_access_token (str): OAuth access token for Discogs API.
        discogs_access_token_secret (str): OAuth access token secret for Discogs API.

    Returns:
        discogs_client.Identity or None: The authenticated user's identity object,
        or None if tokens are missing or invalid.
    """
    if not discogs_access_token or not discogs_access_token_secret:
        current_app.logger.warning("Missing Discogs access token or secret.")
        return None

    try:
        d = discogs_client.Client(
            'discofy/0.1 +discofy.onrender.com',
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            token=discogs_access_token,
            secret=discogs_access_token_secret,
        )
        me = d.identity()
        current_app.logger.info("Successfully initialized Discogs client for user: %s", getattr(
            me, 'username', 'unknown'))
        return me
    except Exception as e:
        current_app.logger.error(
            "Failed to initialize Discogs client: %s", e, exc_info=True)
        return None


def import_library(discogs_access_token, discogs_access_token_secret):
    """
    Fetches the user's Discogs library folder structure.

    Authenticates with the Discogs API and retrieves metadata about the user's
    collection folders (e.g. 'All', 'Uncategorized', or custom folders), including
    the name and number of records in each folder.

    Args:
        discogs_access_token (str): OAuth access token for Discogs API.
        discogs_access_token_secret (str): OAuth access token secret for Discogs API.

    Returns:
        dict: A dictionary containing:
            - 'user_info': The authenticated user's username and profile URL.
            - 'library': A list of folders with index, folder name, and record count.
    """
    me = initialize_discogs_client(
        discogs_access_token, discogs_access_token_secret)

    if not me:
        current_app.logger.error(
            "Failed to authenticate Discogs client in import_library.")
        return {"error": "Failed to authenticate with Discogs."}

    username = me.username
    user_url = me.url

    # Import library folders
    current_app.logger.info(
        "Importing library folders for user %s", username)
    folders = me.collection_folders
    library = []
    for index, folder in enumerate(folders, start=1):
        current_app.logger.debug(
            "Importing folder %d out of %d: %s, containing %d records", index, len(folders), folder.name, folder.count)

        folder_item = {
            'index': index,
            'folder': folder.name,
            'count': f"{folder.count} records"
        }

        library.append(folder_item)

    # Return user details and list of library folders
    response = {
        'user_info': {
            'username': username,
            'url': user_url
        },
        'library': library
    }

    current_app.logger.info(
        "Successfully imported %d library folders", len(library))

    return response


def import_collection(discogs_access_token, discogs_access_token_secret, folder_id=0):
    """
    Imports a user's Discogs collection data from a specified folder.

    Args:
        discogs_access_token (str): OAuth access token for the Discogs API.
        discogs_access_token_secret (str): OAuth access token secret for the Discogs API.
        folder_id (int, optional): ID of the collection folder to import from. Defaults to 0 (the "All" folder).

    Returns:
        list[dict]: A list of dictionaries, each representing a release in the collection.
    """
    me = initialize_discogs_client(
        discogs_access_token, discogs_access_token_secret)

    if not me:
        current_app.logger.error(
            "Failed to authenticate Discogs client in import_collection.")
        return []

    current_app.logger.info(
        "Importing Discogs collection for folder_id=%s", folder_id)
    collection = []
    try:
        # Get folder items data and append to collection
        selected_folder = me.collection_folders[folder_id]
        selected_folder_albums = selected_folder.releases
        for index, item in enumerate(selected_folder_albums, start=1):
            basic_info = item.data.get('basic_information', {})
            formats = basic_info.get('formats', [{}])[0]
            artist = [sanitise_string(a.get('name'))
                      for a in basic_info.get('artists', [])]
            title = basic_info.get('title')
            year = basic_info.get('year')
            discogs_id = basic_info.get('id')
            thumb = basic_info.get('thumb')
            format_name = formats.get('name')
            descriptions = formats.get('descriptions')
            url = f"https://www.discogs.com/release/{discogs_id}"

            release = {
                'index': index,
                'artists': artist,
                'title': title,
                'year': year,
                'discogs_id': discogs_id,
                'cover': thumb,
                'format': format_name,
                'descriptions': descriptions,
                'url': url
            }

            current_app.logger.debug(
                "[%d out of %d] Imported item: '%s - %s', discogs_id: %s", index, len(selected_folder_albums), artist, title, discogs_id)

            collection.append(release)

        current_app.logger.info(
            "Successfully imported %d releases from folder_id=%s", len(collection), folder_id)

    except Exception as e:
        current_app.logger.error(
            "Error importing collection from folder_id=%s: %s", folder_id, e, exc_info=True)

    return collection


def sanitise_string(string):
    """
    Util function for removing unnecessary characters from string that Discogs adds
    """
    return re.sub(r'\s*\(\d+\)$', '', string.strip())

def getCurrentUser(discogs_access_token, discogs_access_token_secret):
    me = initialize_discogs_client(
        discogs_access_token, discogs_access_token_secret)
    
    return me
    