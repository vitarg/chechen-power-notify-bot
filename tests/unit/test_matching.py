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


def test_unmatched_street_does_not_fall_back_to_wide_locality() -> None:
    address = parse_user_address("Грозный, ул. Хабусиевой")
    result = match_address_to_segment(
        address,
        segment(
            raw_zone="Часть г. Грозного: новые МКД по ул.Сулейманова (Новаторов)",
            streets=["сулейманова", "новаторов"],
        ),
    )
    assert not result.matched
    assert result.reason == "street_mismatch"


def test_unparsed_street_segment_does_not_match_whole_locality() -> None:
    address = parse_user_address("Грозный, ул. Хабусиевой")
    result = match_address_to_segment(
        address,
        segment(raw_zone="Часть г. Грозного: новые МКД по ул.Сулейманова", streets=[]),
    )
    assert not result.matched
    assert result.reason == "unparsed_street_segment"


def test_settlement_inside_city_matches_landmark_only() -> None:
    segment_with_settlement = segment(
        raw_zone="Часть г.Грозного: п.Алхан-Чурт",
        normalized_zone="часть г.грозного п.алхан-чурт",
        landmarks=["алхан-чурт"],
    )

    assert match_address_to_segment(parse_user_address("п. Алхан-Чурт"), segment_with_settlement).matched

    result = match_address_to_segment(parse_user_address("Грозный, ул. Хабусиевой"), segment_with_settlement)
    assert not result.matched
    assert result.reason == "landmark_mismatch"


def test_district_segment_matches_any_listed_settlement() -> None:
    segment_with_villages = segment(
        raw_zone="Шалинский район: с.Агишты, с.Герменчук",
        normalized_zone="шалинский район с.агишты с.герменчук",
        district="шалинский",
        locality="агишты",
        landmarks=["герменчук"],
    )

    assert match_address_to_segment(parse_user_address("с. Агишты"), segment_with_villages).matched
    assert match_address_to_segment(parse_user_address("Герменчук"), segment_with_villages).matched
