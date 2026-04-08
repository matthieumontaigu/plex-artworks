from typing import TypedDict, cast

"""
{
    "iso_3166_1": "BG",
    "release_dates": [
        {
            "certification": "c",
            "descriptors": [],
            "iso_639_1": "",
            "note": "",
            "release_date": "2012-08-28T00:00:00.000Z",
            "type": 3,
        }
    ],
}
"""


class ReleaseDate(TypedDict):
    certification: str
    descriptors: list[str]
    iso_639_1: str
    note: str
    release_date: str
    type: int


class CountryInfo(TypedDict):
    iso_3166_1: str
    release_dates: list[ReleaseDate]


def get_country_release_date(
    results: list[CountryInfo], country_code: str, type_order: list[int] = [3, 4, 5]
) -> str | None:
    for country_info in results:
        if country_info["iso_3166_1"] == country_code:
            return get_first_release_date(country_info["release_dates"], type_order)
    return None


def get_first_release_date(
    release_dates: list[ReleaseDate], type_order: list[int] = [3, 4, 5]
) -> str | None:
    """
    Release	Type
    Premiere	1
    Theatrical (limited)	2
    Theatrical	3
    Digital	4
    Physical	5
    TV	6
    """
    by_type: dict[int, str] = {rd["type"]: rd["release_date"] for rd in release_dates}
    for t in type_order:
        if t in by_type:
            return by_type[t]
    return None
