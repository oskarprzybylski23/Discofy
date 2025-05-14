# Discofy - create Spotify playlists from your Discogs record collection

Discofy is a web application that lets users create Spotify playlists from their personal Discogs libraries. This repository contains the Flask backend, which handles authentication, collection retrieval, and playlist creation via the Spotify and Discogs APIs.

> **Frontend:** The React frontend is in a separate repository: [Discofy Frontend](https://github.com/oskarprzybylski23/discofy-frontend)

---

## 🏗️ Architecture

- **Flask** backend (this repo)
- **Celery** for background task processing
- **Redis** for session management and Celery
- **React** frontend ([repo link](https://github.com/oskarprzybylski23/discofy-frontend))
- **Spotify & Discogs APIs** for music and collection data

**Folder structure:**

```
.
├── app/
│   ├── auth/       # Authentication routes
│   ├── main/       # Main entry routes
│   ├── spotify/    # Spotify integration routes
│   ├── discogs/    # Discogs integration routes
│   ├── services/   # Business logic and Celery tasks
│   └── extensions.py   # Flask extensions
├── config.py # Flask configuration and environment parameters
├── docker-compose.dev.yml
├── docker-compose.prod.yml
├── docker-compose.yml
├── Dockerfile
└── wsgi.py
```

---

## ⚙️ Prerequisites

- Python 3.8+
- [Redis](https://redis.io/) running locally or accessible remotely
- Spotify Developer credentials
- Discogs Developer credentials
- Docker & Docker Compose

---

## 🚀 Local Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/oskarprzybylski23/Discofy.git
   cd Discofy
   ```
2. **Create and fill your `.env` file:**

   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Build and run the containers (API, Celery worker, Redis):**

   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
   ```

   This will start:

   - Flask API (on port 5000)
   - Celery worker (for background jobs)
   - Redis (for sessions and Celery broker/backend)

4. **Access the API:**

   default on: http://localhost:5000

---

## ☁️ Production/Deployment Notes

### In production, you must run **two services** with appropiate start commands:

- **Flask API (web server)**
  ```bash
  gunicorn --timeout 300 --workers 5 wsgi:app
  ```
  Alter timeout and worker parameters based on infrastructure
- **Celery worker (background worker)**
  ```bash
  celery -A app.services.celery_tasks.celery worker --loglevel=info --concurrency=1
  ```
  Alter worker parameter based on infrastructure and limit concurrency to avoid out of memory errors
- **Both must have access to the same Redis instance (preferably managed Redis service).**

---

## 📚 API Endpoints

### Main

- `GET /` — Health check, returns 'Discofy API'

### Auth

- `GET /success` — OAuth success page (used for popup flow)

### Spotify

- `GET /spotify/get_auth_url` — Get Spotify OAuth URL
- `GET /spotify/callback` — Spotify OAuth callback
- `GET /spotify/check_authorization` — Check Spotify auth status
- `POST /spotify/transfer_collection` — Start transfer of Discogs collection to Spotify (background task).
  (body: `{ collection: [...] }`)
  - Use the returned `task_id` and `progress_key` to poll the status endpoint below.
- `GET /spotify/transfer_collection_status?task_id=...&progress_key=...` — Check progress and result of a transfer task
- `POST /spotify/create_playlist` — Create Spotify playlist (body: `{ playlist: [...], playlist_name: "..." }`)
- `POST /spotify/logout` — Disconnect from Spotify (removes session data)

### Discogs

- `POST /discogs/get_auth_url` — Get Discogs OAuth URL
- `GET /discogs/callback` — Discogs OAuth callback
- `GET /discogs/check_authorization` — Check Discogs auth status
- `GET /discogs/get_library` — Get user's Discogs library
- `GET /discogs/get_folder_contents?folder=<id>` — Get contents of a Discogs folder
- `POST /discogs/logout` — Disconnect from Discogs (removes session data)

---

## 🤝 Contributing

Contributions are welcome. Feel free to suggest new features or report bugs in [Issues](https://github.com/oskarprzybylski23/Discofy/issues). To contribute a fix or feature:

1. Fork the repository
2. Create a new branch (`git checkout -b feature/YourFeature`)
3. Commit your changes (`git commit -m 'Add YourFeature'`)
4. Push to your branch (`git push origin feature/YourFeature`)
5. Open a pull request

---

## 📝 License

Distributed under the MIT License. See `LICENSE` for details.
