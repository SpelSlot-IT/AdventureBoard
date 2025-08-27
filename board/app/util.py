from flask import jsonify
from datetime import datetime, timedelta, date
from flask import current_app
from collections import defaultdict
from typing import Dict, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

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
                start_date=next_wed,
                end_date=next_wed
            )
    db.session.add(waiting_list)
    db.session.flush()  # ensure waiting.id is populated
    return waiting_list.id
    
def assign_adventures_from_db(top_n: int = 3) -> Dict[int, List[Tuple[int, bool]]]:
    """
    Build an assignment plan (in memory) and return a mapping:
        { adventure_id: [(user_id, is_top_n), ...], WAITING_LIST_KEY: [...] }

    Behavior:
      - iterate users in descending karma order
      - try to place users into their highest-priority signup with remaining capacity
      - then fill remaining users into any adventure with free spots
      - leftover users go to WAITING_LIST_ID (in-memory); caller can map this to a real DB id
    """
    # Load users (by karma desc)
    users = db.session.execute(db.select(User).order_by(User.karma.desc())).scalars().all()

    # Load adventures & capacities
    adventures = db.session.execute(db.select(Adventure)).scalars().all()
    adventure_capacity = {adv.id: (adv.max_players or 0) for adv in adventures}

    # Existing assignments: to avoid re-assigning same users and to reflect current occupancy
    existing_pairs = db.session.execute(
        db.select(AdventureAssignment.user_id, AdventureAssignment.adventure_id)
    ).all()
    already_assigned_user_ids = {user_id for user_id, _ in existing_pairs}

    # Build initial assignments map from existing DB rows (so capacity is respected)
    assignments = defaultdict(list)
    for user_id, adv_id in existing_pairs:
        assignments[adv_id].append((user_id, False))

    # Load signups grouped by user, ordered by priority ascending (1 = highest)
    signups = db.session.execute(
        db.select(Signup).order_by(Signup.user_id, Signup.priority)
    ).scalars().all()
    signups_by_user = defaultdict(list)
    for s in signups:
        signups_by_user[s.user_id].append((s.priority, s.adventure_id))

    # Ensure each user's signup list is sorted by priority
    for uid in signups_by_user:
        signups_by_user[uid].sort(key=lambda x: x[0])

    placed_users = set(already_assigned_user_ids)

    # Phase 1: place users into their top signups (in karma order)
    for user in users:
        uid = user.id
        if uid in placed_users:
            continue

        for priority, adv_id in signups_by_user.get(uid, []):
            cap = adventure_capacity.get(adv_id, 0)
            if len(assignments[adv_id]) < cap:
                is_top = (priority <= top_n)
                assignments[adv_id].append((uid, bool(is_top)))
                placed_users.add(uid)
                break  # placed for this user

    # Phase 2: fill remaining users into any adventure with free space
    for user in users:
        uid = user.id
        if uid in placed_users:
            continue

        placed = False
        # deterministic order: iterate adventures by id (change if you want popularity/order)
        for adv_id, cap in adventure_capacity.items():
            if len(assignments[adv_id]) < cap:
                assignments[adv_id].append((uid, False))
                placed_users.add(uid)
                placed = True
                break

        if not placed:
            # No space anywhere -> waiting list (in-memory)
            assignments[WAITING_LIST_ID].append((uid, False))

    return dict(assignments)


def assign_players_to_adventures():
    """
    Top-level: deletes old assignments, ensures waiting-list Adventure exists,
    builds a plan and persists new AdventureAssignment rows (skips duplicates).
    """
    try:
        with db.session.begin():
            # 1) Delete AdventureAssignment rows for adventures that ended in the past
            old_advs_sq = db.select(Adventure.id).where(Adventure.end_date < date.today()).scalar_subquery()
            del_stmt = db.delete(AdventureAssignment).where(AdventureAssignment.adventure_id.in_(old_advs_sq))
            db.session.execute(del_stmt)

            # 2) Ensure waiting list adventure exists and get its real id
            waiting_adv_id = make_waiting_list()

            # 3) Build the in-memory plan
            plan = assign_adventures_from_db() or {}

            # 4) Map the in-memory waiting-list key to the real waiting list adventure id for persistence
            if WAITING_LIST_ID in plan:
                plan.setdefault(waiting_adv_id, []).extend(plan.pop(WAITING_LIST_ID))

            # 5) Load existing DB pairs again to skip duplicates safely
            existing_q = db.select(AdventureAssignment.user_id, AdventureAssignment.adventure_id)
            existing_pairs = { (u, a) for u, a in db.session.execute(existing_q).all() }

            # 6) Prepare new AdventureAssignment model instances (skip duplicates)
            new_rows = []
            for adv_id, entries in plan.items():
                # defensive: skip invalid adv_id
                if adv_id is None:
                    continue
                for user_id, top_three in entries:
                    key = (int(user_id), int(adv_id))
                    if key in existing_pairs:
                        continue
                    aa = AdventureAssignment(
                        user_id=key[0],
                        adventure_id=key[1],
                        top_three=bool(top_three),
                        appeared=True,
                    )
                    new_rows.append(aa)
                    existing_pairs.add(key)

            # 7) Persist new rows efficiently
            if new_rows:
                db.session.bulk_save_objects(new_rows)

        # transaction committed
        return jsonify({"message": "Adventures assigned and saved", "inserted": len(new_rows)}), 200

    except IntegrityError as ie:
        # likely unique constraint due to race — rollback and report
        db.session.rollback()
        current_app.logger.exception("IntegrityError in assign_players_to_adventures")
        return jsonify({"error": "database integrity error", "details": str(ie)}), 500

    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error in assign_players_to_adventures")
        return jsonify({"error": str(exc)}), 500

    
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
