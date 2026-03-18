from __init__ import app, db
import uuid
from sqlalchemy import JSON
from sqlalchemy.orm import validates
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone

# Submission categories - community deeds types
SUBMISSION_CATEGORIES = [
    'volunteer',      # Volunteer work and service
    'charity',        # Charitable donations and giving
    'environmental',  # Environmental and sustainability efforts
    'mentoring',      # Mentoring and tutoring efforts
    'community',      # Community service and events
    'fundraising',    # Fundraising initiatives
    'cleanup',        # Cleanup and beautification projects
    'donation',       # Material donations
    'support',        # Personal support and assistance
    'Misc'            # Miscellaneous/other deeds
]

class Submissions(db.Model):
    __tablename__ = 'public_submissions'

    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.JSON, nullable = False)
    category = db.Column(db.String(50), default = 'Misc', nullable=False)
    image = db.Column(db.String(255), nullable=True)
    submitted_at = db.Column(db.DateTime, default = datetime.now)
    user = db.relationship("User", backref=db.backref("submissions_rel", cascade="all, delete-orphan"), overlaps="personas")

    def __init__(self, content, user, category='Misc', image=None):
        self.user = user
        self.content = content
        self.category = self._validate_category(category)
        self.image = image
        self.submitted_at = datetime.now()
    
    @staticmethod
    def _validate_category(category):
        """Validate and normalize category. Returns the category if valid, else 'Misc'."""
        if category in SUBMISSION_CATEGORIES:
            return category
        return 'Misc'
    

    def read(self):
        return {
        "id": self.id,
        "content": self.content,
        "category": self.category,
        "image": self.image,
        "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
        "user_id": self.user_id,
        "user_name": self.user.name if self.user else None
    }

    def create(self):
        db.session.add(self)
        db.session.commit()
        return self
    
    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        db.session.commit()
        return self
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    @staticmethod
    def get_by_user(user_id):
        return Submissions.query.filter_by(user_id=user_id).all()
    
    @staticmethod
    def get_by_id(submission_id):
        return Submissions.query.get(submission_id)
        
        
