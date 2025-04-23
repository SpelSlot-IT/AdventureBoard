from flask import Flask, jsonify, request, send_from_directory
import mysql.connector
from datetime import date, timedelta
import webbrowser
import os
from ranking_tools import *


app = Flask(__name__)

# Database credentials
DB_CONFIG = {
    'host': 'localhost',
    'user': 'Test',
    'password': 'test',
}
DB_NAME = 'adventure_db'

def init_db():
    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor()

    # Create database
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
    connection.database = DB_NAME

    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            karma INT DEFAULT 1000
        )
    """)

    # Create adventures table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS adventures (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            short_description TEXT NOT NULL,
            user_id INT,
            max_players INT DEFAULT 5 NOT NULL,
            start_date DATE NOT NULL,
            end_date   DATE NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)


    # Create assignments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS adventure_assignments (
            user_id INT,
            adventure_id INT,
            appeared BOOLEAN DEFAULT TRUE,
            top_three BOOLEAN DEFAULT FALSE,
            PRIMARY KEY (user_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (adventure_id) REFERENCES adventures(id)
        )
    """)    

    # Create signups table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS signups (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        adventure_id INT NOT NULL,
        priority INT NOT NULL,
        UNIQUE(user_id, adventure_id),
        UNIQUE(user_id, priority),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (adventure_id) REFERENCES adventures(id)
    );
    """)



    # Add default user 'test' if not exists
    cursor.execute("INSERT IGNORE INTO users (username) VALUES ('test')")

    connection.commit()
    cursor.close()
    connection.close()
    print("Database initialized.")

init_db()

DB_CONFIG_WITH_DB = {**DB_CONFIG, 'database': DB_NAME}

@app.route('/')
def serve_html():
    return send_from_directory('.', 'index.html')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/public/<path:path>')
def send_public(path):
    return send_from_directory('public', path)

@app.route('/api/users', methods=['GET'])
def get_all_users():
    connection = mysql.connector.connect(**DB_CONFIG_WITH_DB)
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT id, username, karma FROM users")
    users = cursor.fetchall()
    
    connection.close()
    
    return jsonify(users)

@app.route('/api/adventures', methods=['GET'])
def get_adventures_with_players():
    # Parse optional week_start from query string
    week_start = request.args.get('week_start')
    week_end = request.args.get('week_end')

    connection = mysql.connector.connect(**DB_CONFIG_WITH_DB)
    cursor = connection.cursor(dictionary=True)

    base_query = """
        SELECT a.id AS adventure_id, a.title, a.short_description, a.user_id, a.max_players,
            a.start_date, a.end_date,
            u.id AS player_id, u.username, u.karma
        FROM adventures a
        LEFT JOIN adventure_assignments aa ON a.id = aa.adventure_id
        LEFT JOIN users u ON aa.user_id = u.id
    """

    conditions = []
    params = []

    if week_start and week_end:
        conditions.append("(a.start_date <= %s AND a.end_date >= %s)")
        params.extend([week_end, week_start])

    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)

    cursor.execute(base_query, tuple(params))
    rows = cursor.fetchall()
    connection.close()

    # Group players by adventure
    adventures = {}
    for row in rows:
        adv_id = row['adventure_id']
        if adv_id not in adventures:
            adventures[adv_id] = {
                'id':                adv_id,
                'title':             row['title'],
                'short_description': row['short_description'],
                'user_id':           row['user_id'],
                'max_players':       row['max_players'],
                'start_date':        row['start_date'].isoformat(),
                'end_date':          row['end_date'].isoformat(),
                'players':           []
            }
        if row['player_id']:
            adventures[adv_id]['players'].append({
                'id':       row['player_id'],
                'username': row['username'],
                'karma':    row['karma']
            })
    print(list(adventures.values()))
    return jsonify(list(adventures.values()))

@app.route('/api/adventures', methods=['POST'])
def add_adventure():
    data = request.get_json()
    title = data.get('title')
    description = data.get('short_description')
    creator_id = data.get('creator_id')
    max_players = data.get('max_players')
    start_date = data.get('start_date')
    end_date = data.get('end_date')

    

    if not title or not description:
        return jsonify({'error': 'Missing title or short_description'}), 400

    connection = mysql.connector.connect(**DB_CONFIG_WITH_DB)
    cursor = connection.cursor()
    if  not isinstance(creator_id, int):
        creator_id = get_user_id_by_name(creator_id, cursor)
    cursor.execute(
        "INSERT INTO adventures (title, short_description, user_id, max_players, start_date, end_date) VALUES (%s, %s, %s, %s, %s, %s)",
        (title, description, creator_id, max_players, start_date, end_date)
    )
    connection.commit()
    cursor.close()
    connection.close()

    return jsonify({'message': 'Adventure added successfully'}), 201

class UserNotFoundError(Exception):
    pass

def get_user_id_by_name(username, cursor):
    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
    result = cursor.fetchone()
    if not result:
        raise UserNotFoundError(f"User '{username}' not found.")
    if isinstance(result, dict):
        return result["id"]
    else:
        return result[0]
    
@app.route('/api/register', methods=['POST'])
def register_new_user():
    data = request.get_json()
    username = data.get('username')

    if not username:
        return jsonify({'error': 'Username is required'}), 400

    connection = mysql.connector.connect(**DB_CONFIG_WITH_DB)
    cursor = connection.cursor()

    # Check if the username already exists
    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
    existing_user = cursor.fetchone()

    if existing_user:
        return jsonify({'error': 'Username already exists'}), 409

    # Insert new user into the 'users' table
    cursor.execute("INSERT INTO users (username) VALUES (%s)", (username,))
    connection.commit()

    # Fetch the ID of the newly registered user
    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
    new_user = cursor.fetchone()

    cursor.close()
    connection.close()

    return jsonify({'message': f'User {username} registered successfully.', 'user_id': new_user[0]}), 201

@app.route('/api/signups', methods=['POST'])
def signup():
    data = request.get_json()
    adventure_id = data.get('adventure_id')
    priority = data.get('priority')
    username = data.get('user')

    connection = mysql.connector.connect(**DB_CONFIG_WITH_DB)
    cursor = connection.cursor()
    try:
        user_id = get_user_id_by_name(username, cursor)
    except UserNotFoundError as e:
        return jsonify({'error': str(e)}), 405
    
    # Check if signup with same priority and adventure already exists (toggle off)
    cursor.execute("""
        SELECT id FROM signups
        WHERE user_id = %s AND adventure_id = %s AND priority = %s
    """, (user_id, adventure_id, priority))
    existing = cursor.fetchone()

    if existing:
        # Toggle off (remove the signup)
        cursor.execute("""
            DELETE FROM signups
            WHERE user_id = %s AND adventure_id = %s AND priority = %s
        """, (user_id, adventure_id, priority))
        message = 'Signup removed'
    else:
        # Remove any existing signup with same priority
        cursor.execute("""
            DELETE FROM signups
            WHERE user_id = %s AND priority = %s
        """, (user_id, priority))

        # Remove any existing signup for the same adventure
        cursor.execute("""
            DELETE FROM signups
            WHERE user_id = %s AND adventure_id = %s
        """, (user_id, adventure_id))

        # Insert new signup
        cursor.execute("""
            INSERT INTO signups (user_id, adventure_id, priority)
            VALUES (%s, %s, %s)
        """, (user_id, adventure_id, priority))
        message = 'Signup registered'

    connection.commit()
    cursor.close()
    connection.close()

    return jsonify({'message': message}), 200

@app.route('/api/signups', methods=['GET'])
def get_user_signups():
    username = request.args.get('user', 'test')
    connection = mysql.connector.connect(**DB_CONFIG_WITH_DB)
    cursor = connection.cursor(dictionary=True)
    try:
        user_id = get_user_id_by_name(username, cursor)
    except UserNotFoundError as e:
        return jsonify({'error': str(e)}), 404

    cursor.execute("SELECT adventure_id, priority FROM signups WHERE user_id = %s", (user_id,))
    rows = cursor.fetchall()

    result = {row['adventure_id']: row['priority'] for row in rows}

    cursor.close()
    connection.close()
    return jsonify(result)

@app.route('/api/update-karma')
def update_karma():
    connection = mysql.connector.connect(**DB_CONFIG_WITH_DB)
    reassign_karma(connection)

    return jsonify({'message': 'Karma updated successfully'}), 200

@app.route('/api/adventure-assignment', methods=['GET'])
def get_adventure_assignment():
    adventure_id = request.args.get('adventure_id')
    if not adventure_id:
        return jsonify({'error': 'Adventure ID is required'}), 400
    
    connection = mysql.connector.connect(**DB_CONFIG_WITH_DB)
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT users.id, users.username, users.karma
        FROM users
        JOIN adventure_assignments ON users.id = adventure_assignments.user_id
        WHERE adventure_assignments.adventure_id = %s
    """, (adventure_id,))
    players = cursor.fetchall()
    
    cursor.close()
    connection.close()
    return jsonify(players)

