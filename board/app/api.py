from flask_smorest import Blueprint, abort
from marshmallow import validates_schema, ValidationError
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask.views import MethodView
from flask import ( 
    request, 
    current_app, 
    url_for, 
    redirect,
    jsonify, 
    g 
    )
from sqlalchemy import text, delete
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import json
import requests

from .models import db, User, Adventure, Assignment
from .util import *
from .provider import ma, ap_scheduler


blp_utils = Blueprint("utils", "utils", url_prefix="/api/",
               description="Utils API: Everything that does not fit in the other categories.")
blp_adventures = Blueprint("adventures", "adventures", url_prefix="/api/adventures",
               description="Adventures API: Everything related to adventures. The big boxes with adventure names and descriptions.")
blp_assignments = Blueprint("player-assignment", "player-assignment", url_prefix="/api/player-assignments",
               description="Assignment API: Everything related to the assignments of players to adventures. The boxes with player names.")
blp_signups = Blueprint("signups", "signups", url_prefix="/api/signups",
               description="Signups API: Everything related to the signups of users. Priority medals 1, 2, 3")
blp_users = Blueprint("users", "users", url_prefix="/api/users",
               description="Users API: Everything related to the users.")

api_blueprints = [blp_utils, blp_users, blp_adventures, blp_assignments, blp_signups]

# ----------------------- Schemas ---------------------------------

class AliveSchema(ma.Schema):
    status = ma.String()
    db = ma.String()
    version = ma.String()

class RedirectSchema(ma.Schema):
    redirect_url = ma.Url(required=True)

class MessageSchema(ma.Schema):
    message = ma.String(required=True)

class AdminActionSchema(ma.Schema):
    action = ma.String(required=True)
    date = ma.Date(allow_none=True, required=False)

class DateSchema(ma.Schema):
    date = ma.Date(allow_none=True)

class JobSchema(ma.Schema):
    id = ma.Str(required=True)
    name = ma.Str(required=True)
    next_run_time = ma.DateTime(allow_none=True, required=False)
    trigger = ma.Str(required=True)

class SiteMapLinkSchema(ma.Schema):
    url = ma.Url(required=True)
    endpoint = ma.Str(required=True)

class AssignmentUpdateSchema(ma.Schema):
    player_id = ma.Integer(required=True)
    from_adventure_id = ma.Integer(required=True)
    to_adventure_id = ma.Integer(required=True)

class UserSchema(ma.SQLAlchemyAutoSchema):
    """Schema for User that excludes the `name` column and exposes
    `display_name` (as the canonical display identity).

    Only a small set of non-sensitive fields are included by default. If you
    need to show or hide additional fields (email, google_id, etc.) consider
    adding parameters or a `hide_fields` pattern as in your original model file.
    """

    class Meta:
        model = User
        include_fk = True
        load_instance = False
        sqla_session = db.session
        # Exclude the database `name` field
        exclude = ("name","google_id","email")

class SignupUserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Signup
        include_fk = True
        load_instance = False
        sqla_session = db.session
        exclude = ("id", "user_id", "adventure_date")

    user = ma.Nested(UserSchema, dump_only=True)

class AdventureSmallSchema(ma.SQLAlchemyAutoSchema):
    """Auto-schema for Adventure used for both output (dump) and input (load). Without any references
    """

    class Meta:
        model = Adventure
        include_fk = True
        load_instance = False
        sqla_session = db.session

class SignupAdventureSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Signup
        include_fk = True
        load_instance = True
        sqla_session = db.session
        exclude = ("id", "user_id", "adventure_date")

    adventure = ma.Nested(AdventureSmallSchema, dump_only=True)

class UserWithSignupsSchema(ma.SQLAlchemyAutoSchema):
    """Schema for User that excludes the `name` column and exposes
    `display_name` (as the canonical display identity).

    Only a small set of non-sensitive fields are included by default. If you
    need to show or hide additional fields (email, google_id, etc.) consider
    adding parameters when using this schema.
    """
    signups = ma.Nested(SignupAdventureSchema, many=True, dump_only=True)

    class Meta:
        model = User
        include_fk = True
        load_instance = True
        sqla_session = db.session

        exclude = ("id","world_builder_name","name","google_id","email","dnd_beyond_name","privilege_level","karma")

