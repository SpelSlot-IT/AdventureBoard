from flask import jsonify
from datetime import datetime, timedelta, date
from flask import current_app
from collections import defaultdict
from typing import Dict, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from .models import *

def check_release():
    """
    Returns True/False whether the release date has passed.
    """
    stmt = db.select(VariableStorage).limit(1)
    variable = db.session.execute(stmt).scalar_one_or_none()
    return variable.release_state if variable else False
     
def get_next_wednesday():
    today = date.today()
    days_ahead = (2 - today.weekday() + 7) % 7  # 2 is Wednesday
    return today if days_ahead == 0 else today + timedelta(days=days_ahead)

def release_assignments():
    try:
        stmt = (
            db.update(VariableStorage)
            .where(VariableStorage.id == 1)
            .values(release_state=True)
            .execution_options(synchronize_session="fetch")  # keeps ORM objects in sync
        )
        db.session.execute(stmt)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    
def reset_release():
    try:
        stmt = (
            db.update(VariableStorage)
            .where(VariableStorage.id == 1)
            .values(release_state=False)
            .execution_options(synchronize_session="fetch")  # keeps ORM objects in sync
        )
        db.session.execute(stmt)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500    
    
def delete_expired_assignments():
    pass   

# Constants
WAITING_LIST_ID = -999             # in-memory placeholder used by the planner
WAITING_LIST_NAME = "Waiting List"  # unique name used to create the waiting-list adventure


def make_waiting_list():
    """
    Ensure a waiting-list Adventure exists in the DB and return its id.
    """
    next_wed = get_next_wednesday()

    # Try to find an existing waiting-list adventure
    row = db.session.execute(
        db.select(Adventure).where(Adventure.id == WAITING_LIST_ID)
    ).scalars().first()
    if row:
        return row.id

    # Create a small waiting-list adventure record and return its id
    waiting_list = Adventure(
                id=WAITING_LIST_ID,
                title=WAITING_LIST_NAME,
                max_players=0,
                short_description='',
                date=next_wed,
            )
    db.session.add(waiting_list)
    db.session.flush()  # ensure waiting.id is populated
    return waiting_list
    
def try_to_signup_user_for_adventure(taken_places, players_signedup_not_assigned, adventure, user, top_three=True):
    """
    Attempts to sign up a user for an adventure.

    Modifies:
      - taken_places (dict): increments the count for this adventure.
      - players_signedup_not_assigned (list): removes the user if successfully assigned.
    """
    # Check if there is still room
    if taken_places.get(adventure.id, 0) < adventure.max_players:
        # Create an assignment (assuming this persists automatically)
        assignment =AdventureAssignment(user=user, adventure=adventure, top_three=top_three)
        db.session.add(assignment)
        db.session.flush()

        # Increment the number of taken places
        taken_places[adventure.id] = taken_places.get(adventure.id, 0) + 1
        
        # Remove the player from the not-assigned list (if present)
        if user in players_signedup_not_assigned:
            players_signedup_not_assigned.remove(user)
        
        return True  # Success
    return False  # No slot available


