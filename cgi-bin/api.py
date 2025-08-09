from flask import Flask, request
from flask_restx import Api, Resource, fields, reqparse, Namespace, abort
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import joinedload
from datetime import datetime
from yourapp import db
from yourapp.models import Adventure, AdventureAssignment, User
from yourapp.utils import validate_strings, check_release

app = Flask(__name__)
api = Api(app, version='1.0', title='Adventures API', description='Manage Adventures')
adventures_ns = Namespace('adventures', description='Adventure operations')
api.add_namespace(adventures_ns, path='/api/adventures')

# Models for marshalling
user_model = adventures_ns.model('User', {
    'id': fields.Integer,
    'username': fields.String,
    'karma': fields.Integer(attribute='karma', required=False)
})

assignment_model = adventures_ns.model('Assignment', {
    'user': fields.Nested(user_model)
})

adventure_model = adventures_ns.model('Adventure', {
    'id': fields.Integer(readOnly=True),
    'title': fields.String(required=True),
    'short_description': fields.String(required=True),
    'user_id': fields.Integer,
    'max_players': fields.Integer,
    'start_date': fields.String,
    'end_date': fields.String,
    'players': fields.List(fields.Nested(user_model))
})

# Input payload for POST/PUT
adventure_input = adventures_ns.model('AdventureInput', {
    'title': fields.String(required=True),
    'short_description': fields.String(required=True),
    'max_players': fields.Integer(required=True),
    'start_date': fields.String(required=True, description='ISO8601 date'),
    'end_date': fields.String(required=True, description='ISO8601 date'),
    'is_story_adventure': fields.Boolean,
    'requested_room': fields.String,
    'requested_players': fields.List(fields.Integer)
})

# Parser for GET query params
get_parser = reqparse.RequestParser()
get_parser.add_argument('adventure_id', type=int, required=False, help='Filter by adventure ID')
get_parser.add_argument('week_start', type=str, required=False, help='Start of week (ISO8601)')
get_parser.add_argument('week_end', type=str, required=False, help='End of week (ISO8601)')

@adventures_ns.route('')
class AdventureList(Resource):
    @adventures_ns.expect(get_parser)
    @adventures_ns.marshal_list_with(adventure_model)
    def get(self):
        '''List adventures, optionally filtered by ID or date range'''
        args = get_parser.parse_args()
        adv_id = args.get('adventure_id')
        ws = args.get('week_start')
        we = args.get('week_end')

        query = db.session.query(Adventure).options(
            joinedload(Adventure.assignments).joinedload(AdventureAssignment.user)
        )
        if adv_id:
            query = query.filter(Adventure.id == adv_id)
        elif ws and we:
            try:
                start_dt = datetime.fromisoformat(ws)
                end_dt = datetime.fromisoformat(we)
            except ValueError:
                abort(400, 'Invalid date format. Use ISO 8601.')
            query = query.filter(Adventure.start_date <= end_dt, Adventure.end_date >= start_dt)

        adventures = query.all()
        display_players = (not current_user.is_anonymous and current_user.privilege_level >= 1) or check_release()

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
                            'username': user.name
                        }
                        if current_user.privilege_level >= 1:
                            player['karma'] = user.karma
                        adv_dict['players'].append(player)
            result.append(adv_dict)
        return result, 200

    @login_required
    @adventures_ns.expect(adventure_input)
    def post(self):
        '''Create a new adventure'''
        data = request.json
        # validate basic
        title = data.get('title')
        desc = data.get('short_description')
        if not title or not desc:
            abort(400, 'Missing title or short_description')

        try:
            validate_strings([title, desc, data.get('requested_room')])
            max_players = int(data.get('max_players'))
            sd = datetime.fromisoformat(data['start_date']).date()
            ed = datetime.fromisoformat(data['end_date']).date()
        except (ValueError, TypeError) as e:
            abort(400, f'Invalid input: {e}')

        new_adv = Adventure(
            title=title,
            short_description=desc,
            user_id=current_user.id,
            max_players=max_players,
            start_date=sd,
            end_date=ed,
            is_story_adventure=data.get('is_story_adventure', False),
            requested_room=data.get('requested_room')
        )
        db.session.add(new_adv)
        db.session.flush()

        mis = []
        for pid in data.get('requested_players', []):
            try:
                assign = AdventureAssignment(
                    adventure_id=new_adv.id,
                    user_id=pid,
                    appeared=True,
                    top_three=True
                )
                db.session.add(assign)
                db.session.flush()
            except IntegrityError:
                db.session.rollback()
                mis.append(pid)

        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            abort(500, f'Database error: {e}')

        if mis:
            return {'message': 'Adventure added, but some players could not be assigned.',
                    'adventure_id': new_adv.id,
                    'mis_assignments': mis}, 409
        return {'message': 'Adventure added successfully', 'adventure_id': new_adv.id}, 201

    @login_required
    @adventures_ns.expect(adventure_input)
    def put(self):
        '''Update an existing adventure. Provide adventure_id in JSON'''
        data = request.json or {}
        adv_id = data.get('adventure_id')
        if not adv_id:
            abort(400, 'Missing adventure_id')
        adv = Adventure.query.get(adv_id)
        if not adv:
            abort(404, 'Adventure not found')
        if current_user.privilege_level < 1 and adv.user_id != current_user.id:
            abort(401, 'Unauthorized to edit this adventure')

        # update fields
        for field in ['title', 'short_description', 'max_players', 'requested_room']:
            if field in data:
                setattr(adv, field, data[field])
        for date_field in ['start_date', 'end_date']:
            if date_field in data:
                try:
                    setattr(adv, date_field, datetime.fromisoformat(data[date_field]).date())
                except ValueError:
                    abort(400, f'Invalid {date_field} format')
        if 'is_story_adventure' in data:
            adv.is_story_adventure = data['is_story_adventure']

        try:
            validate_strings([v for k, v in data.items() if isinstance(v, str)])
        except ValueError as e:
            abort(400, str(e))

        mis = []
        if 'requested_players' in data:
            AdventureAssignment.query.filter_by(adventure_id=adv_id).delete()
            for pid in data.get('requested_players', []):
                try:
                    assign = AdventureAssignment(adventure_id=adv_id, user_id=pid, appeared=True, top_three=True)
                    db.session.add(assign)
                    db.session.flush()
                except IntegrityError:
                    db.session.rollback()
                    mis.append(pid)

        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            abort(500, f'Database error: {e}')

        if mis:
            return {'message': 'Adventure updated; some players could not be assigned.',
                    'mis_assignments': mis}, 409
        return {'message': 'Adventure updated successfully'}, 200

    @login_required
    def delete(self):
        '''Delete an adventure by ID. Provide adventure_id in JSON'''
        data = request.json or {}
        adv_id = data.get('adventure_id')
        if not adv_id:
            abort(400, 'Missing adventure_id')
        adv = Adventure.query.get(adv_id)
        if not adv:
            abort(404, 'Adventure not found')
        if current_user.privilege_level < 1 and adv.user_id != current_user.id:
            abort(401, 'Unauthorized to delete this adventure')

        try:
            db.session.delete(adv)
            db.session.commit()
            return {'message': f'Adventure {adv_id} deleted successfully'}, 200
        except SQLAlchemyError as e:
            db.session.rollback()
            abort(500, f'Database error: {e}')