class AdventureQuerySchema(ma.Schema):
    adventure_id = ma.Integer(allow_none=True)
    week_start = ma.Date(allow_none=True)
    week_end = ma.Date(allow_none=True)

    @validates_schema
    def validate_dates(self, data, **kwargs):
        sd = data.get("week_start")
        ed = data.get("week_end")
        if sd and ed and sd > ed:
            raise ValidationError("week_start must be <= week_end.")
        
class AssignmentSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Assignment
        include_fk = True
        exclude = ("adventure_id","top_three","user_id")

    user = ma.Nested(UserSchema, dump_only=True)

class AssignmentMoveSchema(ma.Schema):
    player_id = ma.Integer(required=True)
    from_adventure_id = ma.Integer(required=True)
    to_adventure_id = ma.Integer(required=True)

class AssignmentUpdateSchema(ma.Schema):
    user_id = ma.Integer(required=True)
    adventure_id = ma.Integer(required=True)
    appeared = ma.Boolean(required=True)


class AssignmentUpdateSchema(ma.Schema):
    user_id = ma.Integer(required=True)
    adventure_id = ma.Integer(required=True)
    appeared = ma.Boolean(required=True)

class AssignmentDeleteSchema(ma.Schema):
    adventure_id = ma.Integer(required=True)


class AdventureSchema(ma.SQLAlchemyAutoSchema):
    """Auto-schema for Adventure used for both output (dump) and input (load).

    - `players` is a nested list of UserSchema for dumping only.
    - `requested_players` is a load-only list of ints that the POST endpoint
       will use to create Assignment rows.
    """

    # assignments -> nested users (dump only)
    assignments = ma.List(ma.Nested(AssignmentSchema), dump_only=True)

    # signups -> nested users (dump only)
    signups = ma.List(ma.Nested(SignupUserSchema), dump_only=True)

    # allow the same schema to accept requested_players during creation
    requested_players = ma.List(ma.Integer(), load_only=True, allow_none=True)

    # allow creator to be set during creation
    creator = ma.Nested(UserSchema, dump_only=True)

    class Meta:
        model = Adventure
        include_fk = True
        load_instance = True
        sqla_session = db.session

    @validates_schema
    def validate_dates(self, data, **kwargs):
        sd = data.get("start_date")
        ed = data.get("end_date")
        max_players = data.get("max_players")
        if sd and ed and sd > ed:
            raise ValidationError("start_date must be <= end_date.")
        if not (max_players > 0 and max_players <= 30):
            raise ValidationError("max_players between 1 and 30, inclusive.")
        


class ConflictResponseSchema(ma.Schema):
    message = ma.Str(required=True)
    mis_assignments = ma.List(ma.Integer(), required=True)
    adventure = ma.Nested(AdventureSchema)

# ----------------------- Routes ----------------------------------

# --- UTILS ---

@blp_utils.route("/alive")
class AliveResource(MethodView):
    @blp_utils.response(200, AliveSchema)
    def get(self):
        """Check API and DB connectivity."""
        try:
            db.session.execute(text("SELECT 1"))
            return {
                "status": "ok",
                "db": "reachable",
                "version": current_app.config["VERSION"]["version"],
            }
        except SQLAlchemyError as e:
            abort(
                500,
                message=str(e),
                extra={"version": current_app.config["VERSION"]["version"], "status": "error"},
            )
    
#@blp_utils.route("/site-map")
class SiteMapResource(MethodView):
    #@blp_utils.response(200, SiteMapLinkSchema(many=True))
    #@login_required
    def get(self):
        """
        Returns a list of all available endpoints (not only api).

        ---
        TODO: REMOVE
        """
        links = []
        for rule in current_app.url_map.iter_rules():
            # Filter out rules we can't navigate to in a browser
            # and rules that require parameters
            if "GET" in rule.methods and has_no_empty_params(rule):
                url = url_for(rule.endpoint, **(rule.defaults or {}))
                links.append((url, rule.endpoint))
        # links is now a list of url, endpoint tuples
        return jsonify(links)

@blp_utils.route("/scheduler")
class SchedulerResource(MethodView):
    @blp_utils.response(200, JobSchema(many=True))
    def get(self):
        """
        Returns a list of all scheduled jobs.
        """
        return ap_scheduler.get_jobs()

@blp_utils.route('/update-karma')
class UpdateKarmaResource(MethodView):
    @login_required
    @blp_utils.arguments(DateSchema)
    @blp_utils.response(200, MessageSchema)
    def post(self, args):
        """
        Force an update of the karma of all players regarding the normal update rules.
        """
        if not is_admin(current_user):
            abort(401, message={'error': 'Unauthorized'})
        reassign_karma(args.get("date", date.today()))

        return {'message': 'Karma updated successfully'}

@blp_utils.route("/login")
class LoginResource(MethodView):
    @blp_utils.response(200, RedirectSchema)
    def get(self):
        """
        Requests a login from Google. Redirects to Google.
        """
        client, google_provider_cfg = get_google()
        # Find out what URL to hit for Google login            
        authorization_endpoint = google_provider_cfg["authorization_endpoint"]

        # Remember the page we want to go back to after logins
        next_url = request.args.get("next", "/")

        # Use library to construct the request for login and provide
        # scopes that let you retrieve user's profile from Google
        request_uri = client.prepare_request_uri(
            authorization_endpoint,
            redirect_uri=request.base_url + "/callback",
            scope=["openid", "email", "profile"],
            state=next_url  # store the original URL
        )
        return redirect(request_uri)
    
@blp_utils.route("/login/callback")
class CallbackResource(MethodView):
    @blp_utils.response(200, RedirectSchema)
    def get(self):
        """
        Endpoint for Google to redirect to after login.
        """
        try:
            # Get authorization code Google sent back to you
            code = request.args.get("code")
            if not code:
                return redirect(url_for("utils.LoginResource"))
            client, google_provider_cfg = get_google()
            state = request.args.get("state", "/")  # this is the original URL the login came from
        except Exception as e:
            return redirect(url_for("utils.LoginResource"))

        # Find out what URL to hit to get tokens that allow you to ask for
        # things on behalf of a user
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
            auth=(current_app.config["GOOGLE"]["client_id"], current_app.config["GOOGLE"]["client_secret"]),
        )
        if not token_response.ok:
            return redirect(url_for("api.login"))

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
            abort(400, message="User email not available or not verified by Google.")

        # See if Google’s user_id is already in our table
        stmt = db.select(User).where(User.google_id == unique_id)
        existing = db.session.scalars(stmt).first()

        if existing:
            # They’re already in our DB — use that
            user = existing
            
        else:
            # Not found → create and commit
            new_user = User.create(
                google_id=unique_id,
                name=users_name,
                email=users_email,
                profile_pic=picture)
            db.session.add(new_user)
            db.session.commit()
            user = new_user

        login_user(user)

        # Send user back to homepage or if he has not yet finished setup set him to edit his profile
        if user.is_setup():
            return redirect(state)
        else:
            return redirect(state)


@blp_utils.route('/logout')
class LockoutResource(MethodView):
    @login_required
    @blp_utils.response(200, RedirectSchema)
    def get(self):
        """
        Logout the current user.
        """
        next_url = request.args.get("next", "/")
        logout_user()
        return redirect(next_url)  

    
# --- USERS ---
@blp_users.route("")
class UsersListResource(MethodView):
    @blp_users.response(200, UserSchema(many=True, exclude=['karma']))
    def get(self):
        """
        Return list of all users. 
        
        Excludes karma.
        Only non-sensitive fields are included by default. 
        If you are not an admin.
        """
        try:        
            return db.session.execute(db.select(User)).scalars().all()
        except SQLAlchemyError as e:
            abort(500, message=f"Database error: {str(e)}")

