from datetime import datetime, timedelta, date
from flask import current_app
from collections import defaultdict
from sqlalchemy.orm import joinedload
import calendar

from .models import *
from .email import notify_user, notifications_enabled

def is_admin(user):
    return user.is_authenticated and user.privilege_level >= 2

def get_next_wednesday(today=None):
    today = today or date.today()
    days_ahead = (2 - today.weekday() + 7) % 7  # 2 is Wednesday
    return today if days_ahead == 0 else today + timedelta(days=days_ahead)

def get_this_week(today=None):
    """
    Returns the start (Monday) and end (Sunday) of the this week.
    """
    today = today or date.today()
    # Find Monday of the current week
    start_of_current_week = today - timedelta(days=today.weekday())
    end_of_current_week = start_of_current_week + timedelta(days=6)

    return start_of_current_week, end_of_current_week

def get_upcoming_week(today=None):
    """
    Returns the start (Monday) and end (Sunday) of the upcoming week.
    - If today is Monday–Wednesday → return this week's Mon–Sun.
    - If today is Thursday–Sunday → return next week's Mon–Sun.
    """
    today = today or date.today()
    start_of_current_week, end_of_current_week = get_this_week(today)

    if today.weekday() <= 2:  # Mon(0), Tue(1), Wed(2)
        return start_of_current_week, end_of_current_week
    else:  # Thu–Sun
        start_of_next_week = start_of_current_week + timedelta(weeks=1)
        end_of_next_week = end_of_current_week + timedelta(weeks=1)
        return start_of_next_week, end_of_next_week
    
def get_this_month(today=None):
    """
    Returns the start (first day) and end (last day) of the current month.
    """
    today = today or date.today()
    # First day of this month
    start_of_month = today.replace(day=1)

    # Last day of this month
    last_day = calendar.monthrange(today.year, today.month)[1]
    end_of_month = today.replace(day=last_day)

    return start_of_month, end_of_month
    
def check_release(adventures):
    return (len(adventures) > 0 and adventures[-1].release_assignments)

def release_assignments(today=None):
    today = today or date.today()
    start_of_week, end_of_week = get_upcoming_week(today)
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
            f"Releasing assignments for adventures between {start_of_week} and {end_of_week}: #{len(adventures)}: {[adventure.title for adventure in adventures]}"
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
    
def reset_release(today=None):
    today = today or date.today()
    start_of_week, end_of_week = get_upcoming_week(today)
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
    

WAITING_LIST_NAME = "Waiting List" # unique name used to create the waiting-list adventure
def make_waiting_list(today=None) -> Adventure:
    """
    Ensure a waiting-list Adventure exists in the DB and return it.
    """
    today = today or date.today()
    next_wed = get_next_wednesday(today)

    # Try to find an existing waiting-list adventure
    existing_waiting_list = db.session.execute(
        db.select(Adventure).where(Adventure.is_waitinglist == 1)
    ).scalars().first()
    if existing_waiting_list and existing_waiting_list.date == next_wed:
        current_app.logger.info(f"Found existing waiting list adventure: {existing_waiting_list} on the {existing_waiting_list.date}, skipping creation.")
        return existing_waiting_list
    
    if existing_waiting_list:
        existing_waiting_list.is_waitinglist = 2 # Mark as "was waiting list"
        db.session.flush()
        current_app.logger.info(f"Found existing waiting list adventure: {existing_waiting_list}, marking as old and creating a new one.")

    # Create a waiting-list adventure and return it
    waiting_list = Adventure.create(
                title=WAITING_LIST_NAME,
                max_players=128,
                short_description='',
                date=next_wed,
                is_waitinglist=1, # Mark as waiting list
            )
    db.session.add(waiting_list)
    db.session.flush()
    return waiting_list
    

def assign_rooms_to_adventures(today=None):
    today = today or date.today()
    start_of_week, end_of_week = get_upcoming_week(today)
    possible_rooms = current_app.config.get("ROOMS", ["A", "B", "C", "D", "E", "Comp", "Hall"])
    try:
        this_weeks_adventures = (
            db.session.execute(
                db.select(Adventure)
                .filter(
                    Adventure.date >= start_of_week,
                    Adventure.date <= end_of_week,
                    Adventure.is_waitinglist == 0,  # Exclude waiting list
                )
                .order_by(
                    func.random(), # Shuffle
                )
            ).scalars().all()
        )
        assigned_adventures = []
        # First, handle personal rooms
        for adventure in this_weeks_adventures:
            if adventure.creator.personal_room is not None:
                adventure.requested_room = adventure.creator.personal_room
                assigned_adventures.append(adventure)
                try:
                    possible_rooms.remove(adventure.requested_room)
                except ValueError:
                    pass  # Room wasn’t in pool, ignore

        # Assign remaining rooms to adventures without personal rooms
        unassigned_adventures = [
            adv for adv in this_weeks_adventures if adv not in assigned_adventures
        ]
        for adventure in unassigned_adventures:
            if possible_rooms:
                adventure.requested_room = possible_rooms.pop()
            assigned_adventures.append(adventure)

        # Flush changes so they're tracked before logging
        db.session.flush()

        current_app.logger.info(
            f"Assigned rooms to adventures between {start_of_week} and {end_of_week}: "
            f"#{len(assigned_adventures)}: "
            f"{[{adv.title, adv.requested_room} for adv in assigned_adventures]}"
        )

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
    
