from datetime import datetime, timedelta
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
    personal_room       = db.Column(db.String(16), nullable=True)
    email               = db.Column(db.String(255), nullable=True)
    profile_pic         = db.Column(db.String(255), nullable=True)
    karma               = db.Column(db.Integer, default=1000)
    story_player        = db.Column(db.Boolean, nullable=False, default=False)

    adventures_created  = db.relationship('Adventure', back_populates='creator', lazy='dynamic')
    signups             = db.relationship('Signup', back_populates='user')
    assignments         = db.relationship('Assignment', back_populates='user')

    def __repr__(self):
        return f"<User(display_name='{self.display_name}', karma={self.karma}, privilege_level={self.privilege_level})>"
    
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
    num_sessions        = db.Column(db.Integer, nullable=False, default=1)
    predecessor_id      = db.Column(db.Integer, db.ForeignKey('adventures.id'), nullable=True)
    title               = db.Column(db.String(255), nullable=False)
    short_description   = db.Column(db.Text, nullable=False)
    user_id             = db.Column(db.Integer, db.ForeignKey('users.id')) # This is the creator
    max_players         = db.Column(db.Integer, nullable=False, default=5)
    date                = db.Column(db.Date, nullable=False)
    tags                = db.Column(db.String(255), nullable=True)
    requested_room      = db.Column(db.String(16), nullable=True)
    release_assignments = db.Column(db.Boolean, nullable=False, default=False) # After this date assignments to this adventure are visible
    rank_combat         = db.Column(db.Integer, nullable=False, default=0)
    rank_exploration    = db.Column(db.Integer, nullable=False, default=0)
    rank_roleplaying    = db.Column(db.Integer, nullable=False, default=0)
    is_waitinglist      = db.Column(db.Integer, nullable=False, default=0) # 0 = no, 1 = yes, 2 = was waitinglist

    predecessor     = db.relationship('Adventure', remote_side=[id], foreign_keys=[predecessor_id])
    creator         = db.relationship('User', back_populates='adventures_created')
    signups         = db.relationship('Signup', back_populates='adventure')
    assignments     = db.relationship('Assignment', back_populates='adventure')

    def __repr__(self):
        return f"<Adventure(id={self.id}, title='{self.title}')>"
    
    @classmethod
    def create(cls, commit=True, **kwargs) -> "Adventure":
        """
        Factory to create one or multiple Adventures. 
        If num_sessions > 1, it creates that many adventures one week apart,
        and wires up predecessor_id accordingly.
        """
        adventures = []
        num_sessions = kwargs.get("num_sessions", 1)

        # store the base date
        base_date = kwargs["date"]

        predecessor = None
        for i in range(num_sessions):
            # fresh copy of kwargs for each loop
            data = dict(kwargs)
            data["date"] = base_date + timedelta(days=7 * i)

            adventure = cls(**data)
            if predecessor:
                adventure.predecessor = predecessor  # link to previous
            adventures.append(adventure)
            db.session.add(adventure)

            predecessor = adventure  # move chain forward

        if commit:
            db.session.commit()

        return adventures if num_sessions > 1 else adventures[0] # return first adventure created

class Assignment(db.Model):
    __tablename__ = 'assignments'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'adventure_id', name='pk_adventure_assignment'),
    )

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    adventure_id = db.Column(db.Integer, db.ForeignKey('adventures.id'), primary_key=True)
    appeared = db.Column(db.Boolean, nullable=False, default=True)
    # preference_place stores the priority of the user's signup that led to this assignment.
    # 1 = first choice, 2 = second choice, 3 = third choice, 4+ = assigned outside top three
    # None = not applicable (e.g., waiting list assignment)
    preference_place = db.Column(db.Integer, nullable=True)
    creation_date = db.Column(db.DateTime, nullable=False, default=datetime.now())

    user = db.relationship('User', back_populates='assignments')
    adventure = db.relationship('Adventure', back_populates='assignments')

    def __repr__(self):
        return f"<Assignment(user_id={self.user_id}, adventure_id={self.adventure_id}, appeared={self.appeared}, preference_place={self.preference_place}, creation_date={self.creation_date})>"

class Signup(db.Model):
    __tablename__ = 'signups'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'adventure_id', name='unique_user_adventure'),
        db.UniqueConstraint('user_id', 'priority', 'adventure_date', name='unique_user_priority_date'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    adventure_id = db.Column(db.Integer, db.ForeignKey('adventures.id'), nullable=False)
    priority = db.Column(db.Integer, nullable=False)
    adventure_date = db.Column(db.Date, nullable=False)

    user = db.relationship('User', back_populates='signups')
    adventure = db.relationship('Adventure', back_populates='signups')

    def __repr__(self):
        return f"<Signup(id={self.id}, user_id={self.user_id}, adventure_id={self.adventure_id}, priority={self.priority})>"