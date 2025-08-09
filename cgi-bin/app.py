import os
import site
# add path to installed packages to PATH:
site.addsitedir('/mnt/web105/e0/90/517590/htdocs/.local/lib/python3.11/site-packages')
import webbrowser
import requests
import json
from flask import Flask, jsonify, request, send_from_directory, url_for, render_template,  redirect
from flask_apscheduler import APScheduler
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import joinedload

from oauthlib.oauth2 import WebApplicationClient

from models import *
from util import *
#from api import api

# set configuration values
class Config:
    SCHEDULER_API_ENABLED = True

# --- Launch app --- 
app = Flask(__name__)
app.config.from_file("config.json", load=json.load)
config = app.config
app.secret_key = config["APP"]["secret_key"]


# --- Database setup ---
# Dynamically construct the SQLALCHEMY_DATABASE_URI from app.config['DB']
db_conf = app.config['DB']
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{db_conf['user']}:{db_conf['password']}@{db_conf['host']}/{db_conf['database']}"

db.init_app(app)
with app.app_context():
    db.create_all()

# --- APScheduler setup --- 
ap_scheduler = APScheduler()
ap_scheduler.init_app(app)
ap_scheduler.start()

# --- API setup ---
#api.init_app(app)

# --- User session management setup --- 
# https://flask-login.readthedocs.io/en/latest
login_manager = LoginManager()
login_manager.init_app(app)
# Flask-Login helper to retrieve a user from our db
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)
login_manager.anonymous_user = Anonymous
# OAuth2 client setup
def get_google_provider_cfg():
    return requests.get(config["GOOGLE"]["discovery_url"]).json()
client = WebApplicationClient(config["GOOGLE"]["client_id"])



# --- Basic provider routs ---
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

# --- Google OAuth2 provider routs ---
@app.route("/login")
def google_login():
    # Find out what URL to hit for Google login
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    # Use library to construct the request for login and provide
    # scopes that let you retrieve user's profile from Google
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url + "/callback",
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)


@app.route("/login/callback")
def google_callback():    
    try:
        # Get authorization code Google sent back to you
        code = request.args.get("code")

        # Find out what URL to hit to get tokens that allow you to ask for
        # things on behalf of a user
        google_provider_cfg = get_google_provider_cfg()
        token_endpoint = google_provider_cfg["token_endpoint"]

        # Prepare and send request to get tokens! Yay tokens!
        token_url, headers, body = client.prepare_token_request(
            token_endpoint,
            authorization_response=request.url,
            redirect_url=request.base_url,
            code=code,
        )
        token_response = requests.post(
            token_url,
            headers=headers,
            data=body,
            auth=(config["GOOGLE"]["client_id"], config["GOOGLE"]["client_secret"]),
        )

        # Parse the tokens!
        client.parse_request_body_response(json.dumps(token_response.json()))

        # Now that we have tokens (yay) let's find and hit URL
        # from Google that gives you user's profile information,
        # including their Google Profile Image and Email
        userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
        uri, headers, body = client.add_token(userinfo_endpoint)
        userinfo_response = requests.get(uri, headers=headers, data=body)

        # We want to make sure their email is verified.
        # The user authenticated with Google, authorized our
        # app, and now we've verified their email through Google!
        if userinfo_response.json().get("email_verified"):
            unique_id = userinfo_response.json()["sub"]
            users_email = userinfo_response.json()["email"]
            picture = userinfo_response.json()["picture"]
            users_name = userinfo_response.json()["given_name"]
        else:
            return "User email not available or not verified by Google.", 400

        # Create a user in our db with the information provided by Google
        # 1) See if Google’s user_id is already in our table
        existing = User.query.filter_by(google_id=unique_id).first()

        if existing:
            # They’re already in our DB — use that
            login_user(existing)
        else:
            # Not found → create and commit
            new_user = User(
                google_id=unique_id,
                name=users_name,
                email=users_email,
                profile_pic=picture)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user, fresh=True) 

        # Send user back to homepage
        return redirect(url_for("dashboard"))

    except Exception as e:
        return str(e)+f" - {unique_id} {users_name}", 500




@app.route('/logout', methods=['POST', 'GET'])
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))    


