# Discogs-Spotify-Playlist-Creator (WIP)

## Overview
The Discogs-Spotify Playlist Creator is a Python-based application that allows users to create Spotify playlists based on their Discogs collections. This tool authenticates users with Spotify, retrieves album information from a Discogs collection, and creates a Spotify playlist containing tracks from those albums.

## Features
- Authentication with Spotify using OAuth.
- Retrieval of user's Discogs collection data.
- Automated creation of Spotify playlists based on the Discogs collection.
- Error handling and reporting for albums not found on Spotify.

## Installation

1. Clone the repository:

```bash 
git clone https://github.com/oskarprzybylski23/Discogs-Spotify-Playlist-Creator.git 
```

2. Navigate to the project directory:

```bash 
cd Discogs-Spotify-Playlist-Creator
```

3. Install the required Python packages:

```bash 
pip install -r requirements.txt
```
4. Create `.env` and fill in your Spotify and Discogs credentials:

```text
SPOTIPY_CLIENT_ID= `your_spotify_client_id`
SPOTIPY_CLIENT_SECRET= `your_spotify_client_secret`
SPOTIPY_CLIENT_URI= `your_spotify_redirect_uri`
discogs_consumer_key=`your_discogs_consumer_key`
discogs_consumer_secret=`your_discogs_consumer_secret`
```

5. start virtualenv

```bash
source venv/bin/activate 
```

6. start flask server

```bash
python App/App.py 
```

## Usage

## Contributing
Contributions to the Discogs-Spotify Playlist Creator are welcome. To contribute:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).
5. Open a pull request.

## License
Distributed under the MIT License. See `LICENSE` for more information.

Project Link: