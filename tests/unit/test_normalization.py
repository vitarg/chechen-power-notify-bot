from app.matching.address import parse_user_address
from app.utils.text import comparable_name, normalize_text


def test_normalize_common_address_forms() -> None:
    assert normalize_text("г.Грозный ул.Мира") == "г.грозный ул.мира"
    assert comparable_name("ул. Мира") == "мира"


def test_parse_grozny_street() -> None:
    parsed = parse_user_address("Грозный, ул. Мира")
    assert parsed.locality == "грозный"
    assert parsed.street == "мира"
    assert parsed.confidence.value == "high"


def test_parse_city_only() -> None:
    parsed = parse_user_address("Урус-Мартан")
    assert parsed.locality == "урус-мартан"
    assert parsed.street is None
    assert parsed.confidence.value == "medium"


def test_parse_short_settlement_prefix() -> None:
    parsed = parse_user_address("п. Заря")
    assert parsed.locality == "заря"
    assert parsed.street is None
    assert parsed.confidence.value == "medium"


def test_parse_district_is_not_locality() -> None:
    parsed = parse_user_address("Урус-Мартановский район")
    assert parsed.district == "урус-мартановский"
    assert parsed.locality is None
