from collections import defaultdict
from models import db, User, Adventure, AdventureAssignment, Signup

def assign_adventures_from_db():
    # Step 1: Fetch all required data
    users = db.session.query(User.id, User.karma).all()
    adventures = db.session.query(Adventure.id, Adventure.max_players).all()
    old_assignments = {row.user_id for row in db.session.query(AdventureAssignment.user_id).distinct()}
    signups = db.session.query(Signup.user_id, Signup.adventure_id, Signup.priority).all()

    # Step 2: Organize data
    adventure_capacity = {adv.id: adv.max_players for adv in adventures}
    assignments = defaultdict(list)

    # Map user_id to list of (priority, adventure_id), sorted by priority
    user_signups = defaultdict(list)
    for signup in signups:
        user_signups[signup.user_id].append((signup.priority, signup.adventure_id))
    for uid in user_signups:
        user_signups[uid].sort()  # Sort by priority (1, 2, 3)

    sorted_users = sorted(users, key=lambda u: -u.karma)
    placed_users = set(old_assignments)

    # Step 3: Try assigning based on priority signups
    for user in sorted_users:
        uid = user.id
        if uid in placed_users or uid not in user_signups:
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
    creators = db.session.query(User).join(Adventure).distinct()
    for user in creators:
        user.karma += 100

    # -100 karma for not appearing
    non_appearances = db.session.query(User).join(AdventureAssignment).filter(AdventureAssignment.appeared == False)
    for user in non_appearances:
        user.karma -= 100

    # +10 karma for being assigned to something not in top three
    off_prefs = db.session.query(User).join(AdventureAssignment).filter(AdventureAssignment.top_three == False)
    for user in off_prefs:
        user.karma += 10

    # +1 karma for playing
    played = db.session.query(User).join(AdventureAssignment).filter(AdventureAssignment.appeared == True)
    for user in played:
        user.karma += 1

    db.session.commit()