@blp_users.route("/signups/<string:day>")
class UsersListSignupsResource(MethodView):
    @blp_users.response(200)
    def get(self, day):
        """
        Return list of all users. 
        
        Excludes karma.
        Only non-sensitive fields are included by default. 
        If you are not an admin.
        """
        exclude = []
        if not is_admin(current_user):
            exclude=["privilege_level", "email", "signups", "karma"]
        try:
            today = date.today()
            # If day is provided and valid, use it instead of today
            if (day) and (day != "0"):
                try:
                    today = date.fromisoformat(day)
                except ValueError:
                    abort(400, message="Invalid date format. Use YYYY-MM-DD.")

            start_of_week, end_of_week = get_upcoming_week(today)
            stmt = (
                    db.select(User)
                    .options(
                        joinedload(User.signups),
                        db.with_loader_criteria(
                            Signup,
                            Signup.adventure_date.between(start_of_week, end_of_week),
                            include_aliases=True
                        )
                    )

                )
            users = db.session.execute(stmt).unique().scalars().all()
            current_app.logger.info(f"U: {[[u.display_name, u.signups] for u in users]}")
        
            return UserWithSignupsSchema(many=True, exclude=exclude).dump(users)
        except SQLAlchemyError as e:
            abort(500, message=f"Database error: {str(e)}")

@blp_users.route("/<int:user_id>")
class UserResource(MethodView):
    @blp_users.response(200, UserSchema(exclude=['karma'])) 
    def get(self, user_id):
        """Return single user by id."""
        try:
            user = db.session.get(User, user_id)
            if not user:
                abort(404, message="User not found")
            return user
        except SQLAlchemyError as e:
            abort(500, message=f"Database error: {str(e)}")

    @blp_users.arguments(UserSchema(partial=True, only=["display_name", "world_builder_name", "dnd_beyond_name", "email"]))
    @blp_users.response(200, UserSchema(exclude=['karma']))
    def patch(self, args, user_id):
        """
        Partially update a user. Only fields present in the JSON body will be changed.
        """
        try:
            user = db.session.get(User, user_id)
            if not user:
                abort(404, message="User not found")

            for key, val in args.items():
                    setattr(user, key, val)

            db.session.commit()
            return user

        except IntegrityError as e:
            db.session.rollback()
            # typically triggered by unique constraint (e.g. email already exists)
            abort(409, message=f"Conflict: {str(e.orig) if hasattr(e, 'orig') else str(e)}")

        except SQLAlchemyError as e:
            db.session.rollback()
            abort(500, message=f"Database error: {str(e)}")
    
    @blp_utils.response(201)
    def post(self, user_id):
        """
        DEMO: Login as the user specified by id

        THIS WILL BE REMOVED
        ---
        TODO: REMOVE
        """
        login_user(db.session.get(User, user_id), fresh=True)
        return  
    

@blp_users.route("/me")
class MeResource(MethodView):
    @login_required
    @blp_utils.response(200, UserSchema(exclude=['karma']))
    def get(self):
        """Return current user's details."""
        return current_user

# --- ADVENTURES ---
@blp_adventures.route("")
class AdventureIDlessRequest(MethodView):

    @blp_adventures.arguments(AdventureQuerySchema, location="query")
    #@blp_adventures.response(200, AdventureSchema(many=True))
    def get(self, args):
        """
        Returns a list of Adventure objects within the specified date range. 
        
        The field `players` will be present only when the requester is allowed (privilege level or over release date).
        """
        try:
            week_start = args.get("week_start")
            week_end = args.get("week_end")

            # Eager-load assignments -> user to avoid N+1 queries
            stmt = db.select(Adventure).options(
                joinedload(Adventure.assignments).joinedload(Assignment.user)
            ).order_by(Adventure.date)


            if week_start and week_end:
                stmt = db.select(Adventure).where(
                    Adventure.date <= week_end,
                    Adventure.date >= week_start
                )

            adventures = db.session.scalars(stmt).all()

            # Determine display rights
            user_is_admin = is_admin(current_user)
            display_players = user_is_admin or check_release(adventures) # check for last one cause handling separately is annoying
            exclude = []
            if not user_is_admin:
                exclude = ["assignments.user.karma", "signups"]
                pass
            if not display_players:
                exclude = exclude + ["assignments"]
                pass
            
            return AdventureSchema(many=True, exclude=exclude).dump(adventures)

        except ValidationError as ve:
            abort(400, message=str(ve))

        except SQLAlchemyError as e:
            abort(500, message=f"Database error: {str(e)}")

    @login_required
    @blp_adventures.arguments(AdventureSchema(exclude=("id","user_id"), load_instance = False))
    @blp_adventures.response(201, AdventureSchema()) 
    @blp_adventures.alt_response(409, schema=ConflictResponseSchema())
    def post(self, args):
        """
        Create a new adventure
        """
        try: 
            requested_players = args.pop("requested_players", [])

            new_adv = Adventure.create(
                user_id=current_user.id,
                **args
            ) # this will only return the first adventure if repeat > 1
            db.session.flush()  # new_adv.id available


            # Player requests are only done for the first adventure created
            mis_assignments = []
            for pid in requested_players:
                try:
                    with db.session.begin_nested():  # savepoint per assignment
                        assignment = Assignment(
                            adventure_id=new_adv.id,
                            user_id=pid,
                            appeared=True,
                            top_three=True
                        )
                        db.session.add(assignment)
                        db.session.flush()
                except IntegrityError:
                    db.session.rollback()
                    mis_assignments.append(pid)

            db.session.commit()
            if mis_assignments:
                conflict_payload = ConflictResponseSchema().dump({
                    "message": "Adventure added, but some players could not be assigned.",
                    "adventure": new_adv,
                    "mis_assignments": mis_assignments
                })
                return conflict_payload, 409

            # Normal success: return the model instance (decorator will dump it)
            return new_adv

        except ValidationError as ve:
            db.session.rollback()
            abort(400, message=str(ve))

        except SQLAlchemyError as e:
            db.session.rollback()
            abort(500, message=f"Database error: {str(e)}")

        except Exception as e:
            db.session.rollback()
            raise e