def try_to_signup_user_for_adventure(taken_places, players_signedup_not_assigned, adventure, user, assignment_map, preference_place=None):
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
        assignment = Assignment(user=user, adventure=adventure, preference_place=preference_place)  # type: ignore
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


def assign_players_to_adventures(today=None):
    """
    Creates assignments for players that signed up this week. Working in 4 rounds:
    1. Signup all players that played last week, if they try to signup again for an ongoing adventure.
    2.
    3. Signup all remaining players ranked by their karma to the first available adventure they signed up for according to there priority.
    4. Signup all remaining players ranked by their karma to any available adventure. Sorted by random.
    5. Signup the rest of the players to the waiting list.
    This means that a player with more karma will always be preferred also if the adventure was a lower priority of his.
    """
    today = today or date.today()
    start_of_week, end_of_week = get_upcoming_week(today)
    start_of_month, end_of_month = get_this_month(today)
    current_app.logger.info(f" >--- Assigning players from waiting list for week {start_of_week} to {end_of_week} ---< ")
    # create a placeholder that will track how many places are already taken per adventure
    taken_places = defaultdict(int)
    assignment_map = defaultdict(list) # trace assignments in moa for human readability.


    # Query old assignments per adventure in the date window to check for taken places
    already_taken = (
        db.session.execute(
            db.select(
                Assignment.adventure_id,
                func.count(Assignment.user_id)
            )
            .join(Assignment.adventure)
            .filter(
                Adventure.date >= start_of_week,
                Adventure.date <= end_of_week,
            )
            .group_by(Assignment.adventure_id)
        ).all()
    )
    for adventure_id, count in already_taken:
        taken_places[adventure_id] = count

    # Subquery: get all assigned user ids this week
    assigned_ids_subq = (
        db.select(User.id)
        .join(User.assignments)
        .join(Assignment.adventure)
        .filter(Adventure.date >= start_of_week, Adventure.date <= end_of_week)
    )

    # Subquery: get number of signups per user this month
    monthly_signup_count = (
        db.select(func.count(Signup.id))
        .join(Signup.adventure)
        .filter(
            Signup.user_id == User.id,  # correlate to outer User
            Adventure.date >= start_of_month,
            Adventure.date <= end_of_month,
        )
        .correlate(User)
        .scalar_subquery()
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
                db.contains_eager(User.signups).contains_eager(Signup.adventure)
            )
            .order_by(
                User.karma.desc(),              # 3. Karma
                monthly_signup_count.desc(),    # 2. This month's signups number
                func.random(),                  # 1. Random                
            )
        )
        .unique()   # ensures deduplication when eager-loading collections
        .scalars()
        .all()
    )
    current_app.logger.info(f"Players signed up for the week {start_of_week} to {end_of_week}:   #{len(players_signedup_not_assigned)}: {[dict({user: user.signups}) for user in players_signedup_not_assigned]} ")
    MAX_PRIORITY = 3
    
    # -- First round of assigning players --
    # Assign all players that already played last week.
    round_ = []
    
    # go through priorities one by one
    for prio in range(1, MAX_PRIORITY + 1):
        for user in list(players_signedup_not_assigned):
            # For the current signup per player check if the player was already assigned for the predecessor of this adventure
            for signup in [s for s in user.signups if s.priority == prio]:
                pre = signup.adventure.predecessor
                if pre and any(a.user_id == user.id for a in pre.assignments):
                    adventure = signup.adventure
                    if try_to_signup_user_for_adventure(taken_places, players_signedup_not_assigned, adventure, user, assignment_map, preference_place=prio): 
                        round_.append(user.display_name)
                        break
    current_app.logger.info(f"- Players assigned in round 1: #{len(round_)}: {round_} => {dict(taken_places)}")

    # -- Second round of assigning players --
    # Assign all story players sorted by karma.
    round_ = []
    # go through priorities one by one
    for prio in range(1, MAX_PRIORITY + 1):
        for user in list(players_signedup_not_assigned):
            # For every player check if that player is story player, if not continue
            if not user.story_player:
                continue
            for signup in [s for s in user.signups if s.priority == prio]:
                adventure = signup.adventure
                if try_to_signup_user_for_adventure(taken_places, players_signedup_not_assigned, adventure, user, assignment_map, preference_place=prio): 
                    round_.append(user.display_name)
                    break
    current_app.logger.info(f"- Players assigned in round 2: #{len(round_)}: {round_} => {dict(taken_places)}")

    # -- Third round of assigning players --
    # Assign all players ranked by their karma to the first available adventure in there signups. 
    round_ = []
    for prio in range(1, MAX_PRIORITY + 1):
        for user in list(players_signedup_not_assigned):
            for signup in [s for s in user.signups if s.priority == prio]:
                adventure = signup.adventure
                if try_to_signup_user_for_adventure(taken_places, players_signedup_not_assigned, adventure, user, assignment_map, preference_place=prio): 
                    round_.append(user.display_name)
                    break
    current_app.logger.info(f"- Players assigned in round 3: #{len(round_)}: {round_} => {dict(taken_places)}")

    adventures_this_week = (
        db.session.execute(
            db.select(Adventure)
            .filter(Adventure.date >= start_of_week, Adventure.date <= end_of_week)
            .order_by(func.random())
            .distinct()
        )
        .scalars()
        .all()
    )

    # -- Fourth round of assigning players --
    # Assign all players ranked by their karma to the first available adventure independent of any signups. 
    round_ = []
    for user in list(players_signedup_not_assigned):
        for adventure in adventures_this_week:
            # Check if player still fits into the adventure
            if taken_places[adventure.id] < adventure.max_players:
                # Assigned outside top 3 preferences
                if try_to_signup_user_for_adventure(taken_places, players_signedup_not_assigned, adventure, user, assignment_map, preference_place=4): 
                    round_.append(user.display_name)
                    break
    current_app.logger.info(f"- Players assigned in round 4: #{len(round_)}: {round_} => {dict(taken_places)}")


    # -- Fifth round of assigning players --
    # Assign all players not assigned yet to the waiting list.
    round_ = []
    waiting_list = make_waiting_list()
    current_app.logger.info(f"Waiting-list adventure: {waiting_list}")
    for user in list(players_signedup_not_assigned):
        # For waiting list, no specific preference_place
        if not try_to_signup_user_for_adventure(taken_places, players_signedup_not_assigned, waiting_list, user, assignment_map, preference_place=None):
            current_app.logger.error(f"Failed to assign player {user.display_name} to waiting list!")
    current_app.logger.info(f"- Players assigned in round 5: #{len(round_)}: {round_} => {dict(taken_places)}")

    current_app.logger.info(f"Assigned players to adventures: {dict(assignment_map)}")
    db.session.commit()