def assign_players_to_adventures():
    """
    Creates assignments for players that signed up this week. Working in 4 rounds:
    1. Signup all players that played last week, if they try to signup again for an ongoing adventure.
    2. Signup all remaining players ranked by their karma to the first available adventure they signed up for according to there priority.
    3. Signup all remaining players ranked by their karma to any available adventure. Sorted by random.
    4. Signup the rest of the players to the waiting list.
    This means that a player with more karma will always be preferred also if the adventure was a lower priority of his.
    """
    today = datetime.today()
    start_of_week = today - timedelta(days=today.weekday())  # Monday
    end_of_week = start_of_week + timedelta(days=6)          # Sunday
    # create a placeholder that will track how many places are already taken per adventure
    taken_places = defaultdict(int)

   # Subquery: get all assigned user ids this week
    assigned_ids_subq = (
        db.select(User.id)
        .join(User.assignments)
        .join(AdventureAssignment.adventure)
        .filter(Adventure.date >= start_of_week, Adventure.date <= end_of_week)
    )

    # Main query: players signed up this week but NOT in assigned_ids_subq
    players_signedup_not_assigned = list(
        db.session.execute(
            db.select(User)
            .join(User.signups)
            .join(Signup.adventure)
            .filter(
                Adventure.date >= start_of_week,
                Adventure.date <= end_of_week,
                ~User.id.in_(assigned_ids_subq)   # exclude already assigned player
            )
            .options(
                joinedload(User.signups).joinedload(Signup.adventure),
                joinedload(User.signups)
            )
            .order_by(User.karma.desc())
            .distinct()
        )
        .unique()   # ensures deduplication when eager-loading collections
        .scalars()
        .all()
    )
   
    
    # -- First round of assigning players --
    # Assign all players that already played last week.
    for user in players_signedup_not_assigned:
        # For every signup per player check if the player was already assigned for the predecessor of this adventure
        for signup in user.signups:
            pre = signup.adventure.predecessor
            if pre and any(a.user_id == user.id for a in pre.assignments):
                adventure = signup.adventure
                if try_to_signup_user_for_adventure(taken_places, players_signedup_not_assigned, adventure, user, top_three=True): break

    # -- Second round of assigning players --
    # Assign all players ranked by their karma to the first available adventure in there signups. 
    # (That means that a player with a higher karma will still get an adventure if it was their 3. priority over a player with less karma but the 1. priority)
    for user in players_signedup_not_assigned:
        for signup in user.signups:
            adventure = signup.adventure
            if try_to_signup_user_for_adventure(taken_places, players_signedup_not_assigned, adventure, user, top_three=True): break

    adventures_this_week = (
        db.session.execute(
            db.select(Adventure)
            .filter(Adventure.date >= start_of_week, Adventure.date <= end_of_week)
            .distinct()
        )
        .scalars()
        .all()
    )

    # -- Third round of assigning players --
    # Assign all players ranked by their karma to the first available adventure independent of any signups. 
    for user in players_signedup_not_assigned:
        for adventure in adventures_this_week:
            # Check if player still fits into the adventure
            if taken_places[adventure.id] < adventure.max_players:
                if try_to_signup_user_for_adventure(taken_places, players_signedup_not_assigned, adventure, user, top_three=False): break


    # -- Fourth round of assigning players --
    # Assign all players not assigned yet to the waiting list.
    waiting_list = make_waiting_list()
    for user in players_signedup_not_assigned:
        try_to_signup_user_for_adventure(taken_places, players_signedup_not_assigned, waiting_list, user, top_three=False)

    db.session.commit()

def has_no_empty_params(rule):
    defaults = rule.defaults if rule.defaults is not None else ()
    arguments = rule.arguments if rule.arguments is not None else ()
    return len(defaults) >= len(arguments)

def get_google():
    return current_app.extensions["google_oauth"].client, current_app.extensions["google_oauth"].provider_cfg


def reassign_karma():

    # +100 karma for creating an adventure
    creators = db.session.execute(
        db.select(User).join(Adventure).distinct()
    ).scalars().all()
    for user in creators:
        user.karma += 100

    # -100 karma for not appearing
    non_appearances = db.session.execute(
        db.select(User).join(AdventureAssignment).where(AdventureAssignment.appeared.is_(False))
    ).scalars().all()
    for user in non_appearances:
        user.karma -= 100

    # +10 karma for being assigned to something not in top three
    off_prefs = db.session.execute(
        db.select(User).join(AdventureAssignment).where(AdventureAssignment.top_three.is_(False))
    ).scalars().all()
    for user in off_prefs:
        user.karma += 10

    # +1 karma for playing
    played = db.session.execute(
        db.select(User).join(AdventureAssignment).where(AdventureAssignment.appeared.is_(True))
    ).scalars().all()
    for user in played:
        user.karma += 1

    db.session.commit()
