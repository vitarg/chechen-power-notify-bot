from datetime import date

from app.sources.chechenenergo import html_to_text, parse_segments


def test_parse_multiple_paragraph_segments() -> None:
    html = """
    <p><strong>с 09.00 до 16.00 –Урус-Мартановский район: </strong>с.Алхан-Юрт, частично с.Старые-Атаги;</p>
    <p><strong>с 09.00 до 16.00-Частично г.Гудермес</strong></p>
    """
    text = html_to_text(html)
    segments = parse_segments(date(2026, 6, 11), text)
    assert len(segments) == 2
    assert segments[0].district == "урус-мартановский"
    assert segments[0].locality == "алхан-юрт"
    assert "старые-атаги" in segments[0].landmarks
    assert segments[1].locality == "гудермес"


def test_parse_street_segment() -> None:
    text = (
        "с 09.00 до 14.00–Часть г. Грозного: ул.Дади Айбики, ул.Мира (частично), "
        "ул.Поповича, Дачные участки (п.Заря);"
    )
    segments = parse_segments(date(2026, 6, 2), text)
    assert len(segments) == 1
    assert segments[0].locality == "грозный"
    assert "мира" in segments[0].streets
    assert "дачные участки" not in segments[0].streets
    assert "дачные участки" in segments[0].landmarks
    assert "заря" in segments[0].landmarks


def test_parse_street_after_prefix_with_alias() -> None:
    text = (
        "с 16.00 до 18.00 Часть г. Грозного: новые МКД по ул.Сулейманова "
        "(Новаторов) и частный сектор района Палестинских домов"
    )
    segments = parse_segments(date(2026, 7, 10), text)
    assert len(segments) == 1
    assert segments[0].district is None
    assert segments[0].locality == "грозный"
    assert "сулейманова" in segments[0].streets
    assert "новаторов" in segments[0].streets


def test_parse_multiple_settlements_in_district_segment() -> None:
    text = "с 08.00 до 18.00-Шалинский район: с.Агишты, с.Герменчук, с.Сержень-Юрт, с.Автуры, частично г.Шали;"
    segments = parse_segments(date(2026, 7, 1), text)
    assert len(segments) == 1
    assert segments[0].district == "шалинский"
    assert segments[0].locality == "агишты"
    assert "герменчук" in segments[0].landmarks
    assert "сержень-юрт" in segments[0].landmarks
    assert "автуры" in segments[0].landmarks
    assert "шали" in segments[0].landmarks
    assert "частично г.шали" not in segments[0].landmarks


def test_parse_settlement_inside_city_as_landmark() -> None:
    text = "с 10:00 до 13:00- Часть г.Грозного: п.Алхан-Чурт;"
    segments = parse_segments(date(2026, 7, 1), text)
    assert len(segments) == 1
    assert segments[0].locality == "грозный"
    assert segments[0].landmarks == ["алхан-чурт"]


def test_district_only_segment_has_no_landmarks() -> None:
    text = "с 09.00 до 17.00-Веденский район"
    segments = parse_segments(date(2026, 7, 1), text)
    assert len(segments) == 1
    assert segments[0].district == "веденский"
    assert segments[0].locality is None
    assert segments[0].landmarks == []


def test_split_multiple_times_in_one_paragraph() -> None:
    text = (
        "с 09.00 до 14.00–Часть г. Грозного: ул.Мира; "
        "с 10.00 до 13.00-Часть г. Гудермеса"
    )
    segments = parse_segments(date(2026, 6, 2), text)
    assert len(segments) == 2
    assert segments[0].locality == "грозный"
    assert segments[1].locality == "гудермес"
