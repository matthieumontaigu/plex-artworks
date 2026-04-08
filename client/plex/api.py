import logging

import requests
from requests import Response

logger = logging.getLogger(__name__)

IMAGES_MAPPING = {
    "poster": "posters",
    "background": "arts",
    "logo": "clearLogos",
}


class PlexAPIRequester:
    def __init__(self, api_url: str, plex_token: str) -> None:
        self.api_url = api_url.rstrip("/")
        self.headers = {
            "X-Plex-Token": plex_token,
            "X-Plex-Product": "Plex poster manager",
            "X-Plex-Pms-Api-Version": "1.0",
        }

    def get_all_movies(self) -> Response | None:
        """Get all movies."""
        endpoint = f"library/sections/6/all"

        response = self.get(endpoint, {})
        return response

    def get_recently_added_movies(self) -> Response | None:
        """Get recently added movies."""
        endpoint = f"library/sections/6/recentlyAdded"
        params = {"type": 1}

        response = self.get(endpoint, params)
        return response

    def get_metadata(self, movie_id: int) -> Response | None:
        """Get metadata for a specific movie."""
        endpoint = f"library/metadata/{movie_id}"

        response = self.get(endpoint, {})
        return response

    @staticmethod
    def get_image_type(image_type: str) -> str:
        if image_type not in IMAGES_MAPPING:
            raise ValueError(
                f"Invalid image type: {image_type}, available types: {list(IMAGES_MAPPING.keys())}"
            )
        return IMAGES_MAPPING[image_type]

    def get_images(self, id: int, image_type: str) -> Response | None:
        """Get images of a specific type for a movie."""
        image_type = self.get_image_type(image_type)
        endpoint = f"library/metadata/{id}/{image_type}"

        response = self.get(endpoint, {})
        return response

    def upload_image(self, id: int, image_type: str, image_url: str) -> bool:
        image_type = self.get_image_type(image_type)
        endpoint = f"library/metadata/{id}/{image_type}"
        params = {"url": image_url}

        response = self.post(endpoint, params)
        if response is None:
            return False
        return response.status_code == 200

    def upload_poster(self, id: int, poster_url: str) -> bool:
        return self.upload_image(id, "poster", poster_url)

    def upload_background(self, id: int, background_url: str) -> bool:
        return self.upload_image(id, "background", background_url)

    def upload_logo(self, id: int, logo_url: str) -> bool:
        return self.upload_image(id, "logo", logo_url)

    def upload_image_file(self, id: int, image_type: str, image_file_path: str) -> bool:
        image_type = self.get_image_type(image_type)
        endpoint = f"library/metadata/{id}/{image_type}"
        with open(image_file_path, "rb") as f:
            image_data = f.read()

        response = self.post(endpoint, data=image_data)
        if response is None:
            return False
        return response.status_code == 200

    def update_release_date(self, id: int, release_date: str) -> bool:
        """Update the release date for a movie."""
        endpoint = f"library/metadata/{id}"
        params = {
            "originallyAvailableAt.value": release_date,
            "originallyAvailableAt.locked": 1,
        }

        response = self.put(endpoint, params)
        if response is None:
            return False
        return response.status_code == 200

    def get(self, endpoint: str, params: dict) -> Response | None:
        url = f"{self.api_url}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            logger.error(f"{e}")
            return None

    def post(
        self, endpoint: str, params: dict | None = None, **kwargs
    ) -> Response | None:
        url = f"{self.api_url}/{endpoint}"
        try:
            response = requests.post(url, headers=self.headers, params=params, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            logger.error(f"{e}")
            return None

    def put(self, endpoint: str, params: dict) -> Response | None:
        url = f"{self.api_url}/{endpoint}"
        try:
            response = requests.put(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            logger.error(f"{e}")
            return None
