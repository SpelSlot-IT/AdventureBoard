"""Tests for the reassign_karma function."""
from datetime import date, timedelta

import pytest

from app.models import Adventure, Assignment, User
from app.provider import db
from app.util import reassign_karma, get_this_week


@pytest.fixture()
def users(app):
    """Create test users with known starting karma."""
    with app.app_context():
        dm = User.create(google_id="dm1", name="DM One", karma=1000)
        player1 = User.create(google_id="p1", name="Player One", karma=1000)
        player2 = User.create(google_id="p2", name="Player Two", karma=1000)
        player3 = User.create(google_id="p3", name="Player Three", karma=1000)
        db.session.commit()
        return {
            "dm": dm.id,
            "player1": player1.id,
            "player2": player2.id,
            "player3": player3.id,
        }


def test_dm_gets_karma_for_creating_adventure(app, users):
    """DMs should receive +500 karma for creating an adventure this week."""
    today = date.today()
    start_of_week, _ = get_this_week(today)

    with app.app_context():
        dm = db.session.get(User, users["dm"])
        initial_karma = dm.karma

        # Create adventure this week
        Adventure.create(
            title="Test Adventure",
            short_description="A test",
            user_id=dm.id,
            date=start_of_week + timedelta(days=2),  # Wednesday of this week
        )
        db.session.commit()

        reassign_karma(today)

        dm = db.session.get(User, users["dm"])
        assert dm.karma == initial_karma + 500


def test_dm_karma_not_assigned_for_different_week(app, users):
    """DMs should NOT receive karma for adventures in a different week."""
    today = date.today()
    start_of_week, _ = get_this_week(today)

    with app.app_context():
        dm = db.session.get(User, users["dm"])
        initial_karma = dm.karma

        # Create adventure NEXT week (should not count)
        Adventure.create(
            title="Future Adventure",
            short_description="A test",
            user_id=dm.id,
            date=start_of_week + timedelta(days=9),  # Next week
        )
        db.session.commit()

        reassign_karma(today)

        dm = db.session.get(User, users["dm"])
        assert dm.karma == initial_karma  # No change


def test_player_loses_karma_for_not_appearing(app, users):
    """Players who don't appear should lose 500 karma."""
    today = date.today()
    start_of_week, _ = get_this_week(today)

    with app.app_context():
        dm = db.session.get(User, users["dm"])
        player = db.session.get(User, users["player1"])
        initial_karma = player.karma

        adventure = Adventure.create(
            title="Test Adventure",
            short_description="A test",
            user_id=dm.id,
            date=start_of_week + timedelta(days=2),
            is_waitinglist=0,
        )

        # Player assigned but did NOT appear
        assignment = Assignment(
            user_id=player.id,
            adventure_id=adventure.id,
            appeared=False,
            preference_place=1,
        )
        db.session.add(assignment)
        db.session.commit()

        reassign_karma(today)

        player = db.session.get(User, users["player1"])
        # Player loses 500 for not appearing
        assert player.karma == initial_karma - 500


def test_waiting_list_attendee_gets_karma(app, users):
    """Players on waiting list who appeared should get +200 karma."""
    today = date.today()
    start_of_week, _ = get_this_week(today)

    with app.app_context():
        dm = db.session.get(User, users["dm"])
        player = db.session.get(User, users["player1"])
        initial_karma = player.karma

        # Create waiting list adventure
        adventure = Adventure.create(
            title="Waiting List",
            short_description="A waiting list",
            user_id=dm.id,
            date=start_of_week + timedelta(days=2),
            is_waitinglist=1,
        )

        # Player on waiting list who appeared
        assignment = Assignment(
            user_id=player.id,
            adventure_id=adventure.id,
            appeared=True,
        )
        db.session.add(assignment)
        db.session.commit()

        reassign_karma(today)

        player = db.session.get(User, users["player1"])
        assert player.karma == initial_karma + 200


