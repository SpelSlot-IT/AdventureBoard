from datetime import date

from app.util import get_next_wednesday, get_this_month, get_this_week, get_upcoming_week


def test_get_next_wednesday_returns_same_day():
    today = date(2024, 6, 19)  # Wednesday
    assert get_next_wednesday(today) == today


def test_get_next_wednesday_from_thursday():
    today = date(2024, 6, 20)  # Thursday
    assert get_next_wednesday(today) == date(2024, 6, 26)


def test_get_this_week_bounds():
    today = date(2024, 6, 18)  # Tuesday
    start, end = get_this_week(today)
    assert start == date(2024, 6, 17)
    assert end == date(2024, 6, 23)


def test_get_upcoming_week_from_tuesday():
    today = date(2024, 6, 18)  # Tuesday
    start, end = get_upcoming_week(today)
    assert start == date(2024, 6, 17)
    assert end == date(2024, 6, 23)


def test_get_upcoming_week_from_thursday():
    today = date(2024, 6, 20)  # Thursday
    start, end = get_upcoming_week(today)
    assert start == date(2024, 6, 24)
    assert end == date(2024, 6, 30)


def test_get_this_month_leap_year_february():
    today = date(2024, 2, 10)
    start, end = get_this_month(today)
    assert start == date(2024, 2, 1)
    assert end == date(2024, 2, 29)
