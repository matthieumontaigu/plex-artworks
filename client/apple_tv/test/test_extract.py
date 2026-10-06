import unittest
from types import SimpleNamespace
from unittest.mock import call, patch

from client.apple_tv.extract import get_poster_url, person_url_to_collection
from utils.parsing import parse_html


class TestPosterCollections(unittest.TestCase):
    person_url = "https://tv.apple.com/fr/person/example/umc.cpc.2h9wn8jl15vkbhos9c9jb102d"
    content_id = "umc.cmc.example"
    poster_html = (
        '<a href="/fr/movie/example/umc.cmc.example"><picture>'
        '<source srcset="https://example.com/poster/400x600.jpg 1x">'
        "</picture></a>"
    )

    def get_poster(self, entity="movie", max_persons=3):
        page = parse_html(
            f'<a class="person-lockup" href="{self.person_url}"></a>'
            '<a class="person-lockup" href="https://tv.apple.com/fr/person/other/umc.cpc.other"></a>'
        )
        return get_poster_url(
            page, f"https://tv.apple.com/fr/{entity}/example/{self.content_id}", max_persons
        )

    @patch("client.apple_tv.extract.time.sleep")
    @patch("client.apple_tv.extract.get_request")
    def test_regular_collection_success_skips_fallback(self, request, sleep):
        request.return_value = SimpleNamespace(text=self.poster_html)
        self.assertEqual(self.get_poster(), "https://example.com/poster/2000x0w.jpg")
        request.assert_called_once_with(person_url_to_collection(self.person_url, "movie"))
        sleep.assert_not_called()

    @patch("client.apple_tv.extract.time.sleep")
    @patch("client.apple_tv.extract.get_request")
    def test_kids_collection_fallback(self, request, sleep):
        regular_responses = (
            None,
            SimpleNamespace(text='<a href="/movie/umc.cmc.unrelated"></a>'),
            SimpleNamespace(text=f'<a href="/{self.content_id}"></a>'),
            SimpleNamespace(text=f'<a href="/{self.content_id}"><picture></picture></a>'),
        )
        for entity in ("movie", "show"):
            for regular_response in regular_responses:
                with self.subTest(entity=entity, response=regular_response):
                    request.reset_mock()
                    sleep.reset_mock()
                    request.side_effect = [regular_response, SimpleNamespace(text=self.poster_html)]
                    self.assertEqual(self.get_poster(entity), "https://example.com/poster/2000x0w.jpg")
                    self.assertEqual(request.call_args_list, [
                        call(person_url_to_collection(self.person_url, entity)),
                        call("https://tv.apple.com/fr/collection/enfants-et-famille/uts.col.kidsfamily_of_person?ctx_person=umc.cpc.2h9wn8jl15vkbhos9c9jb102d"),
                    ])
                    sleep.assert_called_once_with(1.0)

    @patch("client.apple_tv.extract.time.sleep")
    @patch("client.apple_tv.extract.get_request")
    def test_missing_poster_respects_person_limit(self, request, sleep):
        request.return_value = SimpleNamespace(text="")
        self.assertIsNone(self.get_poster(max_persons=1))
        self.assertEqual(request.call_args_list, [
            call(person_url_to_collection(self.person_url, "movie")),
            call(person_url_to_collection(self.person_url, "kidsfamily")),
        ])

    def test_kids_collection_preserves_country_and_person(self):
        self.assertEqual(
            person_url_to_collection("https://tv.apple.com/us/person/other/umc.cpc.other", "kidsfamily"),
            "https://tv.apple.com/us/collection/enfants-et-famille/uts.col.kidsfamily_of_person?ctx_person=umc.cpc.other",
        )


if __name__ == "__main__":
    unittest.main()
