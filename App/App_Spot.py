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

def transfer_from_discogs():
    token = session['tokens']['access_token']

    if not token:
        print("User authentication failed!")
        return False

    spotify = spotipy.Spotify(auth=token)

    # Playlist info
    collection_data = read_collection_data("./App/collection_export.json")
    export_data = []
    # Find and add tracks to the playlist
    for release in collection_data:
        artist = release['artist']
        title = release['title']
        result = spotify.search(q=f"artist:{artist} album:{title}", type="album")
        discogs_id = release['discogs_id']
        
        if result["albums"]["items"]:
            # log for development only
            # print(json.dumps(album, indent=4))
            album = result["albums"]["items"][0]    
            album_data = {
            "artist": album["artists"][0]["name"],
            "title": album["name"],
            "image": album["images"][0]["url"],  # Make sure to check the correct index for the desired image size
            "url": album["external_urls"]["spotify"],
            "id": album["id"],
            "uri": album["uri"],
            "discogs_id": discogs_id,
            "found": True,
            }

            export_data.append(album_data)
            # log for development only
            print("Successfully transferred: " + album_data["title"] + " by " + album_data["artist"])

        else:

            album_data = {
            "artist": artist,
            "title": title,
            "discogs_id": discogs_id,
            "found": False
            }

            export_data.append(album_data)
            # log for development only
            print("Failed to add: " + artist + " - " + title)

    save_export_data_to_json(export_data)

    # log for debugging only
    print(json.dumps(export_data, indent=2))

    return export_data


def create_playlist(name):
    token = session['tokens']['access_token']

    if not token:
        print("User authentication failed!")
        return False

    spotify = spotipy.Spotify(auth=token)

    # Playlist info
    playlist_data = read_playlist_data("./App/export_data.json")
    playlist_name = name
    playlist_description = "This is a playlist created from Discogs collection using Discofy"

    try:    
        playlist = spotify.user_playlist_create(
            spotify.current_user()["id"], name=playlist_name, public=True, description=playlist_description
        )

        # Create placeholder for statistics
        tracks_number = 0

        # Find and add tracks to the playlist
        for album in playlist_data:
                if album["found"]:
                    album_id = album["uri"]
                    tracks = spotify.album_tracks(album_id)["items"]
                    track_uris = [track["uri"] for track in tracks] #get album track uris
                    spotify.playlist_add_items(playlist["id"], track_uris)

                    # statistics
                    tracks_number = tracks_number + len(tracks)

                # log for debugging only
                # print(json.dumps(tracks, indent = 2))

        playlist_url = playlist["external_urls"]["spotify"]
        create_report(playlist_data, tracks_number, playlist_name, playlist_url)

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

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Format: Year-Month-Day Hour:Minute:Second
    app_name = "Discofy"
    github_link = "https://github.com/yourusername/discofy"  # Replace with your actual GitHub repo URL

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
            f.write(f"{len(failed_items)} albums failed to export or could not be found:\n")
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
        
