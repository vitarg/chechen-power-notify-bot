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
    assert segments[1].locality == "гудермес"


def test_parse_street_segment() -> None:
    text = "с 09.00 до 14.00–Часть г. Грозного: ул.Дади Айбики, ул.Мира (частично), ул.Поповича;"
    segments = parse_segments(date(2026, 6, 2), text)
    assert len(segments) == 1
    assert segments[0].locality == "грозный"
    assert "мира частично" in segments[0].streets


def test_split_multiple_times_in_one_paragraph() -> None:
    text = (
        "с 09.00 до 14.00–Часть г. Грозного: ул.Мира; "
        "с 10.00 до 13.00-Часть г. Гудермеса"
    )
    segments = parse_segments(date(2026, 6, 2), text)
    assert len(segments) == 2
    assert segments[0].locality == "грозный"
    assert segments[1].locality == "гудермес"

