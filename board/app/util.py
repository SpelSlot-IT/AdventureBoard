from datetime import datetime, timedelta, date
from flask import current_app
from collections import defaultdict
from sqlalchemy.orm import joinedload

from .models import *
from .email import notify_user, notifications_enabled
     
def get_next_wednesday():
    today = date.today()
    days_ahead = (2 - today.weekday() + 7) % 7  # 2 is Wednesday
    return today if days_ahead == 0 else today + timedelta(days=days_ahead)

def is_admin(user):
    return user.is_authenticated and user.privilege_level >= 2

def get_this_week():
    """
    Returns the start (Monday) and end (Sunday) of the this week.
    """
    today = date.today()
    # Find Monday of the current week
    start_of_current_week = today - timedelta(days=today.weekday())
    end_of_current_week = start_of_current_week + timedelta(days=6)

    return start_of_current_week, end_of_current_week


def get_upcoming_week():
    """
    Returns the start (Monday) and end (Sunday) of the upcoming week.
    - If today is Monday–Wednesday → return this week's Mon–Sun.
    - If today is Thursday–Sunday → return next week's Mon–Sun.
    """
    today = date.today()
    start_of_current_week, end_of_current_week = get_this_week()

    if today.weekday() <= 2:  # Mon(0), Tue(1), Wed(2)
        return start_of_current_week, end_of_current_week
    else:  # Thu–Sun
        start_of_next_week = start_of_current_week + timedelta(weeks=1)
        end_of_next_week = end_of_current_week + timedelta(weeks=1)
        return start_of_next_week, end_of_next_week
    
def check_release(adventures):
    return (len(adventures) > 0 and adventures[-1].release_assignments)

def release_assignments():
    start_of_week, end_of_week = get_upcoming_week()
    try:
        adventures = (
            db.session.scalars(
                db.select(Adventure)
                .options(db.selectinload(Adventure.assignments))  # eager load users
                .where(
                    Adventure.date >= start_of_week,
                    Adventure.date <= end_of_week,
                )
            ).all()
        )

        # Update release_assignments for these adventures
        for adventure in adventures:
            adventure.release_assignments = True

        # Commit the update before notifications
        db.session.commit()
        current_app.logger.info(
            f"Released assignments for adventures between {start_of_week} and {end_of_week}: #{len(adventures)}: {[adventure.title for adventure in adventures]}"
        )
        if notifications_enabled(current_app.config.get("EMAIL")):

            adventures = (
                db.session.scalars(
                    db.select(Adventure)
                    .options(db.selectinload(Adventure.assignments))  # eager load users
                    .where(
                        Adventure.date >= start_of_week,
                        Adventure.date <= end_of_week,
                        Adventure.release_assignments
                    )
                ).all()
            )
            # Notify assigned users (avoid duplicates)
            notified_users = set()
            for adventure in adventures:
                for assignment in adventure.assignments:
                    user = assignment.user
                    if user.id not in notified_users:
                        notify_user(user, f"You have been assigned to {adventure.title}")
                        notified_users.add(user.id)
        else:
            current_app.logger.info("Notifications where disabled. Skipped email notifications.")

    except Exception as e:
        db.session.rollback()
        raise e
    
def reset_release():
    start_of_week, end_of_week = get_upcoming_week()
    try:
        stmt = (
            db.update(Adventure)
            .filter(
                Adventure.date >= start_of_week,
                Adventure.date <= end_of_week,
            )
            .values(release_assignments=False)
        )
        db.session.execute(stmt)
        current_app.logger.info(f"Reset release for adventures between {start_of_week} and {end_of_week}")
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e  
    

WAITING_LIST_ID = -999             # in-memory placeholder used by the planner
WAITING_LIST_NAME = "Waiting List" # unique name used to create the waiting-list adventure
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
                max_players=128,
                short_description='',
                date=next_wed,
            )
    db.session.add(waiting_list)
    db.session.flush()  # ensure waiting.id is populated
    return waiting_list
    
