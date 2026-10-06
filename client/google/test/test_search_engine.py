import unittest
from unittest.mock import patch

from client.google.search_engine import SearchEngine
from models.target import Target


class TestSearchEngine(unittest.TestCase):
    def setUp(self):
        self.engine = SearchEngine("test-key", "test-cse")
        self.target = Target("Example", ["Jane Doe"], 2024, "us", "movie")

    def item(self, identifier, *, title="Example", director=None, year=None):
        metatags = {"apple:title": title}
        if director is not None:
            metatags["og:video:director"] = director
        if year is not None:
            metatags["og:video:release_date"] = str(year)
        return {
            "link": f"https://tv.apple.com/us/movie/example/umc.cmc.{identifier}",
            "pagemap": {"metatags": [metatags]},
        }

    def test_collects_ties_across_queries_in_discovery_order(self):
        first, second, third = [self.item(i) for i in ("first", "second", "third")]
        # A different title can represent the same normalized URL and score.
        duplicate = self.item("first", title="EXAMPLE")
        with patch.object(
            self.engine, "_google_search",
            side_effect=[[first, second], [first, duplicate, third]],
        ) as search:
            urls, count = self.engine.query(self.target)

        self.assertEqual(urls, [item["link"] for item in (first, second, third)])
        self.assertEqual(count, 2)
        self.assertEqual(search.call_count, 2)

    def test_higher_score_replaces_previous_ties(self):
        first, second = self.item("first"), self.item("second")
        better = self.item("better", director="Jane Doe")
        tied = self.item("tied", director="Jane Doe")
        with patch.object(
            self.engine, "_google_search",
            side_effect=[[first, second], [better, tied]],
        ):
            self.assertEqual(
                self.engine.query(self.target), ([better["link"], tied["link"]], 2)
            )

    def test_strong_match_finishes_response_and_skips_next_query(self):
        weaker = self.item("weaker")
        first = self.item("first", director="Jane Doe", year=2024)
        second = self.item("second", director="Jane Doe", year=2024)
        with patch.object(
            self.engine, "_google_search", return_value=[weaker, first, second, weaker]
        ) as search:
            self.assertEqual(
                self.engine.query(self.target), ([first["link"], second["link"]], 1)
            )

        search.assert_called_once()

    def test_returns_empty_list_when_candidates_are_below_threshold(self):
        weak = self.item("weak", title="", director="Jane Doe")
        with patch.object(self.engine, "_google_search", return_value=[weak]):
            self.assertEqual(self.engine.query(self.target), ([], 2))

    def test_returns_empty_list_when_no_candidates_are_eligible(self):
        rejected = self.item("rejected", director="Someone Else")
        with patch.object(self.engine, "_google_search", return_value=[rejected]):
            self.assertEqual(self.engine.query(self.target), ([], 2))


if __name__ == "__main__":
    unittest.main()