def reassign_players_from_waiting_list(today=None):
    """
    Reassign players from the waiting list to newly opened slots in adventures this week.
    """
    today = today or date.today()
    start_of_week, end_of_week = get_upcoming_week(today)
    current_app.logger.info(f" <--- Reassigning players from waiting list for week {start_of_week} to {end_of_week} ---> ")

    # Get the waiting list adventure
    waiting_list = db.session.execute(
        db.select(Adventure).where(Adventure.is_waitinglist == 1)
    ).scalars().first()
    if not waiting_list:
        current_app.logger.info("No waiting list adventure found. Skipping reassignment.")
        return

    # Get all assignments on the waiting list
    waiting_list_assignments = db.session.execute(
        db.select(Assignment)
        .join(Assignment.user)
        .where(Assignment.adventure_id == waiting_list.id)
        .options(db.contains_eager(Assignment.user))
        .order_by(User.karma.desc())  # Prioritize by karma
    ).scalars().all()

    if not waiting_list_assignments:
        current_app.logger.info("No players on the waiting list. Skipping reassignment.")
        return

    # Track reassigned users for logging
    reassigned_users = []

    for assignment in waiting_list_assignments:
        user = assignment.user

        # Find adventures this week that the user signed up for and have available slots
        available_adventures = db.session.execute(
            db.select(Adventure)
            .outerjoin(Assignment, Assignment.adventure_id == Adventure.id)
            .join(Signup, (Signup.adventure_id == Adventure.id) & (Signup.user_id == user.id))
            .where(
                Adventure.date >= start_of_week,
                Adventure.date <= end_of_week,
                Adventure.is_waitinglist == 0,  # Exclude waiting list
            )
            .group_by(Adventure.id)
            .having(func.count(Assignment.user_id) < Adventure.max_players)
            .order_by(
                Signup.priority.asc(),  # 2. User's priority
                func.random()           # 1. Random
            ) 
        ).scalars().all()

        for adventure in available_adventures:
            # Assign to the first available adventure
            prio = db.session.execute(
                db.select(Signup.priority)
                .where(Signup.user_id == user.id, Signup.adventure_id == adventure.id)
            ).scalar()
            if prio is None:
                prio = 4  # outside top three
            new_assignment = Assignment(user=user, adventure=adventure, preference_place=prio)  # type: ignore
            db.session.add(new_assignment)

            # Remove from waiting list
            db.session.delete(assignment)

            reassigned_users.append((user.display_name, adventure.title))

    if reassigned_users:
        current_app.logger.info(f"Reassigned users from waiting list: {reassigned_users}")
        db.session.commit()