@blp_adventures.route("<int:adventure_id>")
class AdventureResource(MethodView):

    @blp_adventures.arguments(AdventureQuerySchema, location="query")
    #@blp_adventures.response(200, AdventureSchema())
    def get(self, args, adventure_id):
        """
        Returns a singular Adventure objects. 
        
        The field `players` will be present only when the requester is allowed (privilege level or `check_release()`).
        """
        try:
            # Eager-load assignments -> user to avoid N+1 queries
            stmt = db.select(Adventure).options(
                joinedload(Adventure.assignments).joinedload(Assignment.user)
            )

            stmt = db.select(Adventure).where(Adventure.id == int(adventure_id))

            adventures = db.session.scalars(stmt).all()

            # Determine display rights
            user_is_admin = is_admin(current_user)
            display_players = user_is_admin or check_release(adventures)
            exclude = []
            if not user_is_admin:
                exclude = ["assignments.user.karma", "signups"]
                pass
            if not display_players:
                exclude = exclude + ["assignments"]
                pass
            
            return AdventureSchema(many=True, exclude=exclude).dump(adventures)

        except ValidationError as ve:
            abort(400, message=str(ve))

        except SQLAlchemyError as e:
            abort(500, message=f"Database error: {str(e)}")


    @login_required
    @blp_adventures.arguments(AdventureSchema(partial=True, exclude=("id","user_id", "predecessor_id"), load_instance = False))
    def patch(self, args, adventure_id):
        """
        Edit an existing adventure. Only creator or admin can edit.

        Number of sessions, predecessor and creator are not editable.        
        """
        user_id = current_user.id
        adventure = db.session.get(Adventure, adventure_id)
        if not adventure:
            abort(404, message=f"Adventure with id: {adventure_id} not found.")

        # Ownership or admin check
        if not is_admin(current_user) and adventure.user_id != user_id:
            abort(401, message="Unauthorized to edit this adventure.")
            

        # Update provided fields
        for field in args:
            if field in ["requested_room"]: # These fields are only editable by admins
                if not is_admin(current_user):
                    current_app.logger.warning(f"Unauthorized attempt to update field: {field}")
                    continue
            setattr(adventure, field, args[field])

        mis_assignments = []

        # Player reassignment
        if "requested_players" in args:
            new_player_ids = args["requested_players"] or []

            db.session.execute(
                delete(Assignment).where(Assignment.adventure_id == adventure_id)
            )

            for pid in new_player_ids:
                try:
                    assignment = Assignment(
                        adventure_id=adventure_id,
                        user_id=pid,
                        appeared=True,
                        top_three=True
                    )
                    db.session.add(assignment)
                    db.session.flush()
                except IntegrityError:
                    db.session.rollback()
                    mis_assignments.append(pid)

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            abort(500, message=str(e))

        if mis_assignments:
            abort(
                409,
                message="Adventure updated; some players could not be assigned.",
                extra={"mis_assignments": mis_assignments}
            )

        return {"message": "Adventure updated successfully"}
    
    @login_required
    @blp_adventures.response(200, MessageSchema)
    def delete(self, adventure_id):
        """
        Deletes an adventure with the given ID. Only creator or admin can delete.
        """
        user_id = current_user.id

        if not adventure_id:
            abort(400, message={'error': 'Missing adventure_id'})

        try:
            adventure = db.session.get(Adventure, adventure_id)
            if not adventure:
                abort(404, message={'error': 'Adventure not found'})

            # Check permission: admin or creator
            if not is_admin(current_user) and adventure.user_id != user_id:
                abort(401, message={'error': 'Unauthorized to delete this adventure'})

             # Clear predecessor references in other adventures
            db.session.execute(
                db.update(Adventure).
                where(Adventure.predecessor_id == adventure_id).
                values(predecessor_id=None)
            )
            
            # Delete signups related to this adventure
            db.session.execute(
                db.delete(Signup).where(Signup.adventure_id == adventure_id)
            )

            # Delete assignments related to this adventure
            db.session.execute(
                db.delete(Assignment).where(Assignment.adventure_id == adventure_id)
            )

            # Delete the adventure itself
            db.session.delete(adventure)
            db.session.commit()

            return {'message': f'Adventure {adventure_id} and all relations deleted successfully'}

        except SQLAlchemyError as e:
            db.session.rollback()
            return abort(500, message={'error': f'Database error: {str(e)}'})

        except Exception as e:
            return abort(500, message={'error': str(e)})

