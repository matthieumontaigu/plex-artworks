# plex-artworks

Tools and services to manage and update movie artworks (posters, backgrounds, logos) on a Plex server. It integrates with external sources like Apple TV and TMDB to fetch, select, and upload artworks, and can also localize metadata.

## Features
- Fetch and upload posters, backgrounds, and logos for movies
- Update and localize movie metadata (e.g., release dates)
- Detect missing artworks and process recently added items
- Run scheduled tasks or perform one-off updates from Apple TV links

---

## Installation

1) Clone the repository
```bash
git clone https://github.com/your-repo/plex-artworks.git
cd plex-artworks
```

2) Install dependencies
```bash
pip install -r requirements.txt
```

---

## Configuration

Both the scheduler service and the Apple TV → Plex updater use a JSON config file. The top-level shape matches what `services/main.py` expects:

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

Notes
- Schedules: type and params are passed to the internal scheduler (e.g., interval in seconds). Adjust to your needs.
- Only the `plex` section is required by the Apple TV → Plex updater tool.

---

## Run the scheduler service (services/main.py)

Starts the long-running tasks (recently added, missing artworks, revert), using the config above.

```bash
python services/main.py --config-path /path/to/config.json
```

What it does
- Instantiates Plex, TMDB, and Google clients
- Retrieves artworks (Apple TV, TMDB), selects the best match, uploads to Plex
- Updates metadata and runs on the schedule you configure

---

## One-off Apple TV → Plex updater (tools/plex_updater.py)

Upload poster/background/logo for a single Plex item by pointing to an Apple TV title page.

### CLI usage
```bash
python tools/plex_updater.py \
  --config-path /path/to/config.json \
  --plex-url "https://app.plex.tv/desktop#!/server/<server-id>/details?key=metadata%2F123456&..." \
  --apple-url "https://tv.apple.com/<locale>/movie/<slug>/<id>"
```

Behavior
- Extracts poster, background, and logo from the Apple TV page
- Uploads any that are found to the Plex item derived from the Plex URL
- Logging is controlled by your config (see `log` section)

URL tips
- The Plex URL must contain the encoded metadata key (e.g., `metadata%2F123456&…`). The tool extracts the numeric ID from there.

### Programmatic usage
```python
from utils.file_utils import load_json_file
from client.plex.manager import PlexManager
from tools.plex_updater import PlexUpdater

config = load_json_file("/path/to/config.json")
plex_manager = PlexManager(**config["plex"])  # expects keys: plex_url, plex_token, metadata_country, metadata_path

plex_url = "https://app.plex.tv/desktop#!/server/<server-id>/details?key=metadata%2F123456&X-Plex-Token=<token>"
apple_tv_url = "https://tv.apple.com/us/movie/inception/tt123456789"

updater = PlexUpdater(plex_manager)
# All three booleans default to True; set to False to skip an asset type
updater.update(plex_url, apple_tv_url, poster=True, background=True, logo=True)

# You can also upload only a known logo URL to a Plex item
updater.upload_logo_from_url(plex_url, "https://example.com/logo.png")
```

---

## Batch editing

There is also a small batch helper script for bulk operations:
```bash
python tools/batch.py --help
```

---

## Logging

Logs use the `log.path` and `log.level` from your config. Ensure the directory exists or is creatable by the process.

---

## Contributing

Issues and PRs are welcome.

---

## License

MIT License