def test_waiting_list_non_attendee_gets_karma(app, users):
    """Players on waiting list who did not appear should get +180 karma."""
    today = date.today()
    start_of_week, _ = get_this_week(today)

    with app.app_context():
        dm = db.session.get(User, users["dm"])
        player = db.session.get(User, users["player1"])
        initial_karma = player.karma

        # Create waiting list adventure
        adventure = Adventure.create(
            title="Waiting List",
            short_description="A waiting list",
            user_id=dm.id,
            date=start_of_week + timedelta(days=2),
            is_waitinglist=1,
        )

        # Player on waiting list who did NOT appear
        assignment = Assignment(
            user_id=player.id,
            adventure_id=adventure.id,
            appeared=False,
        )
        db.session.add(assignment)
        db.session.commit()

        reassign_karma(today)

        player = db.session.get(User, users["player1"])
        assert player.karma == initial_karma + 180


@pytest.mark.parametrize(
    "preference_place,expected_bonus",
    [
        (1, 100),  # First choice
        (2, 120),  # Second choice
        (3, 140),  # Third choice
        (4, 150),  # Assigned outside top three
    ],
)
def test_choice_based_karma_for_attendees(app, users, preference_place, expected_bonus):
    """Players who attend should get karma based on their preference choice."""
    today = date.today()
    start_of_week, _ = get_this_week(today)

    with app.app_context():
        dm = db.session.get(User, users["dm"])
        player = db.session.get(User, users["player1"])
        initial_karma = player.karma

        adventure = Adventure.create(
            title="Test Adventure",
            short_description="A test",
            user_id=dm.id,
            date=start_of_week + timedelta(days=2),
            is_waitinglist=0,
        )

        # Player assigned and appeared
        assignment = Assignment(
            user_id=player.id,
            adventure_id=adventure.id,
            appeared=True,
            preference_place=preference_place,
        )
        db.session.add(assignment)
        db.session.commit()

        reassign_karma(today)

        player = db.session.get(User, users["player1"])
        assert player.karma == initial_karma + expected_bonus


def test_karma_only_assigned_for_specified_week(app, users):
    """Karma should only be assigned for adventures in the specified week."""
    today = date.today()
    start_of_week, _ = get_this_week(today)
    last_week = today - timedelta(days=7)

    with app.app_context():
        dm = db.session.get(User, users["dm"])
        player = db.session.get(User, users["player1"])
        initial_karma = player.karma

        # Create adventure LAST week
        adventure = Adventure.create(
            title="Last Week Adventure",
            short_description="A test",
            user_id=dm.id,
            date=start_of_week - timedelta(days=3),  # Last week
            is_waitinglist=0,
        )

        # Player assigned and appeared last week
        assignment = Assignment(
            user_id=player.id,
            adventure_id=adventure.id,
            appeared=True,
            preference_place=1,
        )
        db.session.add(assignment)
        db.session.commit()

        # Run karma for THIS week - should not affect last week's adventure
        reassign_karma(today)

        player = db.session.get(User, users["player1"])
        assert player.karma == initial_karma  # No change

        # Now run karma for LAST week - should assign karma
        reassign_karma(last_week)

        player = db.session.get(User, users["player1"])
        assert player.karma == initial_karma + 100  # First choice bonus


def test_karma_is_cumulative_when_run_multiple_times(app, users):
    """Running karma multiple times should apply changes cumulatively (known issue)."""
    today = date.today()
    start_of_week, _ = get_this_week(today)

    with app.app_context():
        dm = db.session.get(User, users["dm"])
        player = db.session.get(User, users["player1"])
        initial_karma = player.karma

        adventure = Adventure.create(
            title="Test Adventure",
            short_description="A test",
            user_id=dm.id,
            date=start_of_week + timedelta(days=2),
            is_waitinglist=0,
        )

        assignment = Assignment(
            user_id=player.id,
            adventure_id=adventure.id,
            appeared=True,
            preference_place=1,
        )
        db.session.add(assignment)
        db.session.commit()

        # Run karma twice
        reassign_karma(today)
        reassign_karma(today)

        player = db.session.get(User, users["player1"])
        # Karma is applied twice (this is the current behavior, documented as warning)
        assert player.karma == initial_karma + 100 + 100
