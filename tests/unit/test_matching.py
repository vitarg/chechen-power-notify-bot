from datetime import date, time

from app.domain import ParsedOutageSegment
from app.matching.address import parse_user_address
from app.matching.matcher import match_address_to_segment


def segment(**kwargs) -> ParsedOutageSegment:
    defaults = {
        "event_date": date(2026, 6, 11),
        "starts_at": time(9, 0),
        "ends_at": time(16, 0),
        "raw_zone": "zone",
        "normalized_zone": "zone",
        "district": None,
        "locality": "грозный",
        "streets": [],
        "landmarks": [],
        "segment_hash": "hash",
    }
    defaults.update(kwargs)
    return ParsedOutageSegment(**defaults)


def test_street_match() -> None:
    address = parse_user_address("Грозный, ул. Мира")
    result = match_address_to_segment(address, segment(streets=["мира"]))
    assert result.matched


def test_wide_locality_match() -> None:
    address = parse_user_address("Грозный, ул. Мира")
    result = match_address_to_segment(address, segment(streets=[]))
    assert result.matched
    assert result.reason == "wide_locality_match"


def test_district_only_does_not_match_city() -> None:
    address = parse_user_address("Урус-Мартан")
    result = match_address_to_segment(
        address,
        segment(district="урус-мартановский", locality=None, streets=[]),
    )
    assert not result.matched

