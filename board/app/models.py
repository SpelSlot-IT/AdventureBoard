from flask_login import UserMixin, AnonymousUserMixin
from sqlalchemy import func

from .provider import db

def custom_name_resolver(schema):
    return schema.__class__.__name__ + "Schema"

class Anonymous(AnonymousUserMixin):
  def __init__(self):
    self.privilege_level = -1
    self.id = -1

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id                  = db.Column(db.Integer, autoincrement=True, primary_key=True)
    google_id           = db.Column(db.String(100), nullable=False, unique=True)
    name                = db.Column(db.String(255), nullable=False)
    display_name        = db.Column(db.String(255), nullable=True)
    world_builder_name  = db.Column(db.String(255), nullable=True)
    dnd_beyond_name     = db.Column(db.String(255), nullable=True)
    dnd_beyond_campaign = db.Column(db.Integer, nullable=True)
    privilege_level     = db.Column(db.Integer, nullable=False, default=0)
    email               = db.Column(db.String(255), nullable=True)
    profile_pic         = db.Column(db.String(255), nullable=True)
    karma               = db.Column(db.Integer, default=1000)

    adventures_created  = db.relationship('Adventure', back_populates='creator', lazy='dynamic')
    signups             = db.relationship('Signup', back_populates='user', lazy='dynamic')
    assignments         = db.relationship('AdventureAssignment', back_populates='user', lazy='dynamic')

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.name}')>"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.display_name is None:
            self.display_name = self.name

    def is_finished(self):
        return self.world_builder_name and self.dnd_beyond_name and self.display_name
    
    
    @classmethod
    def assign_campaign(cls):
        """
        Return an integer campaign id:
         - 1..5 if any have < 6 users
         - otherwise 6
        """
        MAX_USERS_PER_CAMPAIGN = 6
        NUM_CAMPAIGNS = 5
        for campaign_id in range(1, NUM_CAMPAIGNS+1):
            stmt = db.select(func.count(cls.id)).where(cls.dnd_beyond_campaign == campaign_id)
            count = db.session.scalar(stmt)
            if count < MAX_USERS_PER_CAMPAIGN:
                return campaign_id
        return NUM_CAMPAIGNS+1

    @classmethod
    def create(cls, commit=True, **kwargs):
        """
        Factory to create a User and assign campaign if not provided.

        Usage:
            user = User.create(google_id='x', name='Alice', email='a@b.com')
        """
        if kwargs.get("dnd_beyond_campaign") is None:
            kwargs["dnd_beyond_campaign"] = cls.assign_campaign()

        user = cls(**kwargs)
        db.session.add(user)
        if commit:
            db.session.commit()
        return user
    
    def is_setup(self) -> bool:
        """Check if all required fields are filled in."""
        return all([
            bool(self.display_name and self.display_name.strip()),
            bool(self.world_builder_name and self.world_builder_name.strip()),
            bool(self.dnd_beyond_name and self.dnd_beyond_name.strip()),
            self.dnd_beyond_campaign is not None
        ])



class Adventure(db.Model):
    __tablename__ = 'adventures'

    id                  = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title               = db.Column(db.String(255), nullable=False)
    short_description   = db.Column(db.Text, nullable=False)
    user_id             = db.Column(db.Integer, db.ForeignKey('users.id'))
    max_players         = db.Column(db.Integer, nullable=False, default=5)
    start_date          = db.Column(db.Date, nullable=False)
    end_date            = db.Column(db.Date, nullable=False)
    tags                = db.Column(db.String(255), nullable=True)
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