# --- ASSIGNMENTS ---
@blp_assignments.route('')
class AssignmentResource(MethodView):
    @blp_assignments.response(200,UserSchema(many=True, exclude=['karma', 'privilege_level', 'email', ]))
    def get(self):
        """
        Returns a list of players assigned to a single adventure.
        """
        try:
            adventure_id = request.args.get('adventure_id', type=int)
            if not adventure_id:
                abort(400, message={'error': 'Adventure ID is required'})
            stmt = db.select(Assignment).join(User).where(
                Assignment.adventure_id == adventure_id
            )
            assignments = db.session.scalars(stmt).all()
            users = [assignment.user for assignment in assignments if assignment.user]

            return users, 200

        except Exception as e:
            return abort(500, message={'error': str(e)})

    @login_required
    @blp_assignments.arguments(AdminActionSchema)
    @blp_assignments.response(200, MessageSchema)
    def put(self, args):
        """
        Executes an admin action.
        """
        # Admin check
        if not is_admin(current_user):
            abort(401, message="Unauthorized")
        
        action = args.get('action')
        today = args.get('date', date.today())

        if action == "release":
            release_assignments(today)
        elif action == "reset":
            reset_release(today)
        elif action == "assign":
            assign_rooms_to_adventures(today)
            assign_players_to_adventures(today) 
        else:
            abort(400, message=f"Invalid action: {action}")

        return {'message': f'{action.capitalize()} action executed successfully for {today}'}, 200
    
    @login_required
    @blp_assignments.arguments(AssignmentUpdateSchema)
    @blp_assignments.response(200, MessageSchema)
    def post(self, args):
        """
        Updates the 'appeared' value for an Assignment for a given user.
        Expects JSON body: { "user_id": int, "adventure_id": int, "appeared": <new_value> }
        """

        if current_user.privilege_level < 1: # Is semi admin (only allowed to watch if players appear)
            return abort(401, message={'error': 'Unauthorized'})
       
        user_id = args['user_id']
        adventure_id = args['adventure_id']
        new_value = args['appeared']

        if not user_id or not adventure_id:
            return abort(400, message={'error': 'Both user_id and adventure_id are required'})

        # Fetch the assignment
        assignment = db.session.scalar(
            db.select(Assignment).where(
                Assignment.user_id == user_id,
                Assignment.adventure_id == adventure_id
            )
        )

        if not assignment:
            return abort(404, message=({'error': 'Assignment not found'}))

        # Update the value
        assignment.appeared = new_value
        try:
            db.session.commit()

            return {'message': 'Assignment updated successfully'}, 200

        except Exception as e:
            db.session.rollback()
            return abort(500, message={'error': str(e)})
        
    
    @blp_assignments.arguments(AssignmentMoveSchema)
    @login_required
    def patch(self, args):
        """
        Moves a players assignment from one adventure to another.
        """
        if not is_admin(current_user):
            abort(401, message="Unauthorized")

        player_id = args['player_id']
        from_adventure_id = args['from_adventure_id']
        to_adventure_id = args['to_adventure_id']

        stmt = db.select(Assignment).where(
            Assignment.user_id == player_id,
            Assignment.adventure_id == from_adventure_id
        )
        assignment = db.session.scalars(stmt).first()

        if not assignment:
            abort(404, message="Assignment not found")

        assignment.adventure_id = to_adventure_id
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            abort(400, message=str(e))

        return {'message': 'Assignment updated successfully'}, 200
    
    @blp_assignments.arguments(AssignmentDeleteSchema)
    @login_required
    def delete(self, args):
        """
        Deletes a players assignment from one adventure and punishes the player.
        """
        PUNISH_KARMA_MISS = 25
        user_id = current_user.id
        assignment =  db.session.execute(
                db.select(Assignment).where(Assignment.user_id == user_id, Assignment.adventure_id == args['adventure_id'])
            ).scalar_one()
        # Check permission: admin or creator
        if not is_admin(current_user) and assignment.user_id != user_id:
            abort(401, message={'error': 'Unauthorized to delete this adventure'})


        # Delete assignments related to this adventure
        db.session.delete(assignment)

        # Punish the player
        if not is_admin(current_user):
            db.session.execute(
                db.update(User)
                .where(User.id == user_id)
                .values(karma=User.karma - PUNISH_KARMA_MISS)
            )

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            abort(400, message=str(e))

        return {'message': 'Assignment updated successfully'}, 200

