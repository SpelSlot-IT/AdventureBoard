from flask import jsonify, request, current_app
import jwt
import datetime
from functools import wraps


def authenticate_user(username, user_id, privilege_level, password):
    if not username or not password:
        return jsonify({'error': 'Missing credentials'}), 400

    try:
        i = 0
    except Exception as e:
        print(e)
        return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
    
    try:
        token = jwt.encode(
        payload = {
            'user_name': username,
            'user_id': user_id,
            'privilege_level': privilege_level,
            'exp': datetime.datetime.now() + datetime.timedelta(hours=int(current_app.config['APP']['timeout_hours']))
        }, 
        key = current_app.config['APP']['secret_key'], 
        algorithm ='HS256'
        )

        resp = jsonify({ 'success': True })
        resp.set_cookie(
            'access_token', token,
            httponly=True,   # inaccessible to JS
            secure=True,     # only over HTTPS
            samesite='Strict'
            )
        return resp, 200

    except Exception as e:
        print(e)
        return jsonify({'success': False, 'error': 'Could not generate auth token'}), 401
    
def token_required(min_privilege=0, lax=False):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = request.cookies.get('access_token') # get http-only token
            if not token:
                if lax:
                    return f(None, *args, **kwargs)
                else:
                    return jsonify({'message': 'You are not logged in'}), 403
            try:
                token_data = jwt.decode(token, current_app.config['APP']['secret_key'], algorithms=['HS256'])

                # Optional: PyJWT will raise if expired, but you can double-check manually if needed
                exp = datetime.datetime.fromtimestamp(token_data.get('exp'))
                if exp < datetime.datetime.utcnow():
                    return jsonify({'message': 'Your session is expired'}), 403

                user_privilege = token_data.get('privilege_level', 0)
                if user_privilege < min_privilege:
                    return jsonify({'message': 'You have insufficient privileges to perform this action'}), 403

            except jwt.ExpiredSignatureError:
                return jsonify({'message': 'Your session is expired'}), 403
            except jwt.InvalidTokenError:
                return jsonify({'message': 'Invalid auth token!'}), 403

            return f(token_data, *args, **kwargs)
        return decorated
    return decorator

def get_user_info_by_token(token):
    try:
        token_data = jwt.decode(token, current_app.config['APP']['secret_key'], algorithms=['HS256'])
    except jwt.PyJWTError:
        return jsonify({ 'error': 'Invalid token' }), 401

    return jsonify({ 'user_name': token_data['user_name'], 'privilege_level': token_data['privilege_level'] }), 200