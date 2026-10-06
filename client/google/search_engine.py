from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

import requests

from client.google.parser import parse_item_from_cse
from client.google.scoring import REQUIRED_SCORE, STRONG_SCORE, VALIDATION_SCORE, Scorer
from client.google.utils import quote

if TYPE_CHECKING:
    from client.apple_tv.attributes import Attributes
    from models.target import Target

logger = logging.getLogger(__name__)

GOOGLE_ENDPOINT = "https://www.googleapis.com/customsearch/v1"


class SearchEngine:
    """
    Thin Google Programmable Search client for tv.apple.com.
    - country/entity-scoped queries only: site:tv.apple.com/{country}/{entity}
    - scoring/gating delegated to Scorer (easy to unit-test)
    """

    def __init__(
        self,
        api_key: str,
        cse_id: str,
        *,
        session: requests.Session | None = None,
        min_interval_s: float = 0.5,
        timeout_s: float = 20.0,
        scorer: Scorer | None = None,
    ) -> None:
        self.api_key = api_key
        self.cse_id = cse_id
        if not self.api_key or not self.cse_id:
            raise ValueError("Google API key and CSE ID are required (args or env).")

        self.session = session or requests.Session()
        self.min_interval_s = float(min_interval_s)
        self.timeout_s = float(timeout_s)
        self._last_call_ts = 0.0

        self.scorer = scorer or Scorer()

    # --- public API ---

    def query(self, target: Target) -> tuple[list[str], int]:
        """Return unique best-scoring URLs in discovery order and the query count."""
        title = target.title
        directors = target.directors
        entity = self._normalize_entity(target.entity)
        country = self._normalize_country(target.country)

        queries = self._build_queries(title, directors, country, entity)

        best_score = 0.0
        best_urls: list[str] = []
        seen: set[tuple[str, str | None]] = set()
        query_count = 0

        for q in queries:
            query_count += 1
            for raw in self._google_search(q):
                item = parse_item_from_cse(raw)
                if (item.url, item.title) in seen:
                    continue
                seen.add((item.url, item.title))

                if not self.scorer.is_candidate_url(item.url):
                    continue

                score = self.scorer.compute(item, target)
                logger.debug("Score: %s, Item: %s", score, item)
                if score is None:
                    continue

                if score > best_score:
                    best_score, best_urls = score, [item.url]
                elif score == best_score and item.url not in best_urls:
                    best_urls.append(item.url)

            # Finish this response to collect ties before skipping further queries.
            if best_score >= STRONG_SCORE:
                break

        return (best_urls if best_score >= REQUIRED_SCORE else []), query_count

    def validate(self, url: str, attributes: Attributes | None, target: Target) -> bool:
        score = self.scorer.score_attributes(url, attributes, target)
        return score is not None and score >= VALIDATION_SCORE

    # --- internals ---

    def _build_queries(
        self,
        title: str,
        directors: list[str],
        country: str,
        entity: str,
    ) -> list[str]:
        base = f"site:tv.apple.com/{country}/{entity} {title}"
        queries: list[str] = []
        if directors:
            queries.append(f"{base} {quote(directors[0])}")
        queries.append(base)
        return queries

    def _google_search(self, query: str, num: int = 10) -> list[dict]:
        self._respect_min_interval()

        params = {
            "key": self.api_key,
            "cx": self.cse_id,
            "q": query,
            "num": min(max(num, 1), 10),
            "safe": "off",
        }

        backoff = 0.6
        for attempt in range(4):
            try:
                r = self.session.get(
                    GOOGLE_ENDPOINT, params=params, timeout=self.timeout_s
                )
                if r.status_code in (429, 500, 502, 503, 504):
                    raise _TransientHTTPError(r.status_code, r.text)
                r.raise_for_status()
                return r.json().get("items") or []
            except _TransientHTTPError as e:
                if attempt == 3:
                    logger.warning(
                        "Google CSE transient %s (final) for %r", e.status, query
                    )
                    return []
                time.sleep(backoff)
                backoff *= 1.6
            except requests.RequestException as e:
                logger.warning("Google CSE request failed: %s", e)
                return []
            finally:
                self._last_call_ts = time.monotonic()
        return []

    def _respect_min_interval(self) -> None:
        delta = time.monotonic() - self._last_call_ts
        if delta < self.min_interval_s:
            time.sleep(self.min_interval_s - delta)

    @staticmethod
    def _normalize_entity(entity: str) -> str:
        e = (entity or "").strip().lower()
        if e not in {"movie", "show"}:
            raise ValueError("entity must be 'movie' or 'show'")
        return e

    @staticmethod
    def _normalize_country(country: str) -> str:
        c = (country or "").strip().lower()
        if not c:
            raise ValueError("country (lowercase) is required")
        return c


class _TransientHTTPError(Exception):
    def __init__(self, status: int, msg: str = ""):
        super().__init__(f"Transient HTTP {status}: {msg}")
        self.status = status
