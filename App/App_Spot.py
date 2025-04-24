import spotipy
import json
from dotenv import load_dotenv
from flask import session
import os
from datetime import datetime

load_dotenv()


def read_collection_data(file_path):
    with open(file_path, 'r') as json_file:
        collection_data = json.load(json_file)
    return collection_data


def read_playlist_data(file_path):
    with open(file_path, 'r') as json_file:
        playlist_data = json.load(json_file)
    return playlist_data


def transfer_from_discogs(collection_items, access_token):

    if not access_token:
        print('Access token is missing.')
        return []

    spotify = spotipy.Spotify(auth=access_token)
    export_items = []

    # Find and add tracks to the playlist
    for item in collection_items:
        artist = item['artist']
        title = item['title']
        # TODO: refine query and add limit to avoid more than 1 result
        search_result = spotify.search(
            q=f"artist:{artist} album:{title}", type="album")
        discogs_id = item['discogs_id']

        # check if there are albums returned from search and accept the first reseult
        # TODO: perform search and select matching album more intelligently
        if search_result["albums"]["items"]:
            # log for development only
            album = search_result["albums"]["items"][0]
            album_data = {
                "artist": album["artists"][0]["name"],
                "title": album["name"],
                # Make sure to check the correct index for the desired image size
                "image": album["images"][0]["url"],
                "url": album["external_urls"]["spotify"],
                "id": album["id"],
                "uri": album["uri"],
                "discogs_id": discogs_id,
                "found": True,
            }

            export_items.append(album_data)

        else:
            # TODO: Use datatype to include all fields even if empty for consistency
            album_data = {
                "artist": artist,
                "title": title,
                "discogs_id": discogs_id,
                "found": False
            }

            export_items.append(album_data)

    return export_items


def create_playlist(playlist_items, name, access_token):
    if not access_token:
        print('Access token is missing.')
        return

    spotify = spotipy.Spotify(auth=access_token)
    user_id = spotify.current_user()["id"]
    playlist_description = "This is a playlist created from Discogs collection using Discofy"

    try:
        playlist = spotify.user_playlist_create(
            user_id, name=name, public=True, description=playlist_description
        )

        # Create placeholder for statistics
        tracks_number = 0

        # Find and add tracks to the playlist
        for item in playlist_items:
            album_id = item["uri"]
            tracks = spotify.album_tracks(album_id)["items"]
            # get album track uris
            track_uris = [track["uri"]
                          for track in tracks]
            spotify.playlist_add_items(playlist["id"], track_uris)

            # TODO: statistics can be done cleaner
            # statistics
            tracks_number = tracks_number + len(tracks)

        playlist_url = playlist["external_urls"]["spotify"]
        # create_report(playlist_data, tracks_number,
        #               playlist_name, playlist_url)

        return playlist_url

    except Exception as e:
        print(f"Error creating playlist: {e}")
        return False


def save_export_data_to_json(playlist, filename="export_data.json"):
    app_folder = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(app_folder, filename)

    with open(filepath, 'w') as json_file:
        json.dump(playlist, json_file, indent=2)


def create_report(albums_data, number_of_tracks, name_of_playlist, playlist_url):
    successful_items = [album for album in albums_data if album['found']]
    failed_items = [album for album in albums_data if not album['found']]

    # Format: Year-Month-Day Hour:Minute:Second
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    app_name = "Discofy"
    github_link = "https://github.com/oskarprzybylski23/Discogs-Spotify-Playlist-Creator"

    with open('export_report.txt', 'w') as f:
        # Header with general information
        f.write(
            f"Export Report - {app_name}\n"
            f"Export Time: {current_time}\n"
            f"Link to Playlist: {playlist_url}\n"
            f"\n{number_of_tracks} tracks from {len(successful_items)} albums added to playlist '{name_of_playlist}'" + "\n\n"
        )

        # Section for successfully added albums
        if successful_items:
            f.write(f"Albums exported successfully:\n")
            for item in successful_items:
                f.write(f"\n{item['artist']} - {item['title']}")

        # Spacer between sections
        f.write("\n\n")

        # Section for albums that failed to export
        if failed_items:
            f.write(
                f"{len(failed_items)} albums failed to export or could not be found:\n")
            for item in failed_items:
                f.write(f"\n{item['artist']} - {item['title']}")

            # Spacer between sections
            f.write("\n\n")

            f.write(
                "Album export may have failed due to album not being available in Spotify or artist/album name not matching between the platforms. You can try manually searching for these albums in the Spotify catalog,"
            )

        f.write(
            f"Thank you for using Discofy, if you want to explore the project, contribute or raise an issue: please visit the project repository: {github_link}\n\n"
        )
