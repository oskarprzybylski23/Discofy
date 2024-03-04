import spotipy
from spotipy.oauth2 import SpotifyOAuth
import json
from dotenv import load_dotenv
from tkinter import messagebox, simpledialog
import webbrowser
import os
import subprocess
import platform
from pathlib import Path
import _tkinter
from flask import session

load_dotenv()

scope = 'playlist-modify-public'
client_id = os.getenv('SPOTIPY_CLIENT_ID')
client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
redirect_uri = os.getenv('SPOTIPY_CLIENT_URI')

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
    token = session['tokens']['access_token']
    print("Token:" + token)
    spotify = spotipy.Spotify(auth=token)

    if not spotify:
        print("User authentication failed!")
        return False

    # Playlist info
    playlist_data = read_playlist_data("collection_export.json")
    playlist_name = "Discogs Collection"  # Change this to dynamically set based on user input from the web
    playlist_description = "This is a playlist created from Discogs collection."

    try:    
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
                albums_total.append(album_id)
                track_uris_total.append(track_uris)
                tracks_number = tracks_number + len(track_uris)
                print("Added: " + artist + " - " + title + ", id: " + album_id)

            else:
                failed_export.append([artist, title])
                print("Failed to add: " + artist + " - " + title)

        print(
            "\n" + f"{tracks_number} tracks from {len(albums_total)} albums added to playlist '{playlist_name}'."
        )

        # summary message if any albums failed to load
        if len(failed_export) > 0:
            print("\n" + "Following albums failed to export or could not be found:")
            for item in failed_export:
                print(item[0] + "- " + item[1])
            print("\n" + f"{len(failed_export)} albums failed to load")
            summary_message = (
                f"\n{tracks_number} tracks from {len(albums_total)} albums added to playlist '{playlist_name}'\n"
                f"{len(failed_export)} albums failed to load")
            
        else:
            summary_message = (
                    "\n" + f"{tracks_number} tracks from {len(albums_total)} albums added to playlist '{playlist_name}'.")
            
        # create a report txt file
        create_report(failed_export, tracks_number, albums_total, playlist_name)

        return True
    
    except Exception as e:
        print(f"Error creating playlist: {e}")
        return False


def create_report(failed_items, number_of_tracks, number_of_albums, name_of_playlist):
    with open('export_report.txt', 'w') as f:
        f.write(
            f"\n{number_of_tracks} tracks from {len(number_of_albums)} albums added to playlist '{name_of_playlist}'." + "\n\n"
        )

        if len(failed_items) > 0:
            f.write(f"{len(failed_items)} Following albums failed to export or could not be found:" + "\n")

            for item in failed_items:
                f.write("\n" + item[0] + "- " + item[1])

            f.write(
                "\n" + "Album load may have failed due to incorrect album/artist name. In that case, you can try "
                       "manually changing names of the albums/artists in discogs_collection.csv file and trying again."
            )
