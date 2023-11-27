import spotipy
from spotipy.oauth2 import SpotifyOAuth
import csv
import json
from dotenv import load_dotenv
from tkinter import messagebox
import webbrowser
import os
from pathlib import Path

load_dotenv()

scope = 'playlist-modify-public'
client_id = os.getenv('SPOTIPY_CLIENT_ID')
client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
redirect_uri = os.getenv('SPOTIPY_CLIENT_URI')

for key, value in os.environ.items():
    print(f"{key}: {value}")


def authenticate_spotify():
    # Create the authorization object
    oauth_object = SpotifyOAuth(
        client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scope=scope,
        cache_path=".token_cache"
    )
    # Get the authorization URL
    auth_url = oauth_object.get_authorize_url()
    # Prompt the user to go to the authorization URL and authorize the app
    answer = messagebox.askyesno(
        "Spotify Authentication",
        f"To authorize Spotify access, please go to {auth_url}. Would you like to open the URL in your web browser?"
    )
    if answer:
        webbrowser.open(auth_url)
    else:
        return

    token_info = oauth_object.get_access_token()

    if 'access_token' in token_info:
        token = token_info['access_token']
        print("Token:" + token)
        spotify = spotipy.Spotify(auth=token)
        return spotify
    else:
        return


def read_playlist_data(file_path):
    with open(file_path, 'r') as json_file:
        playlist_data = json.load(json_file)
    return playlist_data


def create_playlist():
    spotify = authenticate_spotify()

    if not spotify:
        print("User authentication failed!")
        return

    question_create = messagebox.askyesno(
        "Spotify Authentication",
        f"Authorized your Spotify account succesfully! Would you like to create a playlist now?"
    )

    if not question_create:
        return

    # Create a list of releases
    playlist_data = read_playlist_data("collection_export.json")

    # Create a new playlist
    playlist_name = "Discogs Record Collection"
    playlist_description = "This is a playlist created from Discogs collection."
    playlist = spotify.user_playlist_create(
        spotify.current_user()["id"], name=playlist_name, public=True, description=playlist_description
    )

    # Create placeholders for statistics
    albums_total = []
    track_uris_total = []
    tracks_number = 0
    failed_export = []

    # Find and add tracks to the playlist
    for release in playlist_data:
        artist = release['artist']
        title = release['title']
        result = spotify.search(q=f"artist:{artist} album:{title}", type="album")

        if result["albums"]["items"]:
            album = result["albums"]["items"][0]
            album_id = album["id"]
            tracks = spotify.album_tracks(album_id)["items"]
            track_uris = [track["uri"] for track in tracks]
            spotify.playlist_add_items(playlist["id"], track_uris)
            print("Added: " + artist + " - " + title + ", id: " + album_id)
            albums_total.append(album_id)
            track_uris_total.append(track_uris)
            tracks_number = tracks_number + len(track_uris)

        else:
            print("Failed to add: " + artist + " - " + title)
            failed_export.append([artist, title])

    #   Print some info
    print(
        "\n" + f"{tracks_number} tracks from {len(albums_total)} albums added to playlist '{playlist_name}'."
    )  # currently showing number of albums as number of tracks, fix!

    print("\n" + "Following albums failed to export or could not be found:")
    for item in failed_export:
        print(item[0] + "- " + item[1])
    print("\n" + f"{len(failed_export)} albums failed to load")

    # create a report txt file
    with open('export_report.txt', 'w') as f:
        f.write(
            "\n" + f" {tracks_number} tracks from {len(albums_total)} albums added to playlist '{playlist_name}'." + "\n" + "\n" + "Following albums failed to export or could not be found:" + "\n"
        )
        for item in failed_export:
            f.write("\n" + item[0] + "- " + item[1])
        f.write("\n" + "\n" + f"{len(failed_export)} albums failed to load")
        f.write(
            "\n" + "Album load may have failed due to incorrect album/artist name. In that case you can try manually changing names of the albums/artists in discogs_collection.csv file and trying again."
        )

    # show summary pop up message
    report_answer = messagebox.askyesno(
        title="Spotify Export",
        message="Playlist has been successfuly created. Not all of your records were succesfuly exported. They are either missing from Spotify or have not been found correctly. See report file for more info. Would you like to open it now?"
    )
    if report_answer:
        os.system("notepad.exe export_report.txt")
    else:
        pass


def see_report():
    file = Path("export_report.txt")
    if file.exists():
        print("True")
        os.system("notepad.exe export_report.txt")  # opens report in notepad (!works on windows only)
    else:
        messagebox.showwarning(
            title="Report not found",
            message="The report has not been created yet. You need to create a playlists first."
        )
