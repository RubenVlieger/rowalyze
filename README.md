# RowSplit 🚣

A simple web tool to analyze your Strava rowing sessions. Paste a Strava activity URL, and RowSplit finds your fastest intervals with detailed 500m split breakdowns — speed, cadence, heart rate, the works.

Built for me and my rowing friends at Njord to quickly compare our interval pieces without manually digging through Strava data.

## What it does

- **Finds fastest intervals** — by time (e.g. 4min50s) or distance (e.g. 2000m)
- **500m sub-splits** — each interval broken into 500m chunks with per-segment stats
- **Graphs** — speed, cadence, and heart rate plotted per interval
- **Groups** — save sessions into playlists (like YouTube/Spotify) for easy comparison
- **Share** — public share links so your coach or crewmates can see your results
- **🦈 Shark Mode** — analyze a friend's activity using a bookmarklet, no API access needed

## Quick Start

```bash
# Clone
git clone https://github.com/yourusername/rowsplit.git
cd rowsplit

# Set up your Strava API credentials
cp .env.example .env
# Edit .env with your Strava Client ID & Secret
# Get these from: https://www.strava.com/settings/api

# Run with Docker
docker compose up -d --build

# → Open http://localhost:8080
```

## Strava API Setup

1. Go to [strava.com/settings/api](https://www.strava.com/settings/api)
2. Create an application (use any name/website)
3. Set **Authorization Callback Domain** to `localhost` (or your server domain)
4. Copy the Client ID and Client Secret into your `.env` file

## 🦈 Shark Mode

Want to analyze a friend's activity that you can see on Strava but can't access via the API?

1. Log into Strava in your browser
2. Drag the **"🦈 RowSplit Shark"** bookmarklet from the app's homepage to your bookmarks bar
3. Navigate to your friend's activity on Strava
4. Click the bookmarklet
5. Done — it grabs the stream data and sends it to RowSplit for analysis

*The bookmarklet runs in the context of strava.com (so no CORS issues) and uses your logged-in session to fetch the same data you'd see in DevTools.*

## Tech Stack

- **Backend:** Python / Flask / Gunicorn
- **Frontend:** Vanilla HTML/CSS/JS, Chart.js
- **Database:** SQLite (persistent Docker volume)
- **Deploy:** Docker

## Project Structure

```
├── app.py              # Flask app (routes, auth, analysis)
├── analyze.py          # Interval analysis engine
├── strava_client.py    # Strava OAuth + API client
├── db.py               # SQLite database layer
├── main.py             # CLI tool (still works!)
├── templates/          # Jinja2 HTML templates
├── static/             # CSS + JS
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Privacy

RowSplit stores a hashed (SHA-256) fragment of your Strava athlete ID for analytics — it cannot be reversed to identify you. No passwords or full tokens are stored. See [PRIVACY.md](PRIVACY.md) for details.

## License

This project uses a custom non-commercial license. See [LICENSE](LICENSE) for details.
You may NOT use this code for commercial purposes without written permission from the author.

---

*Made with ☕ for the rowing community*
