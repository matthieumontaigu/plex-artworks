# plex-artworks

Personal Python utilities for keeping movie artwork and selected metadata in sync on a Plex server.

This repository is focused on a specific Plex workflow: use metadata from Apple TV and TMDB pages and APIs where available, choose the best artwork match, upload assets to Plex, and optionally update localized release dates.

## What is in this repository

- A scheduled service that processes recently added movies, movies with missing artwork, and artwork reverts
- A CLI tool for updating a single Plex item from an Apple TV page
- Supporting clients for Plex, Apple TV, TMDB, Google Custom Search, caching, and scheduling

## Repository layout

- `services/main.py`: entry point for the long-running scheduler service
- `tools/plex_updater.py`: one-off CLI for updating a single Plex item
- `client/`: integration code for Plex and supported metadata providers
- `services/`: artwork retrieval, selection, upload, localization, and scheduled tasks
- `storage/`: cache helpers for scheduled runs

## Configuration

The scheduler and the CLI tool both read a JSON config file.

Example:

```json
{
  "plex": {
    "plex_url": "http://your-plex-server:32400",
    "plex_token": "your-plex-token",
    "metadata_country": "us",
    "metadata_path": "/config/metadata"
  },
  "tmdb": {
    "api_token": "your-tmdb-api-token"
  },
  "google": {
    "api_key": "your-google-api-key",
    "custom_search_id": "your-custom-search-id"
  },
  "artworks": {
    "retriever": {
      "countries": ["us", "fr"]
    },
    "selector": {
      "match_movie_title": true,
      "match_logo_poster": true,
      "target_source": "apple_tv"
    },
    "reverter": {
      "artworks_types": ["poster", "background", "logo"]
    },
    "movies_sleep_interval": 1.0
  },
  "missing_artworks_task": {
    "search_quota": 100,
    "recent_threshold_days": 7
  },
  "schedules": {
    "recently_added": { "type": "interval", "params": [3600] },
    "missing_artworks": { "type": "interval", "params": [86400] },
    "artworks_reverter": { "type": "interval", "params": [43200] }
  },
  "cache": {
    "cache_path": "./cache",
    "retention_days": 7
  },
  "log": {
    "path": "./logs/plex-artworks.log",
    "level": "INFO"
  }
}
```

Notes:

- `plex`, `tmdb`, `google`, `artworks`, `missing_artworks_task`, `schedules`, `cache`, and `log` are all expected by `services/main.py`
- `tools/plex_updater.py` only needs the `plex` section from the same config file
- Keep real tokens and server URLs out of version control

## Running the scheduler

The scheduler service wires together the Plex, TMDB, Apple TV, and Google clients, then runs three configured tasks:

- recently added movies
- movies with missing artwork
- artwork reverter

Run it with:

```bash
python services/main.py --config-path /path/to/config.json
```

## Updating one Plex item from Apple TV

`tools/plex_updater.py` provides a small CLI with two subcommands:

- `apple`: retrieve artwork associated with an Apple TV title page for manual Plex item updates
- `logo`: upload a logo directly from an image URL

Examples:

```bash
python tools/plex_updater.py apple \
  --config-path /path/to/config.json \
  --plex-url "https://app.plex.tv/desktop#!/server/<server-id>/details?key=metadata%2F123456&..." \
  --apple-url "https://tv.apple.com/<locale>/movie/<slug>/<id>"
```

```bash
python tools/plex_updater.py logo \
  --config-path /path/to/config.json \
  --plex-url "https://app.plex.tv/desktop#!/server/<server-id>/details?key=metadata%2F123456&..." \
  --logo-url "https://example.com/logo.png"
```

The Plex URL must contain the encoded metadata key so the script can extract the numeric Plex item id.

## Development notes

- This repository does not currently ship as a packaged Python project
- Install the Python dependencies used by the codebase in your preferred environment before running the scripts
- Tests live alongside the implementation under `client/`, `services/`, and `storage/`

## License

MIT
