import sys
import os
from datetime import date, timedelta
import configparser
import re

# Database credentials
config = configparser.ConfigParser()
config.read('config.ini')

DB_CONFIG = {
    'host': config['DB']['host'],
    'user': config['DB']['user'],
    'password': config['DB']['password'],
}
DB_NAME = config['DB']['name']
LOCAL = bool(config['APP']['local'])
VERSION = config['VERSION']['version']


import site
# add path to installed packages to PATH:
site.addsitedir('/mnt/web105/e0/90/517590/htdocs/.local/lib/python3.11/site-packages')
import webbrowser
from flask import Flask, jsonify, request, send_from_directory, url_for, render_template
import mysql.connector

from ranking_tools import *
from auth_tools import *

# Launch app
app = Flask(__name__)


def init_db():
    try:
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
                privilege_level INT NOT NULL DEFAULT 0,
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
        cursor.execute("INSERT IGNORE INTO users (username, privilege_level) VALUES ('admin', 1)")

        connection.commit()
        cursor.close()
        connection.close()
    except mysql.connector.Error as err:
        print(f"Error initializing database: {err}")

init_db()

DB_CONFIG_WITH_DB = {**DB_CONFIG, 'database': DB_NAME}

@app.route('/')
def system_check():
    return send_from_directory('.', 'index.html')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('../static', path)

@app.route('/external/<path:path>')
def send_external(path):
    return send_from_directory('../external', path)

@app.route('/app')
def dashboard():
    return send_from_directory('../public', 'app.html')

@app.route('/help')
def send_help():
    return send_from_directory('../public', 'help.html')

@app.route('/login')
def send_login():
    return send_from_directory('../public', "login.html")

def validate_strings(strings):
    if not isinstance(strings, list):
        strings = [strings]
    for string in strings:
        string = str(string)
        if not re.match(r'^[a-zA-Z0-9_./\- !?]+$', string):
            raise ValueError("Strings may only contain letters, numbers, hyphens, spaces, question and exclamation marks, dots and underscores.")

@app.route('/login', methods=['POST'])
def login():
    # 1) extract & validate form inputs
    username = (request.form.get('username') or '').strip()
    password = request.form.get('password') or ''
    errors = {}
    if not username:
        errors['username'] = 'Username is required.'
    if not password:
        errors['password'] = 'Password is required.'
    if errors:
        return jsonify(success=False, errors=errors), 400

    # 2) attempt to look up user_id & privilege
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG_WITH_DB)
        cur = conn.cursor(dictionary=True)
        validate_strings(username)

        # may raise UserNotFoundError
        user_id = get_user_id_by_name(username, cur)
        privilege = get_privilege_level(user_id, cur)

        # 3) verify credentials
        return authenticate_user(username, user_id, privilege, password)
    
    except ValueError as e:
        return jsonify(
            success=False,
            errors={'username': str(e)}
        ), 400
    
    except UserNotFoundError:
        return jsonify(
            success=False,
            errors={'username': 'User not found.'}
        ), 404

    except mysql.connector.Error:
        return jsonify(
            success=False,
            errors={'database': 'Unable to reach database.'}
        ), 500

    finally:
        if conn:
            cur.close()
            conn.close()

@app.route('/logout', methods=['POST'])
def logout():
    resp = jsonify({'success': True})
    # overwrite the cookie with an expired one
    resp.set_cookie('access_token', '', expires=0, httponly=True, secure=True, samesite='Strict')
    return resp            


# --- API routs ---

@app.route('/api/alive', methods=['GET'])
def alive_check():
    try:
        connection = mysql.connector.connect(**DB_CONFIG_WITH_DB)
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        connection.close()
        return jsonify({'status': 'ok', 'db': 'reachable', 'version': VERSION}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'db': str(e), 'version': VERSION}), 500
    
@app.route('/api/me', methods=['GET'])
def me():
    token = request.cookies.get('access_token')
    if not token:
        return jsonify({ 'error': 'Not authenticated' }), 401
    return get_user_info_by_token(token)


@app.route('/api/users', methods=['GET'])
def get_all_users():
    connection = mysql.connector.connect(**DB_CONFIG_WITH_DB)
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT id, username, karma FROM users")
    users = cursor.fetchall()
    
    connection.close()
    
    return jsonify(users)

@app.route('/api/adventures', methods=['GET'])
def get_adventures():
    adventure_id = request.args.get('adventure_id')
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
    if adventure_id and adventure_id != 'null':
        conditions.append("a.id = %s")
        params.append(adventure_id)
    elif week_start and week_end:
        conditions.append("(a.start_date <= %s AND a.end_date >= %s)")
        params.extend([week_end, week_start])

    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)

    try:
        cursor.execute(base_query, tuple(params))
        rows = cursor.fetchall()
        connection.close()
    except mysql.connector.Error:
        return jsonify({"error": "Unable to reach database."}), 500

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
    return jsonify(list(adventures.values()))