def has_no_empty_params(rule):
    defaults = rule.defaults if rule.defaults is not None else ()
    arguments = rule.arguments if rule.arguments is not None else ()
    return len(defaults) >= len(arguments)

def get_google():
    return current_app.extensions["google_oauth"].client, current_app.extensions["google_oauth"].provider_cfg


def reassign_karma(today=None):
    today = today or date.today()
    start_of_current_week, end_of_current_week = get_this_week(today)
    current_app.logger.info(f"Reassigning karma for week {start_of_current_week} to {end_of_current_week}")

    # DM: +500 karma for creating an adventure this week
    creators = db.session.execute(
        db.select(User)
        .join(Adventure)
        .where(Adventure.date >= start_of_current_week, Adventure.date <= end_of_current_week)
        .distinct()
    ).scalars().all()
    for user in creators:
        user.karma += 500
    current_app.logger.info(f" - Assigned +500 karma to DMs: #{len(creators)}: {[user.display_name for user in creators]}")

    # Not attending (non-waiting list): -500 karma
    non_appearances = db.session.execute(
        db.select(User)
        .join(Assignment)
        .join(Adventure)
        .where(
            Assignment.appeared.is_(False),
            Adventure.is_waitinglist == 0,  # Ignore waiting list
            Adventure.date >= start_of_current_week,
            Adventure.date <= end_of_current_week
        )
    ).scalars().all()
    for user in non_appearances:
        user.karma -= 500
    current_app.logger.info(f" - Assigned -500 karma to players who did not attend: #{len(non_appearances)}: {[user.display_name for user in non_appearances]}")

    # Waiting list attending: +200 karma
    waiting_attending = db.session.execute(
        db.select(User)
        .join(Assignment)
        .join(Adventure)
        .where(
            Adventure.is_waitinglist == 1,
            Assignment.appeared.is_(True),
            Adventure.date >= start_of_current_week,
            Adventure.date <= end_of_current_week
        )
        .distinct()
    ).scalars().all()
    for user in waiting_attending:
        user.karma += 200
    current_app.logger.info(f" - Assigned +200 karma to waiting-list attendees: #{len(waiting_attending)}: {[user.display_name for user in waiting_attending]}")

    # Waiting list not attending: +180 karma
    waiting_not_attending = db.session.execute(
        db.select(User)
        .join(Assignment)
        .join(Adventure)
        .where(
            Adventure.is_waitinglist == 1,
            Assignment.appeared.is_(False),
            Adventure.date >= start_of_current_week,
            Adventure.date <= end_of_current_week
        )
        .distinct()
    ).scalars().all()
    for user in waiting_not_attending:
        user.karma += 180
    current_app.logger.info(f" - Assigned +180 karma to waiting-list non-attendees: #{len(waiting_not_attending)}: {[user.display_name for user in waiting_not_attending]}")

    # Choice-based points for players who attended non-waiting-list sessions
    choice_points = {
        1: 100,
        2: 120,
        3: 140,
        4: 150,  # assigned outside top three
    }
    for prio, pts in choice_points.items():
        users_for_prio = db.session.execute(
            db.select(User)
            .join(Assignment)
            .join(Adventure)
            .where(
                Assignment.preference_place == prio,
                Assignment.appeared.is_(True),
                Adventure.is_waitinglist == 0,
                Adventure.date >= start_of_current_week,
                Adventure.date <= end_of_current_week,
            )
            .distinct()
        ).scalars().all()
        for user in users_for_prio:
            user.karma += pts
        current_app.logger.info(
            f" - Assigned +{pts} karma to attendees with choice {prio}: #{len(users_for_prio)}: {[user.display_name for user in users_for_prio]}"
        )
    db.session.commit()

def last_minute_cancel_punish(user_id: int):
    db.session.execute(
        db.update(User)
        .where(User.id == user_id)
        .values(karma=User.karma - 300)
    )