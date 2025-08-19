from flask import jsonify
from datetime import datetime, timedelta, date
from flask import current_app

from models import *
from ranking_tools import *

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

def make_waiting_list():
    """
    Creates a placeholder 'waiting list' adventure with ID -999 if it doesn't exist.
    """
    next_wed = get_next_wednesday()
    
    try:
        # Check if the waiting list adventure already exists
        stmt = db.select(
            db.exists().where(Adventure.id == -999)
        )
        exists_query = db.session.execute(stmt).scalar()

        if not exists_query:
            waiting_list = Adventure(
                id=-999,
                title='waiting list',
                max_players=0,
                short_description='',
                start_date=next_wed,
                end_date=next_wed
            )
            db.session.add(waiting_list)
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e  # Or log the error / handle it differently if needed

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
    

def assign_players_to_adventures():
    """
    Assigns all players to their respective adventures for upcoming events.
    """

    try:
        # 1. Delete old assignments from past adventures
        # Build a select for old adventure IDs
        old_adventure_ids = db.select(Adventure.id).where(Adventure.end_date < date.today())

        # Use ORM-level delete via session
        stmt = db.delete(AdventureAssignment).where(AdventureAssignment.adventure_id.in_(old_adventure_ids))
        db.session.execute(stmt)
        # 2. Ensure the upcoming waiting list adventure exists
        make_waiting_list()

        # 3. Get new adventure assignments
        assignments = assign_adventures_from_db()

        # 4. Insert new assignments
        for adventure_id, player_entries in assignments.items():
            for user_id, top_three in player_entries:
                new_assignment = AdventureAssignment(
                    user_id=user_id,
                    adventure_id=adventure_id,
                    top_three=top_three,
                    appeared=True  # Assuming `appeared=True` by default
                )
                db.session.add(new_assignment)

        # 5. Commit changes
        db.session.commit()
        return jsonify({'message': 'Adventures assigned and saved successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    
def has_no_empty_params(rule):
    defaults = rule.defaults if rule.defaults is not None else ()
    arguments = rule.arguments if rule.arguments is not None else ()
    return len(defaults) >= len(arguments)

def get_google():
    return current_app.extensions["google_oauth"].client, current_app.extensions["google_oauth"].provider_cfg