# --- API routs ---
@app.route('/api/alive', methods=['GET'])
def alive_check():
    """
    Returns a status message if DM is alive and reachable.
    """
    try:  
        db.session.execute(text('SELECT 1'))
        return jsonify({'status': 'ok', 'db': 'reachable', 'version': config["VERSION"]["version"]}), 200
    except SQLAlchemyError as e:
        return jsonify({'status': 'error', 'db': str(e), 'version': config["VERSION"]["version"]}), 500
    
@app.route('/api/me', methods=['GET'])
@login_required
def me():
    """
    Returns name and privilege level of the current user.
    """
    return jsonify({'username': current_user.display_name, 'privilege_level': current_user.privilege_level}), 200



@app.route('/api/users', methods=['GET'])
def get_all_users():
    """
    Returns a list of all users.
    """
    try:
        users = (
                db.session
                .query(User.id, User.display_name, User.karma)
                .all()
            )
        # Convert result tuples to list of dicts
        user_list = [
            {'id': u.id, 'username': u.display_name, 'karma': u.karma}
            for u in users
        ]
        return jsonify(user_list), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/adventures', methods=['GET'])
def get_adventures():
    """
    Returns a list of all adventures in given timeframe. 
    If release_dt has passed, returns all players assigned to this adventures.
    """
    try:
        adventure_id = request.args.get('adventure_id')
        week_start = request.args.get('week_start')
        week_end = request.args.get('week_end')

        query = db.session.query(Adventure).options(
            joinedload(Adventure.assignments).joinedload(AdventureAssignment.user)
        )

        if adventure_id and adventure_id != 'null':
            query = query.filter(Adventure.id == int(adventure_id))
        elif week_start and week_end:
            try:
                ws = datetime.fromisoformat(week_start)
                we = datetime.fromisoformat(week_end)
            except ValueError:
                return jsonify({"error": "Invalid date format. Use ISO 8601."}), 400
            query = query.filter(Adventure.start_date <= we, Adventure.end_date >= ws)

        adventures = query.all()
        display_players = current_user.privilege_level >= 1 or check_release()

        result = []
        for adv in adventures:
            adv_dict = {
                'id': adv.id,
                'title': adv.title,
                'short_description': adv.short_description,
                'user_id': adv.user_id,
                'max_players': adv.max_players,
                'start_date': adv.start_date.isoformat(),
                'end_date': adv.end_date.isoformat(),
                'players': []
            }

            if display_players:
                for assignment in adv.assignments:
                    user = assignment.user
                    if user:
                        player = {
                            'id': user.id,
                            'username': User.name
                        }
                        if current_user.privilege_level >= 1:
                            player['karma'] = user.karma
                        adv_dict['players'].append(player)

            result.append(adv_dict)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/adventures', methods=['POST'])
