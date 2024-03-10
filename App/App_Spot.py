import spotipy
import json
from dotenv import load_dotenv
from flask import session
import os

load_dotenv()

def read_collection_data(file_path):
    with open(file_path, 'r') as json_file:
        collection_data = json.load(json_file)
    return collection_data

def read_playlist_data(file_path):
    with open(file_path, 'r') as json_file:
        playlist_data = json.load(json_file)
    return playlist_data

def transfer_from_discogs():
    token = session['tokens']['access_token']

    if not token:
        print("User authentication failed!")
        return False

    spotify = spotipy.Spotify(auth=token)

    # Playlist info
    collection_data = read_collection_data("./App/collection_export.json")
    playlist_data = []

    # Create placeholders for statistics
    failed_export = []
    
    # Find and add tracks to the playlist
    for release in collection_data:
        artist = release['artist']
        title = release['title']
        result = spotify.search(q=f"artist:{artist} album:{title}", type="album")
        discogs_id = release['discogs_id']

        if result["albums"]["items"]:
            album = result["albums"]["items"][0]
            # log for development only
            # print(json.dumps(album, indent=4))

            # placeholder for album data
            album_data = {}
            
            #for display
            album_data["artist"] = album["artists"][0]["name"]
            album_data["title"] = album["name"]
            album_data["image"] = album["images"][2]["url"]
            album_data["url"] = album["external_urls"]["spotify"]

            # for later use
            album_data["id"] = album["id"]
            album_data["uri"] = album["uri"]
            album_data["discogs_id"] = discogs_id

            playlist_data.append(album_data)
            # log for development only
            print("Successfully transferred: " + album_data["title"] + " by " + album_data["artist"])

        else:
            failed_export.append({"artist": artist, "title": title})
            # log for development only
            print("Failed to add: " + artist + " - " + title)

    export_playlist_to_json(playlist_data)

    # info to be passed to UI later
    print(f"failed to find: {json.dumps(failed_export, indent=2)}")
    # log for debugging only
    print(
            "\n" + f"{len(playlist_data)} albums transferred."
        )
    print(json.dumps(playlist_data, indent=2))

    return playlist_data


def create_playlist(name):
    token = session['tokens']['access_token']

    if not token:
        print("User authentication failed!")
        return False

    spotify = spotipy.Spotify(auth=token)

    # Playlist info
    playlist_data = read_playlist_data("./App/playlist_albums.json")
    playlist_name = name
    playlist_description = "This is a playlist created from Discogs collection using Discofy"

    try:    
        playlist = spotify.user_playlist_create(
            spotify.current_user()["id"], name=playlist_name, public=True, description=playlist_description
        )

        # Create placeholders for statistics
        albums_total = []
        track_uris_total = []
        tracks_number = 0

        # Find and add tracks to the playlist
        for album in playlist_data:
                album_id = album["uri"]
                tracks = spotify.album_tracks(album_id)["items"]
                track_uris = [track["uri"] for track in tracks] #get album track uris
                spotify.playlist_add_items(playlist["id"], track_uris)

                # statistics
                albums_total.append(album_id)
                track_uris_total.append(track_uris)
                tracks_number = tracks_number + len(track_uris)

                # log for debugging only
                print(json.dumps(tracks, indent = 2))
        # info to be passed to UI later
        print(
            "\n" + f"{tracks_number} tracks from {len(albums_total)} albums added to playlist '{playlist_name}'."
        )

        playlist_url = playlist["external_urls"]["spotify"]
        print(f"playlist url: {playlist_url}")
        return playlist_url
    
    except Exception as e:
        print(f"Error creating playlist: {e}")
        return False
    

def export_playlist_to_json(playlist, filename="playlist_albums.json"):
    app_folder = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(app_folder, filename)

    with open(filepath, 'w') as json_file:
        json.dump(playlist, json_file, indent=2)

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
