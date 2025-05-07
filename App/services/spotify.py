import re

import spotipy
from rapidfuzz import fuzz


def search_spotify_albums(access_token, search_query, limit=1):
    """
    Search Spotify for albums using the given query string.
    Returns metadata for the top match if found, otherwise None.
    """
    if not access_token:
        print('Access token is missing.')
        return []

    spotify = spotipy.Spotify(auth=access_token)

    try:
        search_result = spotify.search(
            q=search_query, type='album', limit=limit)

        items = search_result["albums"]["items"]
        if items:
            # return first result
            album = items[0]
            return {
                "artist": album["artists"][0]["name"],
                "title": album["name"],
                "image": album["images"][0]["url"] if album["images"] else None,
                "url": album["external_urls"]["spotify"],
                "id": album["id"],
                "uri": album["uri"],
                "found": True,
            }

        else:
            return False

    except Exception as e:
        print(f"Spotify search failed: {e}")

    return None


def transfer_from_discogs(collection_items, access_token):
    """
    Attempts to find Spotify matches for a list of Discogs albums.
    Uses a two-pass search: first with artist + album, then album only.
    Applies fuzzy matching to verify the results.
    Returns a list of matched (or not matched) items with Spotify metadata.
    """
    if not access_token:
        print('Access token is missing.')
        return []

    export_items = []

    counter_item = 1
    for item in collection_items:
        discogs_artist = item['artist']
        discogs_album = item['title']
        discogs_id = item['discogs_id']

        print(f"[{counter_item}] SEARCHING for {discogs_artist} - {discogs_album}...")
        counter_item = counter_item + 1
        # Search by album name and filter by artist or by album name only
        search_queries = [
            f"{discogs_album} artist:{discogs_artist}",
            f"album:{discogs_album}",  # fallback
            discogs_album  # fallback 2
        ]

        # Default structure for items not found
        album_data = {
            "artist": None,
            "title": None,
            "image": None,
            "url": None,
            "id": None,
            "uri": None,
            "found": False,
        }
        counter = 1
        for search_query in search_queries:
            print(f"PASS {counter}: searching: {search_query}")
            counter = counter + 1
            search_result = search_spotify_albums(access_token, search_query)
            if search_result:
                found_artist = search_result.get('artist', '')
                found_album = search_result.get('title', '')
                match, match_score = is_match(
                    discogs_artist, discogs_album, found_artist, found_album
                )
                print(
                    f'found {found_artist} - {found_album}. Match score: {match_score}')
                if match:
                    print(
                        f'SUCCESS: {discogs_artist} - {discogs_album} matching with {found_artist} - {found_album}')
                    album_data = search_result
                    break  # Found good match, exit loop
            else:
                print('NO RESULTS')

        # Add corresponding discogs_id and append item data to the exported list
        album_data['discogs_id'] = discogs_id
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


def sanitize(text):
    text = text.lower()
    text = re.sub(r'\s*\(\d+\)', '', text)  # Remove bracketed numbers like (7)
    # Remove anything in (...) or [...]
    text = re.sub(r"[\(\[].*?[\)\]]", "", text)
    text = re.sub(r'[^a-z0-9\s]', '', text)  # Strip special characters
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    return text.strip()


def is_match(discogs_artist, discogs_album, spotify_artist, spotify_album, threshold=85):
    d_artist = sanitize(discogs_artist)
    d_album = sanitize(discogs_album)
    s_artist = sanitize(spotify_artist)
    s_album = sanitize(spotify_album)

    combined_discogs = f"{d_artist} {d_album}"
    combined_spotify = f"{s_artist} {s_album}"
    print(f"comparing: {combined_discogs} with {combined_spotify}...")

    # Base comparison
    base_ratio = fuzz.ratio(combined_discogs, combined_spotify)

    # Looser comparison (to catch e.g. different artist name or title formatting)
    token_ratio = fuzz.token_set_ratio(combined_discogs, combined_spotify)

    # Compare album titles (to catch cases where specified artists differ but album title matches almost exactly)
    title_ratio = fuzz.ratio(d_album, s_album)

    # Compare unsanitized titles in case some essential elements were removed
    original_title_ratio = fuzz.ratio(discogs_album, spotify_album)

    # Prioritize token ratio only if base is below a certain point
    if base_ratio >= threshold:
        print(f"using base ratio: {base_ratio}")
        return True, base_ratio
    elif token_ratio > 92 and base_ratio >= 70:
        print(f"using token ratio: token:{token_ratio}, base: {base_ratio}")
        return True, token_ratio
    elif title_ratio > 85 and token_ratio >= 70:
        print(
            f"using title ratio: title: {title_ratio}, token:{token_ratio}, base: {base_ratio}")
        return True, title_ratio
    elif original_title_ratio > 85 and token_ratio >= 70:
        print(
            f"using original title ratio: org_title: {original_title_ratio}, title: {title_ratio}, token:{token_ratio}, base: {base_ratio}")
        return True, original_title_ratio
    else:
        print(
            f"Not passed with scores: org_title: {original_title_ratio}, title: {title_ratio} token:{token_ratio}, base: {base_ratio}")
        return False, base_ratio