def get_next_wednesday():
    today = date.today()
    days_ahead = (2 - today.weekday() + 7) % 7  # 2 is Wednesday
    return today if days_ahead == 0 else today + timedelta(days=days_ahead)

def make_waiting_list(cursor):
    next_wed = get_next_wednesday()
    next_wed_str = next_wed.strftime('%Y-%m-%d')

    cursor.execute("""
        INSERT INTO adventures (id, title, max_players, short_description, start_date, end_date)
        SELECT -999, 'waiting list', 0, '', %s, %s
        WHERE NOT EXISTS (
            SELECT 1 FROM adventures WHERE id = -999
        )
    """, (next_wed_str, next_wed_str))


@app.route('/api/adventure-assignment', methods=['PUT'])
def assign_players_to_adventures():
    connection = mysql.connector.connect(**DB_CONFIG_WITH_DB)
    cursor = connection.cursor()

    # Clean old assignments (from past adventures)
    cursor.execute("""
        DELETE aa FROM adventure_assignments aa
        JOIN adventures a ON aa.adventure_id = a.id
        WHERE a.end_date < CURDATE()
    """)

    # Ensure upcoming waiting list exists
    make_waiting_list(cursor)

    # Get new assignments only
    assignments = assign_adventures_from_db(connection)

    print(f"New Assignments: {assignments}")

    # Write only new assignments
    for user_id, adventure_id, top_three in assignments:
        cursor.execute(
            "INSERT INTO adventure_assignments (user_id, adventure_id, top_three) VALUES (%s, %s, %s)",
            (user_id, adventure_id, top_three)
        )

    connection.commit()
    cursor.close()
    connection.close()

    return jsonify({'message': 'Adventures assigned and saved successfully'}), 200


@app.route('/api/adventure-assignment', methods=['PATCH'])
def update_adventure_assignment():
    data = request.get_json()
    player_id = data['player_id']
    from_adventure_id = data['from_adventure_id']
    to_adventure_id = data['to_adventure_id']

    connection = mysql.connector.connect(**DB_CONFIG_WITH_DB)
    cursor = connection.cursor()

    # Update the database to move the player to the new adventure
    cursor.execute("""
        UPDATE adventure_assignments
        SET adventure_id = %s
        WHERE user_id = %s AND adventure_id = %s
    """, (to_adventure_id, player_id, from_adventure_id))
    connection.commit()

    cursor.close()
    connection.close()
    return jsonify({'message': 'Assignment updated successfully'}), 200



if __name__ == '__main__':
    app.secret_key = os.urandom(24)
    webbrowser.open("https://localhost:5000/")
    app.run(ssl_context='adhoc')
