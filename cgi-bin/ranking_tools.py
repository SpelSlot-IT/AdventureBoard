from collections import defaultdict

def assign_adventures_from_db(connection):
    cursor = connection.cursor(dictionary=True)

    # Step 1: Fetch data
    cursor.execute("SELECT id, karma FROM users")
    users = cursor.fetchall()

    cursor.execute("SELECT id, max_players FROM adventures")
    adventures = cursor.fetchall()

    cursor.execute("SELECT user_id FROM adventure_assignments")
    old_assignments = cursor.fetchall()

    cursor.execute("SELECT user_id, adventure_id, priority FROM signups")
    signups = cursor.fetchall()

    # Step 2: Organize data
    adventure_capacity = {adv['id']: adv['max_players'] for adv in adventures}
    assignments = defaultdict(list)

    user_signups = defaultdict(list)
    for signup in signups:
        user_signups[signup['user_id']].append((signup['priority'], signup['adventure_id']))
    for user_id in user_signups:
        user_signups[user_id].sort()

    sorted_users = sorted(users, key=lambda u: -u['karma'])
    placed_users = { assignment['user_id'] for assignment in old_assignments }

    # Step 3: Assign based on priorities
    for user in sorted_users:
        uid = user['id']
        if uid in placed_users or uid not in user_signups: 
            continue
        for _, adv_id in user_signups.get(uid, []):
            if len(assignments[adv_id]) < adventure_capacity[adv_id]:
                assignments[adv_id].append((uid,True))
                placed_users.add(uid)
                break

    # Step 4: Fill remaining free spots
    for user in sorted_users:
        uid = user['id']
        # Don't sign up players that are signed up for an adventure or already placed
        if uid in placed_users or uid not in user_signups: 
            continue
        for adv_id in adventure_capacity:
            if len(assignments[adv_id]) < adventure_capacity[adv_id]:
                assignments[adv_id].append((uid, False))
                placed_users.add(uid)
                break
        # Assign the rest to the waiting list
        else:
            # Only if the inner loop didn't place them
            assignments[-999].append((uid, False))

    cursor.close()
    return assignments

def reassign_karma(connection):
    cursor = connection.cursor()

    # +100 karma for creating an adventure
    cursor.execute("""
        UPDATE users
        SET karma = karma + 100
        WHERE id IN (
            SELECT DISTINCT user_id FROM adventures
        )
    """)

    # -100 karma for not appearing
    cursor.execute("""
        UPDATE users
        SET karma = karma - 100
        WHERE id IN (
            SELECT user_id FROM adventure_assignments WHERE appeared = FALSE
        )
    """)

    # +10 karma for being assigned to something not in top three
    cursor.execute("""
        UPDATE users
        SET karma = karma + 10
        WHERE id IN (
            SELECT user_id FROM adventure_assignments WHERE top_three = FALSE
        )
    """)

    # +1 karma for playing
    cursor.execute("""
        UPDATE users
        SET karma = karma + 1
        WHERE id IN (
            SELECT user_id FROM adventure_assignments WHERE appeared = TRUE
        )
    """)

    connection.commit()
    print("Karma reassigned successfully.")