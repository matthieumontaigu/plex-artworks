from __future__ import annotations

import re
from typing import TYPE_CHECKING

from client.apple_tv.attributes import Attributes, get_attributes
from client.google.parser import parse_item_from_apple_tv_attributes
from client.google.utils import extract_path, norm_text, similarity

if TYPE_CHECKING:
    from client.google.parser import ItemView
    from models.target import Target

STRONG_SCORE = 4.0  # 2.0 for title match, 1.0 for director, 1.0 for year
REQUIRED_SCORE = 1.9  # at least a title match at 95% or matching director and year
VALIDATION_SCORE = 2.5  # strong match on at least two of title/director/year

DISALLOWED_RE = re.compile(
    "|".join(
        [
            r"/search\?",
            r"^/api\b",
            r"^/uts/",
            r"ctx_shelf=edt\.shelf\.PersonShelf1",
            r"^/includes/commerce/",
            r"/sporting-event/",
            r"/collection/(trailers|related|bonus-content|clubs|spotlight|other-games)/",
        ]
    )
)

CANONICAL_RE = re.compile(r"^/([a-z]{2,3})/(show|movie)/(.+/)?umc\.cm[cp]\.[\w.]+/?$")


class Scorer:
    """
    Computes a score for a Google CSE item projected to ItemView against a TargetSpec.
    """

    def __init__(
        self,
        *,
        title_threshold: float = 0.75,
    ) -> None:
        self.title_threshold = title_threshold

    def is_candidate_url(self, url: str) -> bool:
        if not (url and url.startswith("https://tv.apple.com/")):
            return False
        return not DISALLOWED_RE.search(extract_path(url))

    def compute(self, item: ItemView, target: Target) -> float | None:
        path = extract_path(item.url)
        if not CANONICAL_RE.match(path):
            return None

        if not f"/{target.entity}/" in path:
            return None

        if not f"/{target.country}/" in path:
            return None

        title_score = get_title_score(target.title, item.title, self.title_threshold)
        director_score = get_director_score(target.directors, item.director)
        year_score = get_year_score(target.year, item.release_year)

        if (
            target.country == "us"
            and item.lang == "es"
            and director_score == 1.0
            and year_score == 1.0
        ):
            attributes = get_attributes(item.url)
            return self.score_attributes(item.url, attributes, target)

        if title_score < 0.0 or director_score < 0.0 or year_score < 0.0:
            return None

        return title_score + director_score + year_score

    def score_attributes(
        self,
        url: str,
        attributes: Attributes | None,
        target: Target,
    ) -> float | None:
        if not attributes:
            return None

        item = parse_item_from_apple_tv_attributes(url, attributes)
        return self.compute(item, target)


def get_title_score(target_title: str, title: str | None, threshold: float) -> float:
    if not title:
        return 0.0

    similarity_score = similarity(target_title, title)
    if similarity_score < 0.5:
        return -1.0
    if similarity_score < threshold:
        return 0.0
    return similarity_score * 2.0


def get_year_score(target_year: int, year: int | None) -> float:
    if year is None:
        return 0.0
    if target_year <= year <= target_year + 1:
        return 1.0
    if year < target_year - 2 or year > target_year + 2:
        return -1.0
    return 0.0


def get_director_score(target_directors: list[str], director: str | None) -> float:
    """
    Compute a signed score for director similarity.

    Returns:
        1.0  → strong match (director clearly matches one of the targets)
        0.0  → uncertain or no information
       -1.0  → strong mismatch (different people, avoid false positives)
    """
    if not target_directors or not director or director == "Unknown":
        return 0.0

    # Normalize and flatten
    director_norm = norm_text(director)
    if not director_norm:
        return 0.0

    # Strong match if any target is included in candidate string
    for target_director in target_directors:
        target_norm = norm_text(target_director)
        if not target_norm:
            continue
        if similarity(target_norm, director_norm) >= 0.9:
            return 1.0

    # Otherwise aggregate all targets into one string
    target_combined = "".join(norm_text(d) for d in target_directors)
    sim = similarity(target_combined, director_norm)

    return -1.0 if sim < 0.5 else 0.0
