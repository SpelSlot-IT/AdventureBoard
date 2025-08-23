from .models import User, Adventure, AdventureAssignment, Signup
from .provider import db

def assign_adventures_from_db():
    # Step 1: Fetch all required data
    users = db.session.execute(db.select(User.id, User.karma).order_by(User.karma.desc())).scalars().all() # MAKE SORTED BY KARMA
    adventures = db.session.execute(db.select(Adventure.id, Adventure.max_players)).scalars().all()
    old_assignments = set(db.session.execute(db.select(AdventureAssignment.user_id).distinct()).scalars().all())
    signups = db.session.execute(db.select(Signup.user_id, Signup.adventure_id, Signup.priority)).scalars().all()

    placed_users = old_assignments
    # Step 3: Try assigning based on priority signups
    for user in users:
        uid = user.id
        if uid in placed_users or uid not in signups:
            continue
        for _, adv_id in user_signups[uid]:
            if len(assignments[adv_id]) < adventure_capacity.get(adv_id, 0):
                assignments[adv_id].append((uid, True))  # True = top three
                placed_users.add(uid)
                break

    # Step 4: Fill remaining users into free spots or waiting list
    for user in sorted_users:
        uid = user.id
        if uid in placed_users or uid not in user_signups:
            continue
        placed = False
        for adv_id, capacity in adventure_capacity.items():
            if len(assignments[adv_id]) < capacity:
                assignments[adv_id].append((uid, False))  # False = not top three
                placed_users.add(uid)
                placed = True
                break
        if not placed:
            # Place in waiting list (special adventure with id -999)
            assignments[-999].append((uid, False))

    return assignments

def reassign_karma():

    # +100 karma for creating an adventure
    creators = session.execute(
        select(User).join(Adventure).distinct()
    ).scalars().all()
    for user in creators:
        user.karma += 100

    # -100 karma for not appearing
    non_appearances = session.execute(
        select(User).join(AdventureAssignment).where(AdventureAssignment.appeared.is_(False))
    ).scalars().all()
    for user in non_appearances:
        user.karma -= 100

    # +10 karma for being assigned to something not in top three
    off_prefs = session.execute(
        select(User).join(AdventureAssignment).where(AdventureAssignment.top_three.is_(False))
    ).scalars().all()
    for user in off_prefs:
        user.karma += 10

    # +1 karma for playing
    played = session.execute(
        select(User).join(AdventureAssignment).where(AdventureAssignment.appeared.is_(True))
    ).scalars().all()
    for user in played:
        user.karma += 1

    db.session.commit()