def try_to_signup_user_for_adventure(taken_places, players_signedup_not_assigned, adventure, user, assignment_map, top_three=True):
    """
    Attempts to sign up a user for an adventure.

    Modifies:
      - taken_places (dict): increments the count for this adventure.
      - players_signedup_not_assigned (list): removes the user if successfully assigned.
      - assignment_map (dict): traces assignment in a human readable map. Provide None to disable this logging.
    """
    # Check if there is still room
    if taken_places.get(adventure.id, 0) < adventure.max_players:
        # Create an assignment (assuming this persists automatically)
        assignment = Assignment(user=user, adventure=adventure, top_three=top_three)
        db.session.add(assignment)
        if assignment_map is not None: # For human readability
            assignment_map.setdefault(adventure.title, []).append(user.display_name)
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
    2.
    3. Signup all remaining players ranked by their karma to the first available adventure they signed up for according to there priority.
    4. Signup all remaining players ranked by their karma to any available adventure. Sorted by random.
    5. Signup the rest of the players to the waiting list.
    This means that a player with more karma will always be preferred also if the adventure was a lower priority of his.
    """
    start_of_week, end_of_week = get_upcoming_week()
    # create a placeholder that will track how many places are already taken per adventure
    taken_places = defaultdict(int)
    assignment_map = defaultdict(list) # trace assignments in moa for human readability.

   # Subquery: get all assigned user ids this week
    assigned_ids_subq = (
        db.select(User.id)
        .join(User.assignments)
        .join(Assignment.adventure)
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
    current_app.logger.info(f"Players signed up for the week {start_of_week} to {end_of_week}:   #{len(players_signedup_not_assigned)}: {[user.display_name for user in players_signedup_not_assigned]} ")
   
    
    # -- First round of assigning players --
    # Assign all players that already played last week.
    round_ = []
    for user in players_signedup_not_assigned:
        # For every signup per player check if the player was already assigned for the predecessor of this adventure
        for signup in user.signups:
            pre = signup.adventure.predecessor
            if pre and any(a.user_id == user.id for a in pre.assignments):
                adventure = signup.adventure
                if try_to_signup_user_for_adventure(taken_places, players_signedup_not_assigned, adventure, user, assignment_map, top_three=True): 
                    round_.append(user.display_name)
                    break
    current_app.logger.info(f"- Players assigned in round 1: #{len(round_)}: {round_}")

    # -- Second round of assigning players --
    # Assign all story players sorted by karma.
    round_ = []
    for user in players_signedup_not_assigned:
        # For every player check if that player is story player, if not continue
        if not user.story_player:
            continue
        for signup in user.signups:
            adventure = signup.adventure
            if try_to_signup_user_for_adventure(taken_places, players_signedup_not_assigned, adventure, user, assignment_map, top_three=True): 
                round_.append(user.display_name)
                break
    current_app.logger.info(f"- Players assigned in round 2: #{len(round_)}: {round_}")

    # -- Third round of assigning players --
    # Assign all players ranked by their karma to the first available adventure in there signups. 
    # (That means that a player with a higher karma will still get an adventure if it was their 3. priority over a player with less karma but the 1. priority)
    round_ = []
    for user in players_signedup_not_assigned:
        for signup in user.signups:
            adventure = signup.adventure
            if try_to_signup_user_for_adventure(taken_places, players_signedup_not_assigned, adventure, user, assignment_map, top_three=True): 
                round_.append(user.display_name)
                break
    current_app.logger.info(f"- Players assigned in round 3: #{len(round_)}: {round_}")

    adventures_this_week = (
        db.session.execute(
            db.select(Adventure)
            .filter(Adventure.date >= start_of_week, Adventure.date <= end_of_week)
            .distinct()
        )
        .scalars()
        .all()
    )

    # -- Fourth round of assigning players --
    # Assign all players ranked by their karma to the first available adventure independent of any signups. 
    round_ = []
    for user in players_signedup_not_assigned:
        for adventure in adventures_this_week:
            # Check if player still fits into the adventure
            if taken_places[adventure.id] < adventure.max_players:
                if try_to_signup_user_for_adventure(taken_places, players_signedup_not_assigned, adventure, user, assignment_map, top_three=True): 
                    round_.append(user.display_name)
                    break
    current_app.logger.info(f"- Players assigned in round 4: #{len(round_)}: {round_}")


    # -- Fifth round of assigning players --
    # Assign all players not assigned yet to the waiting list.
    round_ = []
    waiting_list = make_waiting_list()
    for user in players_signedup_not_assigned:
        if not try_to_signup_user_for_adventure(taken_places, players_signedup_not_assigned, waiting_list, user, assignment_map, top_three=True):
            current_app.logger.error(f"Failed to assign player {user.display_name} to waiting list!")
    current_app.logger.info(f"- Players assigned in round 5: #{len(round_)}: {round_}")

    current_app.logger.info(f"Assigned players to adventures: {dict(assignment_map)}")
    db.session.commit()

def has_no_empty_params(rule):
    defaults = rule.defaults if rule.defaults is not None else ()
    arguments = rule.arguments if rule.arguments is not None else ()
    return len(defaults) >= len(arguments)

def get_google():
    return current_app.extensions["google_oauth"].client, current_app.extensions["google_oauth"].provider_cfg


def reassign_karma():
    start_of_current_week, end_of_current_week = get_this_week()
    current_app.logger.info(f"Reassigning karma for week {start_of_current_week} to {end_of_current_week}")

    # +100 karma for creating an adventure this week (DMs)
    creators = db.session.execute(
        db.select(User)
        .join(Adventure)
        .where(Adventure.date >= start_of_current_week, Adventure.date <= end_of_current_week)
        .distinct()
    ).scalars().all()
    for user in creators:
        user.karma += 100
    current_app.logger.info(f" - Assigned 100 karma to DMs: #{len(creators)}: {[user.display_name for user in creators]}")

    # -100 karma for not appearing in this week's adventures
    non_appearances = db.session.execute(
        db.select(User)
        .join(Assignment)
        .join(Adventure)
        .where(
            Assignment.appeared.is_(False),
            Adventure.id != WAITING_LIST_ID,
            Adventure.date >= start_of_current_week,
            Adventure.date <= end_of_current_week
        )
    ).scalars().all()
    for user in non_appearances:
        user.karma -= 100
    current_app.logger.info(f" - Assigned -100 karma to players who did not appear: #{len(non_appearances)}: {[user.display_name for user in non_appearances]}")

    # +10 karma for being assigned to something not in top three this week
    off_prefs = db.session.execute(
        db.select(User)
        .join(Assignment)
        .join(Adventure)
        .where(
            Assignment.top_three.is_(False),
            Adventure.date >= start_of_current_week,
            Adventure.date <= end_of_current_week
        )
    ).scalars().all()
    for user in off_prefs:
        user.karma += 10
    current_app.logger.info(f" - Assigned 10 karma to players who did not got what they wanted: #{len(off_prefs)}: {[user.display_name for user in off_prefs]}")

    # +1 karma for playing in this week's adventures
    played = db.session.execute(
        db.select(User)
        .join(Assignment)
        .join(Adventure)
        .where(
            Assignment.appeared.is_(True),
            Adventure.date >= start_of_current_week,
            Adventure.date <= end_of_current_week
        )
    ).scalars().all()
    for user in played:
        user.karma += 1
    current_app.logger.info(f" - Assigned 1 karma to players who played: #{len(played)}: {[user.display_name for user in played]}")

    
    db.session.commit()