# --- SIGNUP ---
@blp_signups.route('')
class SignupResource(MethodView):
    @login_required
    @blp_signups.response(200, SignupUserSchema(many=True))
    def get(self):
        """
        Returns all the signups (priority medals 1, 2, 3) of the authenticated user.
        """
        if current_user.is_anonymous: # User is not signed in
            abort(401, message="Unauthorized")

        try:
            stmt = db.select(Signup).where(Signup.user_id == current_user.id)
            signups = db.session.scalars(stmt).all()
            return signups

        except SQLAlchemyError as e:
            abort(500, message=f"Database error: {str(e)}")

        except Exception as e:
            abort(500, message=str(e))

    @login_required
    @blp_signups.arguments(SignupUserSchema())
    @blp_signups.response(200, MessageSchema())
    def post(self, args):
        """
        Makes a signup for a specific adventure.
        Deletes old ones if a signup already exists.
        Acts as a toggle: if the same signup exists, it removes it.
        """
        adventure_id = args["adventure_id"]
        priority = args["priority"]
        user_id = current_user.id

        try:

            # Fetch the adventure date
            adventure_date = db.session.execute(
                db.select(Adventure.date).where(Adventure.id == adventure_id)
            ).scalar_one()
            
            # Check if exact same signup already exists (toggle behavior)
            stmt = db.select(Signup).where(
                Signup.user_id == user_id,
                Signup.adventure_id == adventure_id,
                Signup.priority == priority
            )

            existing_signup = db.session.scalars(stmt).first()

            if existing_signup:
                db.session.delete(existing_signup)
                message = 'Signup removed'
            else:
               # Remove any existing signup with same priority and date (regardless of adventure)
                db.session.execute(
                    delete(Signup).where(
                        Signup.user_id == user_id, 
                        Signup.priority == priority,
                        Signup.adventure_date == adventure_date
                    )
                )

                # Remove any existing signup for same adventure (regardless of priority)
                db.session.execute(
                    delete(Signup).where(
                        Signup.user_id == user_id, 
                        Signup.adventure_id == adventure_id
                    )
                )

                # Add new signup
                new_signup = Signup(
                    user_id=user_id, 
                    adventure_id=adventure_id, 
                    priority=priority,
                    adventure_date=adventure_date
                )
                db.session.add(new_signup)
                message = 'Signup registered'

            db.session.commit()
            return {"message": message}, 200

        except SQLAlchemyError as e:
            db.session.rollback()
            abort(500, message=f"Database error: {str(e)}")

        except Exception as e:
            abort(500, message=str(e))