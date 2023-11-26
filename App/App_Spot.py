import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.oauth2 import SpotifyClientCredentials
import csv
import json
from dotenv import load_dotenv
from tkinter import simpledialog
from tkinter import messagebox
import webbrowser
import os
from pathlib import Path

load_dotenv()

scope = 'playlist-modify-public'
# username = 'oskar_przybylski23'

client_id = os.getenv('SPOTIPY_CLIENT_ID')
client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
redirect_uri = os.getenv('SPOTIPY_CLIENT_URI')

for key, value in os.environ.items():
    print(f"{key}: {value}")

def create_playlist():
    oauth_object = spotipy.SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scope=scope)

    # Get the authorization URL
    auth_url = oauth_object.get_authorize_url()

    # Prompt the user to go to the authorization URL and authorize the app
    print(f"Please go to this URL: {auth_url}")
    answer = messagebox.askyesno("Spotify Authentication",
                                 f"To authorize Spotify access, please go to {auth_url}. Would you like to open the URL in your web browser?")
    if answer:
        webbrowser.open(auth_url)
        # Here you can wait for the user to input the code and return it
    else:
        return

    token_info = oauth_object.get_access_token()
    print(token_info)

    token = token_info['access_token']
    spotify = spotipy.Spotify(auth=token)

    # auth_manager = SpotifyClientCredentials()
    # spotify = spotipy.Spotify(auth_manager=auth_manager)

    question_create = messagebox.askyesno("Spotify Authentication",
                                          f"Authorized your Spoitfy account succesfully! Would you like to create a playlist now?")

    if question_create:
        pass
    else:
        return

    # Create a list of releases
    with open('discogs_collection.csv', 'r') as collection:
        reader = csv.reader(collection)

        albums = [row[1] for row in reader]
        collection.seek(0)
        artists = [row[0] for row in reader]
        releases = list(zip(artists, albums))

    # Create a new playlist
    playlist_name = "Discogs Record Collection"
    playlist_description = "This is a playlist created from Discogs collection."
    playlist = spotify.user_playlist_create(spotify.current_user()["id"], name=playlist_name, public=True,
                                            description=playlist_description)

    # Create placeholders for statistics
    albums_total = []
    track_uris_total = []
    tracks_number = 0
    failed_export = []

    # Find and add tracks to the playlist
    for release in releases:
        artist = release[0]
        title = release[1]
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
            failed_export.append([artist, title])

    #   Print some info
    print(
        "\n" + f"{tracks_number} tracks from {len(albums_total)} albums added to playlist '{playlist_name}'.")  # currently showing number of albums as number of tracks, fix!

    print("\n" + "Following albums failed to export or could not be found:")
    for item in failed_export:
        print(item[0] + "- " + item[1])
    print("\n" + f"{len(failed_export)} albums failed to load")

    # create a report txt file
    with open('export_report.txt', 'w') as f:
        f.write(
            "\n" + f" {tracks_number} tracks from {len(albums_total)} albums added to playlist '{playlist_name}'." + "\n" + "\n" + "Following albums failed to export or could not be found:" + "\n")
        for item in failed_export:
            f.write("\n" + item[0] + "- " + item[1])
        f.write("\n" + "\n" + f"{len(failed_export)} albums failed to load")
        f.write("\n" + "Album load may have failed due to incorrect album/artist name. In that case you can try manually changing names of the albums/artists in discogs_collection.csv file and trying again.")

    # show summary pop up message
    report_answer = messagebox.askyesno(title="Spotify Export", message="Playlist has been successfuly created. Not all of your records were succesfuly exported. They are either missing from Spotify or have not been found correctly. See report file for more info. Would you like to open it now?")
    if report_answer:
        os.system("notepad.exe export_report.txt")
    else:
        pass

def see_report():
    file = Path("export_report.txt")
    if file.exists():
        print ("True")
        os.system("notepad.exe export_report.txt") # opens report in notepad (!works on windows only)
    else:
        messagebox.showwarning(title="Report not found", message="The report has not been created yet. You need to create a playlists first.")
