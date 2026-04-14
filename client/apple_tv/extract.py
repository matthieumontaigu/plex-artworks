import re
import time
from urllib.parse import urlparse, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from client.apple_tv.attributes import Attributes, get_umc_id, parse_attributes
from utils.parsing import parse_html
from utils.requests_utils import get_request


def get_apple_tv_artworks(
    url: str,
) -> tuple[Attributes | None, str | None, str | None, str | None]:
    response = get_request(url)
    if response is None:
        return None, None, None, None

    parsed_page = parse_html(response.text)

    attributes = parse_attributes(parsed_page)
    if attributes is None:
        return None, None, None, None

    time.sleep(0.5)  # Wait before next request needed for poster extraction
    poster_url = get_poster_url(parsed_page, url)
    background_url = get_background_url(parsed_page)
    logo_url = get_logo_url(parsed_page)

    return attributes, poster_url, background_url, logo_url


def get_cover_art_url(attributes: Attributes) -> str | None:
    if "image" not in attributes:
        return None

    image_url = attributes["image"]
    return get_enlarged_image_url(image_url, "2000x0w.jpg")


def get_poster_url(page: BeautifulSoup, url: str, max_persons: int = 3) -> str | None:
    content_umc_id = get_umc_id(url)
    if not content_umc_id:
        return None

    if "/movie/" in url:
        entity = "movie"
    elif "/show/" in url:
        entity = "show"
    else:
        return None

    pattern = re.compile(r"^person-lockup")
    crew = page.find_all("a", class_=pattern, href=True)
    if not crew:
        return None

    crew_to_test = crew[:max_persons]  # Limit to first max_persons persons only
    for person in crew_to_test:
        person_url = person["href"]
        poster_url = get_poster_from_person(person_url, content_umc_id, entity)
        if poster_url:
            return poster_url

        time.sleep(1.0)  # Be nice to Apple servers


def get_poster_from_person(
    person_url: str, content_umc_id: str, entity: str
) -> str | None:
    person_collection_url = person_url_to_collection(person_url, entity)
    if not person_collection_url:
        return None

    response = get_request(person_collection_url)
    if response is None:
        return None

    parsed_page = parse_html(response.text)
    matching_content = [
        a for a in parsed_page.find_all("a", href=True) if content_umc_id in a["href"]
    ]
    if not matching_content:
        return None

    picture = matching_content[0].picture
    if not picture:
        return None

    return get_image_url(picture, "2000x0w.jpg")


def get_logo_url(page: BeautifulSoup) -> str | None:
    """Logo is first picture with class starting with "picture" """
    pattern = re.compile(r"^picture")
    pictures = page.find_all("picture", class_=pattern)

    if not pictures:
        return None

    return get_image_url(pictures[0], "2400x900.png")


def get_background_url(page: BeautifulSoup) -> str | None:
    """Background is first picture with class starting with "svelte" """
    pattern = re.compile(r"^svelte")
    pictures = page.find_all("picture", class_=pattern)

    if not pictures:
        return None

    return get_image_url(pictures[0], "4320x3240.jpg")


def get_image_url(picture: BeautifulSoup, size: str) -> str | None:
    size_parts = size.split(".")
    if len(size_parts) != 2:
        raise ValueError("Size must be in the format 'WIDTHxHEIGHT.extension'")

    image_url = get_matching_source_url(picture, size_parts[1])

    if not image_url:
        return None

    return get_enlarged_image_url(image_url, size)


def get_matching_source_url(picture: BeautifulSoup, extension: str) -> str | None:
    expected_extension = f".{extension} "
    for source in picture.find_all("source"):
        srcset = source.get("srcset")
        if not srcset or expected_extension not in srcset:
            continue

        return srcset.split(", ")[0].split(" ")[0]

    return None


def get_enlarged_image_url(url: str, size: str) -> str:
    """Get the largest available image by replacing with input size '2000x0w.jpg'"""

    parts = urlsplit(url)

    # Split path at the last '/'
    path_parts = parts.path.rsplit("/", 1)
    if len(path_parts) == 2:
        path_parts[-1] = size
        new_path = "/".join(path_parts)
    else:
        new_path = size

    # Rebuild URL with new path
    return urlunsplit(
        (parts.scheme, parts.netloc, new_path, parts.query, parts.fragment)
    )


_ENTITY_COLLECTION_PATH = {
    "movie": "movies/uts.col.movies_of_person",
    "show": "shows/uts.col.shows_of_person_no_kidsfamily",
}


def person_url_to_collection(url: str, entity: str) -> str | None:
    """
    Extract the `umc.*` identifier from an Apple TV person URL and
    return the corresponding collection URL for the given entity type,
    keeping the same scheme, domain, and country code.

    Example (movie)
    -------
    https://tv.apple.com/us/person/josh-o-connor/umc.cpc.2kgky0blff2lspn7skq8vff13
    ->
    https://tv.apple.com/us/collection/movies/uts.col.movies_of_person?ctx_person=umc.cpc.2kgky0blff2lspn7skq8vff13

    Example (show)
    -------
    https://tv.apple.com/us/person/josh-o-connor/umc.cpc.2kgky0blff2lspn7skq8vff13
    ->
    https://tv.apple.com/us/collection/shows/uts.col.shows_of_person_no_kidsfamily?ctx_person=umc.cpc.2kgky0blff2lspn7skq8vff13
    """
    collection_path = _ENTITY_COLLECTION_PATH.get(entity)
    if not collection_path:
        return None

    umc_id = get_umc_id(url)
    if not umc_id:
        return None

    # Keep scheme + domain + country prefix (e.g. /us)
    parsed = urlparse(url)
    path_parts = parsed.path.strip("/").split("/")
    if not path_parts:
        return None

    country = path_parts[0]
    return f"{parsed.scheme}://{parsed.netloc}/{country}/collection/{collection_path}?ctx_person={umc_id}"
