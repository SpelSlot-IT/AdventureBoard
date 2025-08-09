from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, AnonymousUserMixin

db = SQLAlchemy()

class Anonymous(AnonymousUserMixin):
  def __init__(self):
    self.privilege_level = -1
    self.id = -1

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id              = db.Column(db.Integer, autoincrement=True, primary_key=True)
    google_id       = db.Column(db.String(100), nullable=False, unique=True)
    name            = db.Column(db.String(255), nullable=False)
    display_name    = db.Column(db.String(255), nullable=True)
    privilege_level = db.Column(db.Integer, nullable=False, default=0)
    email           = db.Column(db.String(255), nullable=True)
    profile_pic     = db.Column(db.String(255), nullable=True)
    karma           = db.Column(db.Integer, default=1000)

    adventures_created  = db.relationship('Adventure', back_populates='creator', lazy='dynamic')
    signups             = db.relationship('Signup', back_populates='user', lazy='dynamic')
    assignments         = db.relationship('AdventureAssignment', back_populates='user', lazy='dynamic')

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.name}')>"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.display_name is None:
            self.display_name = self.name


class Adventure(db.Model):
    __tablename__ = 'adventures'

    id                  = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title               = db.Column(db.String(255), nullable=False)
    short_description   = db.Column(db.Text, nullable=False)
    user_id             = db.Column(db.Integer, db.ForeignKey('users.id'))
    max_players         = db.Column(db.Integer, nullable=False, default=5)
    start_date          = db.Column(db.Date, nullable=False)
    end_date            = db.Column(db.Date, nullable=False)
    is_story_adventure  = db.Column(db.Boolean, nullable=False, default=False)
    requested_room      = db.Column(db.String(4))

    creator         = db.relationship('User', back_populates='adventures_created')
    signups         = db.relationship('Signup', back_populates='adventure')
    assignments     = db.relationship('AdventureAssignment', back_populates='adventure')

    def __repr__(self):
        return f"<Adventure(id={self.id}, title='{self.title}')>"

class AdventureAssignment(db.Model):
    __tablename__ = 'adventure_assignments'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'adventure_id', name='pk_adventure_assignment'),
    )

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    adventure_id = db.Column(db.Integer, db.ForeignKey('adventures.id'), primary_key=True)
    appeared = db.Column(db.Boolean, nullable=False, default=True)
    top_three = db.Column(db.Boolean, nullable=False, default=False)

    user = db.relationship('User', back_populates='assignments')
    adventure = db.relationship('Adventure', back_populates='assignments')

    def __repr__(self):
        return f"<AdventureAssignment(user_id={self.user_id}, adventure_id={self.adventure_id})>"

class Signup(db.Model):
    __tablename__ = 'signups'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'adventure_id', name='unique_user_adventure'),
        db.UniqueConstraint('user_id', 'priority', name='unique_user_priority'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    adventure_id = db.Column(db.Integer, db.ForeignKey('adventures.id'), nullable=False)
    priority = db.Column(db.Integer, nullable=False)

    user = db.relationship('User', back_populates='signups')
    adventure = db.relationship('Adventure', back_populates='signups')

    def __repr__(self):
        return f"<Signup(id={self.id}, user_id={self.user_id}, adventure_id={self.adventure_id}, priority={self.priority})>"

class VariableStorage(db.Model):
    __tablename__ = 'variable_storage'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    release_state = db.Column(db.Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"<VariableStorage(id={self.id}, release_state={self.release_state})>"
