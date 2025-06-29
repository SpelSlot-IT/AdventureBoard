import sys
import os
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

CONFIG = config


import site
# add path to installed packages to PATH:
site.addsitedir('/mnt/web105/e0/90/517590/htdocs/.local/lib/python3.11/site-packages')
import webbrowser
from flask import Flask, jsonify, request, send_from_directory, url_for, render_template
from flask_apscheduler import APScheduler
import mysql.connector

from ranking_tools import *
from auth_tools import *
from timing_tools import *

# set configuration values
class Config:
    SCHEDULER_API_ENABLED = True

# Launch app
app = Flask(__name__)
ap_scheduler = APScheduler()
ap_scheduler.init_app(app)
ap_scheduler.start()

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
                is_story_adventure BOOLEAN DEFAULT FALSE,
                requested_room VARCHAR(4),
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

         # Create release variable
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS variable_storage  (
            id INT AUTO_INCREMENT PRIMARY KEY,
            release_state BOOLEAN DEFAULT FALSE
        );
        """)
        cursor.execute("INSERT IGNORE INTO variable_storage (id, release_state) VALUES (1, FALSE)")



        # Add default user 'test' if not exists
        cursor.execute("INSERT IGNORE INTO users (username, privilege_level) VALUES ('admin', 1)")

        connection.commit()
        cursor.close()
        connection.close()
    except mysql.connector.Error as err:
        print(f"Error initializing database: {err}")

# Global inits
init_db()

DB_CONFIG_WITH_DB = {**DB_CONFIG, 'database': DB_NAME}


# Basic provider routs
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
    """
    Returns a status message if DM is alive and reachable.
    """
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
    """
    Returns information about the current user.
    """
    token = request.cookies.get('access_token')
    if not token:
        return jsonify({ 'error': 'Not authenticated' }), 401
    return get_user_info_by_token(token)


@app.route('/api/users', methods=['GET'])
@token_required(1)
def get_all_users():
    """
    Returns a list of all users.
    """
    connection = mysql.connector.connect(**DB_CONFIG_WITH_DB)
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT id, username, karma FROM users")
    users = cursor.fetchall()
    
    connection.close()
    
    return jsonify(users)


@app.route('/api/adventures', methods=['GET'])
@token_required(lax=True)
def get_adventures(token_data):
    """
    Returns a list of all adventures in given timeframe. 
    If release_dt has passed, returns all players assigned to this adventures.
    """
    try:
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
        
        display_players = (token_data and token_data['privilege_level'] >= 1) or check_release() # Only show players if user is admin or release time has passed

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
            if display_players and row['player_id']:
                adventures[adv_id]['players'].append({
                    'id':       row['player_id'],
                    'username': row['username'],  
                })
                if token_data and token_data['privilege_level'] >= 1:
                    adventures[adv_id]['players'][-1]['karma'] = row['karma']
        return jsonify(list(adventures.values())), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/adventures', methods=['POST'])
@token_required()
def add_adventure(token_data):
    """
    Creates a new adventure.
    """
    data = request.get_json()
    title = data.get('title')
    description = data.get('short_description')
    creator_id = token_data['user_id']
    max_players = int(data.get('max_players'))
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    is_story_adventure = data.get('is_story_adventure') == 1
    requested_room = data.get('requested_room') 
    requested_players = data.get('requested_players')

    

    if not title or not description:
        return jsonify({'error': 'Missing title or short_description'}), 400

    connection = mysql.connector.connect(**DB_CONFIG_WITH_DB)
    cursor = connection.cursor()
    try:    
        validate_strings([title, description, max_players, start_date, end_date, requested_room])
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    cursor.execute(
        "INSERT INTO adventures (title, short_description, user_id, max_players, start_date, end_date, is_story_adventure, requested_room) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (title, description, creator_id, max_players, start_date, end_date, is_story_adventure, requested_room)
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

@app.route('/api/adventures', methods=['PUT'])
@token_required()
def edit_adventure(token_data, adventure_id):
    """
    Edits an existing adventure. Only the original creator may update.
    """
    data = request.get_json() or {}
    adventure_id = data.get('adventure_id')
    user_id = token_data['user_id']

    # Connect & verify ownership
    connection = mysql.connector.connect(**DB_CONFIG_WITH_DB)
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        "SELECT user_id FROM adventures WHERE id = %s",
        (adventure_id,)
    )
    row = cursor.fetchone()
    if not row:
        cursor.close()
        connection.close()
        return jsonify({'error': 'Adventure not found'}), 404
    creator_id = row['user_id']
    if token_data['privilege_level'] < 1 and creator_id != user_id:
        cursor.close()
        connection.close()
        return jsonify({'error': 'Unauthorized to edit this adventure'}), 401

    # Pull fields (only update those present)
    fields = {}
    if 'title' in data:
        fields['title'] = data['title']
    if 'short_description' in data:
        fields['short_description'] = data['short_description']
    if 'max_players' in data:
        fields['max_players'] = int(data['max_players'])
    if 'start_date' in data:
        fields['start_date'] = data['start_date']
    if 'end_date' in data:
        fields['end_date'] = data['end_date']
    if 'is_story_adventure' in data:
        fields['is_story_adventure'] = (data['is_story_adventure'] == 1)
    if 'requested_room' in data:
        fields['requested_room'] = data['requested_room']

    # Validate required strings if present
    try:
        validate_strings(
            [v for k, v in fields.items() if isinstance(v, str)]
        )
    except ValueError as e:
        cursor.close()
        connection.close()
        return jsonify({'error': str(e)}), 400

    # Build and execute UPDATE
    if fields:
        set_clause = ", ".join(f"{k} = %s" for k in fields)
        params = list(fields.values()) + [adventure_id]
        cursor.execute(
            f"UPDATE adventures SET {set_clause} WHERE id = %s",
            params
        )

    # Handle reassignment of players if provided
    mis_assignments = []
    if 'requested_players' in data:
        new_players = data['requested_players'] or []

        # Delete old assignments
        cursor.execute(
            "DELETE FROM adventure_assignments WHERE adventure_id = %s",
            (adventure_id,)
        )

        # Insert new assignments
        for pid in new_players:
            try:
                cursor.execute(
                    "INSERT INTO adventure_assignments "
                    "(adventure_id, user_id, appeared, top_three) "
                    "VALUES (%s, %s, 1, 1)",
                    (adventure_id, pid)
                )
            except mysql.connector.errors.IntegrityError:
                mis_assignments.append(pid)

    connection.commit()
    cursor.close()
    connection.close()

    if mis_assignments:
        return jsonify({
            'message': 'Adventure updated; some players could not be assigned.',
            'mis_assignments': mis_assignments
        }), 409

    return jsonify({'message': 'Adventure updated successfully'}), 200

@app.route('/api/adventures', methods=['DELETE'])
@token_required()
def delete_adventure(token_data):
    """
    Deletes an adventure with the given ID.
    """
    data = request.get_json()
    adventure_id = data.get('adventure_id')
    user_id = token_data['user_id']

    connection = mysql.connector.connect(**DB_CONFIG_WITH_DB)
    cursor = connection.cursor(dictionary=True)
    cursor.fetchone()

    cursor.execute("SELECTa.user_id FROM adventures WHERE id = %s", (adventure_id,))
    creator_id = cursor.fetchone()

    if token_data['privilege_level'] < 1 and creator_id != user_id:
        cursor.close()
        connection.close()
        return jsonify({'error': 'Unauthorized to delete this adventure'}), 401
    
    cursor.execute("DELETE FROM adventures WHERE id = %s", (adventure_id,))
    connection.close()
    return jsonify({'message': f'adventure {adventure_id} deleted successfully'}), 200

class UserNotFoundError(Exception):
    pass

def get_privilege_level(user_id, cursor):
    """
    Returns the privilege level of the user with the given ID.
    """
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
    """
    Returns the ID of the user with the given username.
    """
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
    """
    DEMO FUNCTION
    Registers a new user and returns their ID.
    """
    #TODO: REMOVE DEMO FUNCTION
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
@token_required()
def signups(token_data):
    """
    Makes a signup for a specific adventure. Deletes old ones a signup if it already exists.
    """
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
    """
    Returns all the signups (medals 1,2,3) of a specific user.
    """
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
def update_karma(_):
    connection = mysql.connector.connect(**DB_CONFIG_WITH_DB)
    reassign_karma(connection)

    return jsonify({'message': 'Karma updated successfully'}), 200

@app.route('/api/adventure-assignment', methods=['GET'])
def get_adventure_assignment():
    """
    Returns a list of players assigned to a single adventure.
    """
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


def assign_players_to_adventures():
    """
    Assigns when call all players to there respective adventures
    """
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

def check_release():
    """
    Returns true/false whether release date has passed.
    """
    connection = mysql.connector.connect(**DB_CONFIG_WITH_DB)
    cursor = connection.cursor()
    cursor.execute("SELECT release_state FROM variable_storage")
    release = cursor.fetchone()[0]
    cursor.close()
    connection.close()

    return release
     
a_d, a_h = CONFIG['TIMING']['assignment_day'].split("@")
r_d, r_h = CONFIG['TIMING']['assignment_day'].split("@")
re_d, re_h = CONFIG['TIMING']['assignment_day'].split("@")

@ap_scheduler.task('cron', id='make_assignments', day_of_week=a_d, hour=a_h)
def make_assignments():
    assign_players_to_adventures()

@ap_scheduler.task('cron', id='release_assignment', day_of_week=r_d, hour=r_h)
def release_assignments():
    connection = mysql.connector.connect(**DB_CONFIG_WITH_DB)
    cursor = connection.cursor()
    cursor.execute("UPDATE variable_storage SET release_state = TRUE WHERE id=1")
    connection.commit()
    cursor.close()
    connection.close()

@ap_scheduler.task('cron', id='reset_release', day_of_week=re_d, hour=re_h)
def reset_release():
    connection = mysql.connector.connect(**DB_CONFIG_WITH_DB)
    cursor = connection.cursor()
    cursor.execute("UPDATE variable_storage SET release_state = FALSE WHERE id=1")
    connection.commit()
    cursor.close()
    connection.close()

@app.route('/api/release', methods=['GET'])
def get_release():
    return jsonify({'release': check_release()})


@app.route('/api/adventure-assignment/<action>', methods=['PUT'])
@token_required(1)
def force_assign_players(_, action):
    """
    Allows admin to trigger assignment now.
    """
    if action == "release":
        release_assignments()
    elif action == "reset":
        reset_release()
    elif action == "assign":
        make_assignments()
    else:
        return jsonify({'error': f'Invalid action: {action}'}), 400
    
    return jsonify({'message': f'{action.capitalize()} action executed successfully'}), 200

@app.route('/api/adventure-assignment', methods=['PATCH'])
@token_required(1)
def update_adventure_assignment(_):
    """
    Updates a single player's assignment to new adventure
    """
    try:
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

    except Exception as e:
        return jsonify({'error': str(e)}), 400
        


if __name__ == '__main__':
    # will only be executed if run local
    app.secret_key = os.urandom(24)
    webbrowser.open("https://localhost:5000/")
    app.run(ssl_context='adhoc')