@app.route('/api/adventures', methods=['POST'])
@token_required(get_token_data=True)
def add_adventure(token_data):
    data = request.get_json()
    title = data.get('title')
    description = data.get('short_description')
    creator_id = token_data['user_id']
    max_players = data.get('max_players')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    requested_players = data.get('requested_players')

    

    if not title or not description:
        return jsonify({'error': 'Missing title or short_description'}), 400

    connection = mysql.connector.connect(**DB_CONFIG_WITH_DB)
    cursor = connection.cursor()
    try:
        if  not isinstance(creator_id, int):
            try:  
                validate_strings(creator_id)
                creator_id = get_user_id_by_name(creator_id, cursor)
            except UserNotFoundError as e:
                return jsonify({'error': str(e)}), 404    
    
        validate_strings([title, description, max_players, start_date, end_date])
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    cursor.execute(
        "INSERT INTO adventures (title, short_description, user_id, max_players, start_date, end_date) VALUES (%s, %s, %s, %s, %s, %s)",
        (title, description, creator_id, max_players, start_date, end_date)
    )
    adventure_id = cursor.lastrowid
    mis_assignments = []
    for player_id in requested_players:
        try:
            cursor.execute(
                "INSERT INTO adventure_assignments (adventure_id, user_id, appeared, top_three) VALUES (%s, %s, 1, 1)", 
                (adventure_id, player_id)
            )
        except mysql.connector.errors.IntegrityError:
            mis_assignments.append(player_id)

    connection.commit()
    cursor.close()
    connection.close()
    if len(mis_assignments) > 0:
        return jsonify({'message': 'Adventure added, not all requested players could be assigned ', 'mis_assignments': mis_assignments}), 409 
    
    return jsonify({'message': 'Adventure added successfully', "adventure_id": adventure_id}), 201

class UserNotFoundError(Exception):
    pass

def get_privilege_level(user_id, cursor):
    if not isinstance(user_id, int):
        raise ValueError("User ID must be an integer.")
    cursor.execute("SELECT privilege_level FROM users WHERE id = %s", (user_id,))
    result = cursor.fetchone()
    if not result:
        raise UserNotFoundError(f"User with ID {user_id} not found.")
    if isinstance(result, dict):
        return result["privilege_level"]
    else:
        return result[0]

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
@token_required(get_token_data=True)
def signups(token_data):
    data = request.get_json()
    adventure_id = int(data.get('adventure_id'))
    priority = int(data.get('priority'))
    user_id = int(token_data['user_id'])

    if not adventure_id or not priority:
        return jsonify({'error': 'Missing adventure_id or priority'}), 400
    if not isinstance(adventure_id, int) or not isinstance(priority, int):
        return jsonify({'error': 'adventure_id and priority must be integers'}), 400

    connection = mysql.connector.connect(**DB_CONFIG_WITH_DB)
    cursor = connection.cursor()

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
    # TODO: Change this function to use the token
    username = request.args.get('user', '')
    connection = mysql.connector.connect(**DB_CONFIG_WITH_DB)
    cursor = connection.cursor(dictionary=True)
    try:
        validate_strings(username)
        user_id = get_user_id_by_name(username, cursor)
    except ValueError as e:
        return jsonify({'username': str(e)}), 400
    except UserNotFoundError as e:
        return jsonify({'error': str(e)}), 404

    cursor.execute("SELECT adventure_id, priority FROM signups WHERE user_id = %s", (user_id,))
    rows = cursor.fetchall()

    result = {row['adventure_id']: row['priority'] for row in rows}

    cursor.close()
    connection.close()
    return jsonify(result)


@app.route('/api/update-karma')
@token_required(1)
def update_karma():
    connection = mysql.connector.connect(**DB_CONFIG_WITH_DB)
    reassign_karma(connection)

    return jsonify({'message': 'Karma updated successfully'}), 200

@app.route('/api/adventure-assignment', methods=['GET'])
def get_adventure_assignment():
    adventure_id = int(request.args.get('adventure_id'))
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
@token_required(1)
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

    # Write only new assignments
    for adventure_id, entries in assignments.items():
        for user_id, top_three in entries:
            cursor.execute(
                "INSERT INTO adventure_assignments (user_id, adventure_id, top_three) VALUES (%s, %s, %s)",
                (user_id, adventure_id, top_three)
            )

    connection.commit()
    cursor.close()
    connection.close()

    return jsonify({'message': 'Adventures assigned and saved successfully'}), 200


@app.route('/api/adventure-assignment', methods=['PATCH'])
@token_required(1)
def update_adventure_assignment():
    data = request.get_json()
    player_id = int(data['player_id'])
    from_adventure_id = int(data['from_adventure_id'])
    to_adventure_id = int(data['to_adventure_id'])

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
    # will only be executed if run local
    app.secret_key = os.urandom(24)
    webbrowser.open("https://localhost:5000/")
    app.run(ssl_context='adhoc')
