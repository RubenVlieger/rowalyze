# Privacy Policy

**RowSplit** is a small open-source tool for analyzing Strava rowing data. Here's exactly what data we handle and how.

## What we collect

| Data | How it's stored | Why |
|------|----------------|-----|
| **Strava athlete ID** | Hashed with SHA-256, only first 16 characters stored | Count unique users on the homepage |
| **Analysis sessions** | Activity name, date, interval parameters, and analysis results stored in SQLite | So you can revisit your results and organize them into groups |
| **Strava access tokens** | Stored temporarily in your encrypted browser session cookie | To make API calls on your behalf during your visit |

## What we do NOT collect

- ❌ Your password (we use Strava OAuth — we never see your password)
- ❌ Your full Strava profile or personal information
- ❌ Your location or GPS data (stream data is processed in memory and not stored)
- ❌ Any data from other users' activities
- ❌ Analytics cookies or tracking pixels
- ❌ Your email address

## How Strava OAuth works

When you click "Connect with Strava", you're redirected to Strava's website where you log in and grant permission. Strava then sends us a temporary access token. We use this token to fetch your activity data. The token expires after 6 hours.

We never see your Strava password. You can revoke access at any time from [strava.com/settings/apps](https://www.strava.com/settings/apps).

## 🦈 Shark Mode

Shark Mode uses a bookmarklet that runs in your browser on the Strava website. It fetches stream data using your own logged-in Strava session (the same data you'd see in your browser's DevTools). This data is sent to the RowSplit server for analysis. No credentials are transmitted — only the stream data arrays (time, speed, cadence, distance).

## Data storage

All data is stored in a local SQLite database on the server. There is no cloud sync, no third-party analytics, and no data sharing. If the server is wiped, all data is gone.

## Shared links

When you share a session link, anyone with that link can view the analysis results. No login required. The link contains a random session ID that is not guessable.

## Your rights

Since this is a small self-hosted tool, you can:
- Delete your groups and sessions at any time from the UI
- Disconnect from Strava to clear your session
- Ask the server administrator to delete your data

## Contact

Questions? Email [ruben.vlieger@ru.nl](mailto:ruben.vlieger@ru.nl)
