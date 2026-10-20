import datetime as dt

from backend.delay.matcher import find_static_trip
from backend.delay.models import ScheduleIndex, Service, StaticTrip

MONDAY = dt.date(2026, 10, 19)  # a real Monday, confirmed against currentDate
SUNDAY = dt.date(2026, 10, 18)


def make_index() -> ScheduleIndex:
    index = ScheduleIndex()
    index.services = {
        "Weekday": Service(
            service_id="Weekday",
            weekdays=frozenset({0, 1, 2, 3, 4}),
            start_date=dt.date(2026, 1, 1),
            end_date=dt.date(2026, 12, 31),
        ),
        "Sunday": Service(
            service_id="Sunday",
            weekdays=frozenset({6}),
            start_date=dt.date(2026, 1, 1),
            end_date=dt.date(2026, 12, 31),
        ),
    }
    index.trips_by_suffix["079850_1..S15R"] = [
        StaticTrip(
            trip_id="XL0S1-1-1094-S02_079850_1..S15R",
            route_id="1",
            service_id="Weekday",
            direction_id="1",
        ),
        StaticTrip(
            trip_id="ASP26GEN-1-1094-S02_079850_1..S15R",
            route_id="1",
            service_id="Sunday",
            direction_id="1",
        ),
    ]
    return index


def test_matches_trip_active_on_that_date():
    index = make_index()
    trip = find_static_trip(index, "079850_1..S15R", "1", MONDAY)
    assert trip is not None
    assert trip.service_id == "Weekday"


def test_picks_the_service_actually_running_that_day():
    index = make_index()
    trip = find_static_trip(index, "079850_1..S15R", "1", SUNDAY)
    assert trip is not None
    assert trip.service_id == "Sunday"


def test_no_match_for_unknown_suffix():
    index = make_index()
    assert find_static_trip(index, "999999_1..S15R", "1", MONDAY) is None


def test_no_match_for_wrong_route():
    index = make_index()
    assert find_static_trip(index, "079850_1..S15R", "7", MONDAY) is None
