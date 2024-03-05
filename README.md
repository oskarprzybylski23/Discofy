<p align="center">
  <img src="./App/static/favicon.ico" alt="Discofy Logo" width="100"/>
</p>

<h1 align="center">Discofy (WIP)</h1>

<p align="center">
Discofy is an application that allows users to create Spotify playlists based on their Discogs collections. This tool retrieves album information from a Discogs collection and creates a Spotify playlist containing tracks from those albums.
  <br>
  <a href="https://github.com/oskarprzybylski23/Discogs-Spotify-Playlist-Creator"><strong>Explore the docs »</strong></a>
  <br>
  <br>
  <a href="#">View Demo</a>
  ·
  <a href="https://github.com/oskarprzybylski23/Discogs-Spotify-Playlist-Creator/issues">Report Bug</a>
  ·
  <a href="https://github.com/oskarprzybylski23/Discogs-Spotify-Playlist-Creator/issues">Request Feature</a>
</p>

---

## 🌟 Features
- **Spotify and Discogs Authentication:** Secure OAuth authentication ensures safe access to your Spotify and Discogs data.
- **Discogs Collection Retrieval:** Easily pull your entire Discogs collection into the app.
- **Automated Playlist Creation:** Convert your Discogs collections into Spotify playlists with just a few clicks.
- **Error Handling:** Intelligent error reporting for albums not found on Spotify, ensuring smooth playlist creation.

## 🛠 Installation

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

## 🚀 Usage
After setting up, visit http://localhost:5000 in your web browser to start creating your playlists.

## 💡 Contributing
Here's how you can contribute:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).
5. Open a pull request.

## 📝 License
Distributed under the MIT License. See `LICENSE` for more information.

Project Link: https://github.com/oskarprzybylski23/Discogs-Spotify-Playlist-Creator