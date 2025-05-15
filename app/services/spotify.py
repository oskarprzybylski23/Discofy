import os
import re
import logging
import json

import redis
import spotipy
from rapidfuzz import fuzz
from flask import current_app

logger = logging.getLogger(__name__)

# Create Celery specific client for functions handled by Celery in background
REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379')
celery_redis_client = redis.Redis.from_url(REDIS_URL)


def search_spotify_albums(access_token, search_query, limit=1):
    """
    Search Spotify for albums using the given query string.
    Returns metadata for the top match if found, otherwise None.
    """
    if not access_token:
        logger.warning("Access token is missing.")
        return []

    spotify = spotipy.Spotify(auth=access_token)

    try:
        logger.debug(
            "Searching Spotify for query: '%s', with limit: %d", search_query, limit)
        search_result = spotify.search(
            q=search_query, type='album', limit=limit)

        items = search_result.get('albums', []).get('items')

        if items:
            logger.debug("Search returned %d items", len(items))
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
            logger.debug(
                "Search returned no items.")
            return False

    except Exception as e:
        logger.error(f"Spotify search failed: {e}")

    return None


def transfer_from_discogs(collection_items, access_token, progress_key=None):
    """
    Attempts to find Spotify matches for a Discogs item.
    Uses a two-pass search: first with artist + album, then album only.
    Applies fuzzy matching to verify the results.
    Returns a  matched (or not matched) items with Spotify metadata.
    """
    if not access_token:
        logger.warning("Access token is missing.")
        return []

    export_items = []
    total = len(collection_items)

    for idx, item in enumerate(collection_items):
        discogs_artist = item['artists'][0]
        discogs_album = item['title']
        discogs_id = item['discogs_id']

        logger.info(
            "[%d out of %d] - Handling collection item: '%s - %s'",
            idx + 1, total, discogs_artist, discogs_album
        )

        search_queries = [
            f"{discogs_album} artist:{discogs_artist}",
            f"album:{discogs_album}",
            discogs_album
        ]

        album_data = {
            "artist": None,
            "title": None,
            "image": None,
            "url": None,
            "id": None,
            "uri": None,
            "found": False,
        }

        for query_idx, search_query in enumerate(search_queries, start=1):
            logger.debug("[Search pass %d]", query_idx)
            search_result = search_spotify_albums(access_token, search_query)
            if search_result:
                found_artist = search_result.get('artist', '')
                found_album = search_result.get('title', '')
                logger.debug("Search returned: '%s - %s'",
                             found_artist, found_album)
                match, score = is_match(
                    discogs_artist, discogs_album, found_artist, found_album)
                if match:
                    logger.info("Matched Discogs item %s - %s with Spotify result %s - %s. Match score: %d",
                                discogs_artist, discogs_album, found_artist, found_album, score)
                    album_data = search_result
                    album_data['found'] = True
                    break

        if not album_data['found']:
            logger.info("No match found for '%s - %s' (discogs_id: %s)",
                        discogs_artist, discogs_album, discogs_id)

        album_data['discogs_id'] = discogs_id
        export_items.append(album_data)

        # Celery task progress update
        if progress_key:
            progress = {'current': idx + 1, 'total': total}
            celery_redis_client.set(progress_key, json.dumps(progress))

    # Final summary
    matched_count = sum(1 for item in export_items if item.get('found'))
    logger.info("Finished processing %d items. Matched: %d, Unmatched: %d.",
                total, matched_count, total - matched_count)

    # Final mark Celery task as finished
    if progress_key:
        celery_redis_client.set(progress_key, json.dumps({
            'current': total,
            'total': total,
            'finished': True
        }))

    return export_items


def create_playlist(playlist_items, name, access_token):
    if not access_token:
        current_app.logger.error("Access token is missing.")
        return

    PLAYLIST_DESCRIPTION = "This is a playlist created from Discogs collection using Discofy"
    spotify = spotipy.Spotify(auth=access_token)
    user_id = spotify.current_user()["id"]

    try:
        # Create an empty playlist
        current_app.logger.debug(
            "Creating playlist with name: '%s' and description: '%s' for user id: %s", name, PLAYLIST_DESCRIPTION, user_id)
        playlist = spotify.user_playlist_create(
            user_id, name=name, public=True, description=PLAYLIST_DESCRIPTION
        )

        # Extract and list track URIs
        playlist_tracks = []
        for album in playlist_items:
            album_uri = album["uri"]
            tracks = spotify.album_tracks(album_uri)["items"]
            album_track_uris = [track["uri"] for track in tracks]
            playlist_tracks.extend(album_track_uris)

        # Add tracks to the playlist in batches (max 100 tracks supported in one request)
        current_app.logger.debug(
            "Adding %d tracks to playlist '%s", len(playlist_tracks), name)
        batch_counter = 1
        for i in range(0, len(playlist_tracks), 100):
            min_track = i + 1
            max_track = i + 100 if i + \
                100 < len(playlist_tracks) else len(playlist_tracks)
            current_app.logger.debug(
                "Batch %d: adding tracks index %d to %d", batch_counter, min_track, max_track)
            batch = playlist_tracks[i:i+100]
            spotify.playlist_add_items(playlist["id"], batch)
            batch_counter = batch_counter + 1

        playlist_url = playlist["external_urls"]["spotify"]
        current_app.logger.info(
            "Successfully created playlist: '%s', with %d tracks in %d albums with url: '%s'", name, len(playlist_tracks), len(playlist_items), playlist_url)
        return playlist_url

    except Exception as e:
        current_app.logger.error(f"Error creating playlist: {e}")
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
    logger.debug(
        "Comparing sanitized strings: %s with %s", combined_discogs, combined_spotify)

    # Base comparison
    base_ratio = fuzz.ratio(combined_discogs, combined_spotify)
    logger.debug("String comparison ratio: %s", base_ratio)

    # Looser comparison (to catch e.g. different artist name or title formatting)
    token_ratio = fuzz.token_set_ratio(combined_discogs, combined_spotify)
    logger.debug(
        "Tokenised string comparison ratio: %s", token_ratio)

    # Compare album titles (to catch cases where specified artists differ but album title matches almost exactly)
    title_ratio = fuzz.ratio(d_album, s_album)
    logger.debug(
        "Album title only comparison ratio: %s", title_ratio)

    # Compare unsanitized titles in case some essential elements were removed
    original_title_ratio = fuzz.ratio(discogs_album, spotify_album)
    logger.debug(
        "Unsantised album title only comparison ratio: %s", title_ratio)

    # Prioritize type of ratio based on criteria
    if base_ratio >= threshold:
        logger.debug(
            "Found matching using string comparison ratio")
        return True, base_ratio
    elif token_ratio > 92 and base_ratio >= 70:
        logger.debug(
            "Found matching using tokenised string comparison ratio")
        return True, token_ratio
    elif title_ratio > 85 and token_ratio >= 70:
        logger.debug(
            "Found matching using title only string comparison ratio")
        return True, title_ratio
    elif original_title_ratio > 85 and token_ratio >= 70:
        logger.debug(
            "Found matching using unsanitised title string comparison ratio")
        return True, original_title_ratio
    else:
        logger.debug(
            "No comparison ratio returned a good match for '%s - %s'", discogs_album, discogs_artist)
        return False, base_ratio
