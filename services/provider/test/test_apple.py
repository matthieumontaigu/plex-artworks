import unittest
from unittest.mock import MagicMock, call, patch

from models.target import Target
from services.provider.apple import AppleProvider


class TestAppleProvider(unittest.TestCase):
    def setUp(self):
        self.engine = MagicMock()
        self.provider = AppleProvider(self.engine)
        self.target = Target("Example", ["Jane Doe"], 2024, "us", "movie")

    def get_artworks(self):
        return self.provider.get_artworks(
            self.target.title, self.target.directors, self.target.year,
            self.target.country, self.target.entity,
        )

    @patch("services.provider.apple.get_apple_tv_artworks")
    def test_returns_first_validated_candidate_and_stops(self, extract):
        self.engine.query.return_value = (["first", "second", "third"], 2)
        self.engine.validate.side_effect = [False, True]
        attributes = {"name": "Example"}
        extract.side_effect = [
            (None, None, None, None),
            (attributes, "poster", "background", "logo"),
        ]

        self.assertEqual(self.get_artworks(), ("poster", "background", "logo", 2))
        self.engine.query.assert_called_once_with(self.target)
        self.assertEqual(extract.call_args_list, [call("first"), call("second")])
        self.assertEqual(self.engine.validate.call_args_list, [
            call("first", None, self.target),
            call("second", attributes, self.target),
        ])

    @patch("services.provider.apple.get_apple_tv_artworks")
    def test_first_candidate_validates_without_fetching_remaining_urls(self, extract):
        self.engine.query.return_value = (["first", "second"], 1)
        self.engine.validate.return_value = True
        extract.return_value = ({"name": "Example"}, "poster", None, None)

        self.assertEqual(self.get_artworks(), ("poster", None, None, 1))
        extract.assert_called_once_with("first")

    @patch("services.provider.apple.get_apple_tv_artworks")
    def test_returns_no_artworks_when_all_candidates_fail(self, extract):
        self.engine.query.return_value = (["first", "second"], 2)
        self.engine.validate.return_value = False
        extract.return_value = (None, None, None, None)

        self.assertEqual(self.get_artworks(), (None, None, None, 2))
        self.assertEqual(extract.call_args_list, [call("first"), call("second")])

    @patch("services.provider.apple.get_apple_tv_artworks")
    def test_empty_candidates_skip_extraction_and_validation(self, extract):
        self.engine.query.return_value = ([], 2)

        self.assertEqual(self.get_artworks(), (None, None, None, 2))
        extract.assert_not_called()
        self.engine.validate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