@login_required
def add_adventure():
    """
    Creates a new adventure.
    """
    data = request.get_json()
    title = data.get('title')
    description = data.get('short_description')
    creator_id = current_user.id
    max_players = data.get('max_players')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    is_story_adventure = data.get('is_story_adventure') == 1
    requested_room = data.get('requested_room')
    requested_players = data.get('requested_players', [])

    # Validate required fields
    if not title or not description:
        return jsonify({'error': 'Missing title or short_description'}), 400

    try:
        max_players = int(max_players)
        start_date = datetime.fromisoformat(start_date).date()
        end_date = datetime.fromisoformat(end_date).date()
        validate_strings([title, description, requested_room])  # your existing function
    except (ValueError, TypeError) as e:
        return jsonify({'error': f'Invalid input: {str(e)}'}), 400

    # Create and add the adventure
    try:
        new_adventure = Adventure(
            title=title,
            short_description=description,
            user_id=creator_id,
            max_players=max_players,
            start_date=start_date,
            end_date=end_date,
            is_story_adventure=is_story_adventure,
            requested_room=requested_room
        )
        db.session.add(new_adventure)
        db.session.flush()  # Assigns an ID to the new adventure without committing yet

        mis_assignments = []

        for player_id in requested_players:
            assignment = AdventureAssignment(
                adventure_id=new_adventure.id,
                user_id=player_id,
                appeared=True,
                top_three=True
            )
            db.session.add(assignment)
            try:
                db.session.flush()  # This will raise IntegrityError if user_id is invalid
            except IntegrityError:
                db.session.rollback()
                mis_assignments.append(player_id)

        db.session.commit()

        if mis_assignments:
            return jsonify({
                'message': 'Adventure added, but some players could not be assigned.',
                'adventure_id': new_adventure.id,
                'mis_assignments': mis_assignments
            }), 409

        return jsonify({
            'message': 'Adventure added successfully',
            'adventure_id': new_adventure.id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/adventures', methods=['PUT'])
@login_required
def edit_adventure(adventure_id):
    """
    Edits an existing adventure. Only the original creator or admin may update.
    """
    data = request.get_json() or {}
    user_id = current_user.id

    try:
        # Fetch adventure from DB
        adventure = Adventure.query.get(adventure_id)
        if not adventure:
            return jsonify({'error': 'Adventure not found'}), 404

        # Check ownership or admin
        if current_user.privilege_level < 1 and adventure.user_id != user_id:
            return jsonify({'error': 'Unauthorized to edit this adventure'}), 401

        # Update only provided fields
        if 'title' in data:
            adventure.title = data['title']
        if 'short_description' in data:
            adventure.short_description = data['short_description']
        if 'max_players' in data:
            adventure.max_players = int(data['max_players'])
        if 'start_date' in data:
            try:
                adventure.start_date = datetime.fromisoformat(data['start_date']).date()
            except ValueError:
                return jsonify({'error': 'Invalid start_date format'}), 400
        if 'end_date' in data:
            try:
                adventure.end_date = datetime.fromisoformat(data['end_date']).date()
            except ValueError:
                return jsonify({'error': 'Invalid end_date format'}), 400
        if 'is_story_adventure' in data:
            adventure.is_story_adventure = data['is_story_adventure'] == 1
        if 'requested_room' in data:
            adventure.requested_room = data['requested_room']

        # Validate any strings
        try:
            validate_strings([
                val for key, val in data.items()
                if isinstance(val, str) and key in ['title', 'short_description', 'requested_room']
            ])
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

        mis_assignments = []

        # Reassign players if requested
        if 'requested_players' in data:
            new_player_ids = data.get('requested_players', [])

            # Clear current assignments
            AdventureAssignment.query.filter_by(adventure_id=adventure_id).delete()

            # Add new assignments
            for pid in new_player_ids:
                try:
                    assignment = AdventureAssignment(
                        adventure_id=adventure_id,
                        user_id=pid,
                        appeared=True,
                        top_three=True
                    )
                    db.session.add(assignment)
                    db.session.flush()  # Trigger integrity check early
                except IntegrityError:
                    db.session.rollback()
                    mis_assignments.append(pid)

        # Commit all changes
        db.session.commit()

        if mis_assignments:
            return jsonify({
                'message': 'Adventure updated; some players could not be assigned.',
                'mis_assignments': mis_assignments
            }), 409

        return jsonify({'message': 'Adventure updated successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/adventures', methods=['DELETE'])
@login_required
def delete_adventure():
    """
    Deletes an adventure with the given ID. Only creator or admin can delete.
    """
    data = request.get_json()
    adventure_id = data.get('adventure_id')
    user_id = current_user.id

    if not adventure_id:
        return jsonify({'error': 'Missing adventure_id'}), 400

    try:
        adventure = Adventure.query.get(adventure_id)
        if not adventure:
            return jsonify({'error': 'Adventure not found'}), 404

        # Check permission: admin or creator
        if current_user.privilege_level < 1 and adventure.user_id != user_id:
            return jsonify({'error': 'Unauthorized to delete this adventure'}), 401

        db.session.delete(adventure)
        db.session.commit()

        return jsonify({'message': f'Adventure {adventure_id} deleted successfully'}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/signups', methods=['POST'])
@login_required
def signups():
    """
    Makes a signup for a specific adventure. Deletes old ones if a signup already exists.
    Acts as a toggle: if the same signup exists, it removes it.
    """
    data = request.get_json()
    try:
        adventure_id = int(data.get('adventure_id'))
        priority = int(data.get('priority'))
        user_id = int(current_user.id)
    except (TypeError, ValueError):
        return jsonify({'error': 'adventure_id and priority must be integers'}), 400

    if not adventure_id or not priority:
        return jsonify({'error': 'Missing adventure_id or priority'}), 400

    try:
        # Check if exact same signup already exists (toggle behavior)
        existing_signup = Signup.query.filter_by(
            user_id=user_id,
            adventure_id=adventure_id,
            priority=priority
        ).first()

        if existing_signup:
            db.session.delete(existing_signup)
            message = 'Signup removed'
        else:
            # Remove any existing signup with same priority (regardless of adventure)
            Signup.query.filter_by(user_id=user_id, priority=priority).delete()

            # Remove any existing signup for same adventure (regardless of priority)
            Signup.query.filter_by(user_id=user_id, adventure_id=adventure_id).delete()

            # Add new signup
            new_signup = Signup(user_id=user_id, adventure_id=adventure_id, priority=priority)
            db.session.add(new_signup)
            message = 'Signup registered'

        db.session.commit()
        return jsonify({'message': message}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    
@app.route('/api/signups', methods=['GET'])
@login_required
def get_user_signups():
    """
    Returns all the signups (priority medals 1, 2, 3) of the authenticated user.
    """
    if current_user.privilege_level < 0:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        user_id = current_user.id
        signups = Signup.query.filter_by(user_id=user_id).all()

        result = {s.adventure_id: s.priority for s in signups}
        return jsonify(result), 200

    except SQLAlchemyError as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/update-karma')
@login_required
def update_karma():
    if current_user.privilege_level < 1:
        return jsonify({'error': 'Unauthorized'}), 401
    reassign_karma()

    return jsonify({'message': 'Karma updated successfully'}), 200

@app.route('/api/adventure-assignment', methods=['GET'])
def get_adventure_assignment():
    """
    Returns a list of players assigned to a single adventure.
    """
    try:
        adventure_id = request.args.get('adventure_id', type=int)
        if not adventure_id:
            return jsonify({'error': 'Adventure ID is required'}), 400

        assignments = AdventureAssignment.query.filter_by(adventure_id=adventure_id).join(User).all()

        players = [
            {
                'id': assignment.user.id,
                'username': assignment.User.name,
                'karma': assignment.user.karma
            }
            for assignment in assignments if assignment.user
        ]

        return jsonify(players), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

a_d, a_h = config['TIMING']['assignment_day'].split("@")
r_d, r_h = config['TIMING']['assignment_day'].split("@")
re_d, re_h = config['TIMING']['assignment_day'].split("@")


@ap_scheduler.task('cron', id='make_assignments', day_of_week=a_d, hour=a_h)
def make_assignments():
    assign_players_to_adventures()

@ap_scheduler.task('cron', id='release_assignment', day_of_week=r_d, hour=r_h)
def release_assignments():
    try:
        variable = db.session.query(VariableStorage).filter_by(id=1).first()
        variable.release_state = True
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@ap_scheduler.task('cron', id='reset_release', day_of_week=re_d, hour=re_h)
def reset_release():
    try:
        variable = db.session.query(VariableStorage).filter_by(id=1).first()
        variable.release_state = False
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/release', methods=['GET'])
def get_release():
    return jsonify({'release': check_release()})


@app.route('/api/adventure-assignment/<action>', methods=['PUT'])
@login_required
def force_assign_players(_, action):
    """
    Allows admin to trigger assignment now.
    """
    if current_user.privilege_level < 1:
        return jsonify({'error': 'Unauthorized'}), 401
    
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
@login_required
def update_adventure_assignment(_):
    """
    Updates a single player's assignment to a new adventure.
    """
    if current_user.privilege_level < 1:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        player_id = int(data['player_id'])
        from_adventure_id = int(data['from_adventure_id'])
        to_adventure_id = int(data['to_adventure_id'])

        assignment = db.session.query(AdventureAssignment).filter_by(
            user_id=player_id,
            adventure_id=from_adventure_id
        ).first()

        if not assignment:
            return jsonify({'error': 'Assignment not found'}), 404

        assignment.adventure_id = to_adventure_id
        db.session.commit()

        return jsonify({'message': 'Assignment updated successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
        


if __name__ == '__main__':
    # will only be executed if run local
    app.secret_key = os.urandom(24)
    webbrowser.open("https://localhost:5000/")
    app.run(ssl_context='adhoc')
